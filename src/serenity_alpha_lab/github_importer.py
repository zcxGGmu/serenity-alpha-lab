from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, Iterable, List, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .evidence import EvidenceItem, dedupe_evidence, tokenize, write_evidence_jsonl


DEFAULT_CANDIDATE_PATHS = [
    "README.md",
    "README_CN.md",
    "README.zh-CN.md",
    "SKILL.md",
    "serenity-skill/SKILL.md",
    "skills/serenity/SKILL.md",
    "references/methodology.md",
    "references/articles.md",
]

RELEVANCE_TERMS = {
    "serenity",
    "aleabitoreddit",
    "stockgodserenity",
    "supply",
    "供应链",
    "bottleneck",
    "chokepoint",
    "卡脖子",
    "卡点",
    "cpo",
    "optical",
    "laser",
    "silicon",
    "photonics",
    "半导体",
    "硅光",
    "ai",
    "hyperscaler",
    "memory",
    "crowding",
    "risk",
    "invalidation",
}

TICKER_BLACKLIST = {
    "AI",
    "AD",
    "API",
    "BC",
    "CN",
    "CPO",
    "CPU",
    "EN",
    "ETF",
    "GPU",
    "HTTP",
    "JSON",
    "LLM",
    "MIT",
    "NFA",
    "README",
    "RSS",
    "SEC",
    "SKILL",
    "URL",
    "X",
}

KNOWN_TICKERS = {
    "AAOI",
    "AMD",
    "ASML",
    "AVGO",
    "AXTI",
    "COHR",
    "CRDO",
    "EWY",
    "IREN",
    "IQE",
    "JBL",
    "LITE",
    "LPK",
    "MRVL",
    "MU",
    "NVDA",
    "POET",
    "SIVE",
    "SMCI",
    "SNDK",
    "SOI",
    "TSM",
}

THEME_KEYWORDS = {
    "CPO": {"cpo", "co-packaged", "optical", "interconnect", "硅光"},
    "AI infrastructure": {"ai", "hyperscaler", "datacenter", "数据中心", "infrastructure"},
    "supply-chain bottleneck": {"bottleneck", "chokepoint", "卡脖子", "卡点", "供应链"},
    "laser": {"laser", "激光"},
    "semiconductor": {"semiconductor", "半导体"},
    "memory": {"memory", "dram", "nand", "hbm", "存储"},
    "crowding": {"crowding", "attention", "拥挤", "社交"},
    "risk": {"risk", "skeptic", "invalidation", "失效", "风险", "weaken"},
}


@dataclass(frozen=True)
class RepoSpec:
    full_name: str
    url: str
    default_branch: str
    candidate_paths: Sequence[str]
    tags: Sequence[str]
    published_at: date


@dataclass(frozen=True)
class GitHubDocument:
    repo: RepoSpec
    path: str
    source_url: str
    content: str


def load_repo_specs(path: Path | str) -> List[RepoSpec]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("repo manifest must be a JSON array")

    specs: List[RepoSpec] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("repo manifest entries must be objects")
        specs.append(_parse_repo_spec(entry))
    return specs


def fetch_repo_documents(repo: RepoSpec, timeout: int = 20) -> List[GitHubDocument]:
    documents: List[GitHubDocument] = []
    for path in repo.candidate_paths:
        raw_url = f"https://raw.githubusercontent.com/{repo.full_name}/{repo.default_branch}/{path}"
        source_url = f"{repo.url}/blob/{repo.default_branch}/{path}"
        request = Request(raw_url, headers={"User-Agent": "serenity-alpha-lab/0.1"})
        try:
            with urlopen(request, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 404:
                continue
            continue
        except (URLError, TimeoutError, UnicodeDecodeError):
            continue
        if content.strip():
            documents.append(GitHubDocument(repo=repo, path=path, source_url=source_url, content=content))
    return documents


def import_github_repos(
    repos: Sequence[RepoSpec],
    output_path: Path | str,
    fetcher: Callable[[RepoSpec], Sequence[GitHubDocument]] = fetch_repo_documents,
    imported_at: date | None = None,
) -> List[EvidenceItem]:
    imported_on = imported_at or date.today()
    items: List[EvidenceItem] = []
    seen_ids = set()

    for repo in repos:
        documents = list(fetcher(repo))
        for item in documents_to_evidence(documents, imported_at=imported_on):
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            items.append(item)

    deduped_items = dedupe_evidence(items)
    write_evidence_jsonl(deduped_items, output_path)
    return deduped_items


def documents_to_evidence(documents: Iterable[GitHubDocument], imported_at: date) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    seen_ids = set()

    for document in documents:
        for heading, body in _markdown_sections(document.content):
            section_text = f"{heading}\n{body}".strip()
            if not _is_relevant(section_text):
                continue

            claim = _summarize_claim(heading, body)
            summary = _summarize_body(body)
            if not summary:
                continue
            evidence_id = _evidence_id(document, heading, claim)
            if evidence_id in seen_ids:
                continue
            seen_ids.add(evidence_id)

            themes = _extract_themes(section_text, document.repo.tags)
            direction = _infer_direction(heading, body)
            strength = _infer_strength(section_text)
            claim_type = _infer_claim_type(heading, body, direction, strength)
            items.append(
                EvidenceItem(
                    id=evidence_id,
                    source_title=f"{document.repo.full_name} {document.path}",
                    source_url=document.source_url,
                    published_at=document.repo.published_at or imported_at,
                    claim=claim,
                    summary=summary,
                    tickers=_extract_tickers(section_text),
                    themes=themes,
                    supply_chain_layer=_infer_supply_chain_layer(section_text),
                    direction=direction,
                    strength=strength,
                    confidence=_infer_confidence(direction, strength),
                    factor_impacts=_infer_factor_impacts(section_text, direction),
                    claim_type=claim_type,
                )
            )

    return items


def _parse_repo_spec(entry: Mapping[str, object]) -> RepoSpec:
    full_name = _required_string(entry, "full_name")
    return RepoSpec(
        full_name=full_name,
        url=str(entry.get("url") or f"https://github.com/{full_name}"),
        default_branch=str(entry.get("default_branch") or "main"),
        candidate_paths=_string_list(entry.get("candidate_paths"), DEFAULT_CANDIDATE_PATHS),
        tags=_string_list(entry.get("tags"), []),
        published_at=date.fromisoformat(str(entry.get("published_at") or date.today().isoformat())),
    )


def _required_string(entry: Mapping[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"repo manifest entry requires non-empty {key}")
    return value.strip()


def _string_list(value: object, default: Sequence[str]) -> List[str]:
    if value is None:
        return list(default)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError("manifest list values must be non-empty strings")
    return [item.strip() for item in value]


def _markdown_sections(content: str) -> List[tuple[str, str]]:
    sections: List[tuple[str, str]] = []
    current_heading = "Overview"
    current_lines: List[str] = []

    for line in content.splitlines():
        heading_match = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if heading_match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = heading_match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [(heading, body) for heading, body in sections if body.strip()]


def _is_relevant(text: str) -> bool:
    tokens = set(tokenize(text))
    return bool(tokens & RELEVANCE_TERMS)


def _summarize_claim(heading: str, body: str) -> str:
    first_paragraph = _first_paragraph(body)
    claim = f"{heading}: {first_paragraph}" if first_paragraph else heading
    return _truncate(_clean_markdown(claim), 320)


def _summarize_body(body: str) -> str:
    return _truncate(_clean_markdown(_first_paragraph(body)), 260)


def _first_paragraph(text: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return paragraphs[0] if paragraphs else ""


def _clean_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_>#-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _evidence_id(document: GitHubDocument, heading: str, claim: str) -> str:
    digest = hashlib.sha1(
        f"{document.repo.full_name}|{document.path}|{heading}|{claim}".encode("utf-8")
    ).hexdigest()[:12]
    return f"github:{document.repo.full_name}:{digest}"


def _extract_tickers(text: str) -> List[str]:
    tickers = []
    for match in re.findall(r"(?<![A-Za-z0-9])\$([A-Z]{1,5})(?![A-Za-z0-9])", text):
        ticker = match.upper()
        if ticker in TICKER_BLACKLIST:
            continue
        if ticker not in tickers:
            tickers.append(ticker)

    for ticker in sorted(KNOWN_TICKERS):
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(ticker)}(?![A-Za-z0-9])", text):
            if ticker not in tickers:
                tickers.append(ticker)
    return tickers or ["SERENITY"]


def _extract_themes(text: str, repo_tags: Sequence[str]) -> List[str]:
    lowered = text.lower()
    themes: List[str] = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            themes.append(theme)
    for tag in repo_tags:
        if tag not in themes:
            themes.append(tag)
    return themes or ["Serenity methodology"]


def _infer_direction(heading: str, body: str) -> str:
    heading_lowered = heading.lower()
    body_probe = body.lower()[:700]
    negative_heading_terms = ["risk", "skeptic", "invalidation", "bear", "failure", "风险", "失效", "反证"]
    negative_body_terms = [
        "crowding risk",
        "should weaken",
        "weaken if",
        "fails to",
        "fail if",
        "substitute",
        "runs ahead",
        "替代",
    ]
    if any(term in heading_lowered for term in negative_heading_terms) or any(term in body_probe for term in negative_body_terms):
        return "negative"
    lowered = f"{heading}\n{body}".lower()
    if any(term in lowered for term in ["bottleneck", "chokepoint", "卡脖子", "卡点", "candidate", "supply chain", "供应链"]):
        return "positive"
    return "neutral"


def _infer_strength(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["speculative", "hypothesis", "thesis", "could", "might", "推断", "可能"]):
        return "speculative"
    return "derived"


def _infer_claim_type(heading: str, body: str, direction: str, strength: str) -> str:
    text = f"{heading}\n{body}".lower()
    heading_lowered = heading.lower()
    if direction == "negative":
        if any(term in text for term in ["invalidation", "invalidated", "fail if", "fails to", "失效"]):
            return "invalidation"
        return "risk"
    if any(term in heading_lowered for term in ["prompt", "how to use", "usage", "install", "quick start", "method", "输出", "复制"]):
        return "methodology"
    if any(term in text for term in ["用 serenity skill", "可以这样问", "workflow", "checklist", "methodology", "方法论", "研究框架"]):
        return "methodology"
    if any(term in text for term in ["catalyst", "upcoming", "near-term", "催化"]):
        return "catalyst"
    if strength == "primary":
        return "fact"
    return "inference"


def _infer_confidence(direction: str, strength: str) -> float:
    if strength == "speculative":
        return 0.56 if direction != "negative" else 0.6
    return 0.66 if direction != "negative" else 0.64


def _infer_supply_chain_layer(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["laser", "光", "component", "器件"]):
        return "component"
    if any(term in lowered for term in ["memory", "dram", "nand", "hbm", "存储"]):
        return "memory"
    if any(term in lowered for term in ["interconnect", "cpo", "optical", "硅光"]):
        return "interconnect"
    if any(term in lowered for term in ["risk", "crowding", "attention"]):
        return "market_structure"
    return "methodology"


def _infer_factor_impacts(text: str, direction: str) -> Mapping[str, int]:
    lowered = text.lower()
    impacts = {
        "evidence_quality": 6,
        "invalidation_clarity": 3,
    }

    if any(term in lowered for term in ["bottleneck", "chokepoint", "卡脖子", "卡点", "constraint"]):
        impacts["bottleneck_scarcity"] = 14
        impacts["supply_elasticity"] = 8
    if any(term in lowered for term in ["cpo", "ai", "hyperscaler", "datacenter", "demand", "scale-out"]):
        impacts["demand_certainty"] = 12
    if any(term in lowered for term in ["laser", "optical", "silicon photonics", "硅光"]):
        impacts["bottleneck_scarcity"] = max(impacts.get("bottleneck_scarcity", 0), 16)
    if any(term in lowered for term in ["qualification", "customer", "design-in", "验证"]):
        impacts["invalidation_clarity"] = 10
    if any(term in lowered for term in ["crowding", "attention", "substitute", "weaken", "runs ahead", "拥挤", "社交", "替代", "抢跑"]):
        impacts["crowding_risk"] = 18
        impacts["invalidation_clarity"] = max(impacts.get("invalidation_clarity", 0), 12)

    if direction == "negative":
        impacts.setdefault("crowding_risk", 12)

    return impacts
