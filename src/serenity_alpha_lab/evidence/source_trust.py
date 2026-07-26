from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from serenity_alpha_lab.evidence.schema import EvidenceTrustLevel


SOURCE_TRUST_CONTRACT_VERSION = "research.source_trust@1.0.0"
SOURCE_TRUST_SCHEMA_NAME = "research.source_trust"
SOURCE_TRUST_SCHEMA_VERSION = "1.0.0"

_REMOVED_EXTERNAL_INSTRUCTION = "[REMOVED_EXTERNAL_INSTRUCTION]"


class SourceTrustError(ValueError):
    """Raised when unstructured source trust input is invalid."""


class UnstructuredSourceType(StrEnum):
    OFFICIAL_DISCLOSURE = "official_disclosure"
    REGULATORY_FILING = "regulatory_filing"
    COMPANY_ANNOUNCEMENT = "company_announcement"
    WIRE_NEWS = "wire_news"
    NEWS = "news"
    SEARCH_RESULT = "search_result"
    SOCIAL_POST = "social_post"
    UNKNOWN = "unknown"


class SourceTrustIssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    MALICIOUS = "malicious"


@dataclass(frozen=True, slots=True)
class SourceTrustIssue:
    code: str
    severity: SourceTrustIssueSeverity
    message: str

    def __post_init__(self) -> None:
        _required_string("code", self.code)
        _required_string("message", self.message)
        object.__setattr__(self, "severity", SourceTrustIssueSeverity(self.severity))

    def to_record(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class UnstructuredSourceInput:
    source_id: str
    source_type: UnstructuredSourceType
    url: str
    title: str
    raw_body: str
    published_at: datetime
    observed_at: datetime
    available_at: datetime
    publisher: str | None = None

    def __post_init__(self) -> None:
        _required_string("source_id", self.source_id)
        object.__setattr__(self, "source_type", UnstructuredSourceType(self.source_type))
        _required_string("url", self.url)
        _required_string("title", self.title)
        _required_string("raw_body", self.raw_body)
        _aware_datetime("published_at", self.published_at)
        _aware_datetime("observed_at", self.observed_at)
        _aware_datetime("available_at", self.available_at)
        _optional_string("publisher", self.publisher)

    def to_record(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "url": self.url,
            "title": self.title,
            "publisher": self.publisher,
            "published_at": self.published_at.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SourceTrustVerdict:
    source: UnstructuredSourceInput
    trust: EvidenceTrustLevel
    canonical_url: str
    url_hash: str
    raw_body_hash: str
    cleaned_body_hash: str
    cleaned_body: str
    issues: tuple[SourceTrustIssue, ...]
    malicious_instruction_detected: bool
    strong_claim_allowed: bool
    corroboration_required: bool
    contract_version: str = SOURCE_TRUST_CONTRACT_VERSION
    schema_name: str = SOURCE_TRUST_SCHEMA_NAME
    schema_version: str = SOURCE_TRUST_SCHEMA_VERSION

    def to_record(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "source_id": self.source.source_id,
            "source_type": self.source.source_type.value,
            "title": self.source.title,
            "publisher": self.source.publisher,
            "published_at": self.source.published_at.isoformat(),
            "observed_at": self.source.observed_at.isoformat(),
            "available_at": self.source.available_at.isoformat(),
            "trust": self.trust.value,
            "canonical_url": self.canonical_url,
            "url_hash": self.url_hash,
            "raw_body_hash": self.raw_body_hash,
            "cleaned_body_hash": self.cleaned_body_hash,
            "cleaned_body": self.cleaned_body,
            "malicious_instruction_detected": self.malicious_instruction_detected,
            "strong_claim_allowed": self.strong_claim_allowed,
            "corroboration_required": self.corroboration_required,
            "issues": [issue.to_record() for issue in self.issues],
        }

    def to_prompt_safe_record(self) -> dict[str, object]:
        return {
            "source_id": self.source.source_id,
            "source_type": self.source.source_type.value,
            "title": self.source.title,
            "publisher": self.source.publisher,
            "published_at": self.source.published_at.isoformat(),
            "available_at": self.source.available_at.isoformat(),
            "trust": self.trust.value,
            "canonical_url": self.canonical_url,
            "url_hash": self.url_hash,
            "cleaned_body_hash": self.cleaned_body_hash,
            "cleaned_body": self.cleaned_body,
            "strong_claim_allowed": self.strong_claim_allowed,
            "corroboration_required": self.corroboration_required,
            "issues": [issue.to_record() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class SourceTrustPolicy:
    trust_by_source_type: dict[UnstructuredSourceType, EvidenceTrustLevel]

    @classmethod
    def default(cls) -> SourceTrustPolicy:
        return cls(
            trust_by_source_type={
                UnstructuredSourceType.OFFICIAL_DISCLOSURE: EvidenceTrustLevel.AUTHORITATIVE,
                UnstructuredSourceType.REGULATORY_FILING: EvidenceTrustLevel.AUTHORITATIVE,
                UnstructuredSourceType.COMPANY_ANNOUNCEMENT: EvidenceTrustLevel.HIGH,
                UnstructuredSourceType.WIRE_NEWS: EvidenceTrustLevel.HIGH,
                UnstructuredSourceType.NEWS: EvidenceTrustLevel.MEDIUM,
                UnstructuredSourceType.SEARCH_RESULT: EvidenceTrustLevel.MEDIUM,
                UnstructuredSourceType.SOCIAL_POST: EvidenceTrustLevel.LOW,
                UnstructuredSourceType.UNKNOWN: EvidenceTrustLevel.UNTRUSTED,
            }
        )

    def assess(self, source: UnstructuredSourceInput) -> SourceTrustVerdict:
        if type(source) is not UnstructuredSourceInput:
            raise SourceTrustError("source must be an UnstructuredSourceInput")

        canonical_url = canonicalize_url(source.url)
        raw_body = normalize_body_text(source.raw_body)
        cleaned_body, cleaning_issues = clean_unstructured_body(source.raw_body)
        issues = [*cleaning_issues, *_time_conflict_issues(source), *_trust_issues(source)]
        trust = self.trust_by_source_type.get(source.source_type, EvidenceTrustLevel.UNTRUSTED)
        malicious = any(issue.severity is SourceTrustIssueSeverity.MALICIOUS for issue in issues)
        time_conflict = any(issue.code == "time_conflict" for issue in issues)
        low_trust = trust in {EvidenceTrustLevel.LOW, EvidenceTrustLevel.UNTRUSTED}
        corroboration_required = (
            low_trust
            or malicious
            or time_conflict
            or source.source_type in {UnstructuredSourceType.SEARCH_RESULT, UnstructuredSourceType.SOCIAL_POST}
        )
        strong_claim_allowed = not (low_trust or malicious or time_conflict)

        return SourceTrustVerdict(
            source=source,
            trust=trust,
            canonical_url=canonical_url,
            url_hash=_sha256_text(canonical_url),
            raw_body_hash=_sha256_text(raw_body),
            cleaned_body_hash=_sha256_text(cleaned_body),
            cleaned_body=cleaned_body,
            issues=tuple(sorted(issues, key=lambda issue: (issue.severity.value, issue.code, issue.message))),
            malicious_instruction_detected=malicious,
            strong_claim_allowed=strong_claim_allowed,
            corroboration_required=corroboration_required,
        )


def canonicalize_url(value: str) -> str:
    url = _required_string("url", value).strip()
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise SourceTrustError("url must be an absolute http(s) URL")
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = quote(parsed.path or "/", safe="/:@-._~")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_query_key(key)
    ]
    query = urlencode(sorted(query_pairs), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_body_text(value: str) -> str:
    text = _required_string("raw_body", value)
    lines = (" ".join(line.strip().split()) for line in text.replace("\r\n", "\n").split("\n"))
    return "\n".join(line for line in lines if line).strip()


def clean_unstructured_body(value: str) -> tuple[str, tuple[SourceTrustIssue, ...]]:
    normalized = normalize_body_text(value)
    cleaned_lines: list[str] = []
    removed_instruction = False
    for line in normalized.split("\n"):
        if _looks_like_external_instruction(line):
            if not cleaned_lines or cleaned_lines[-1] != _REMOVED_EXTERNAL_INSTRUCTION:
                cleaned_lines.append(_REMOVED_EXTERNAL_INSTRUCTION)
            removed_instruction = True
            continue
        cleaned_lines.append(line)
    cleaned_body = "\n".join(cleaned_lines).strip()
    issues: list[SourceTrustIssue] = []
    if removed_instruction:
        issues.append(
            SourceTrustIssue(
                code="external_instruction_removed",
                severity=SourceTrustIssueSeverity.MALICIOUS,
                message="External prompt/tool instruction was removed from prompt-safe content.",
            )
        )
    return cleaned_body, tuple(issues)


def _time_conflict_issues(source: UnstructuredSourceInput) -> tuple[SourceTrustIssue, ...]:
    conflicts: list[str] = []
    if source.observed_at < source.published_at:
        conflicts.append("observed_at precedes published_at")
    if source.available_at < source.published_at:
        conflicts.append("available_at precedes published_at")
    if source.available_at < source.observed_at:
        conflicts.append("available_at precedes observed_at")
    if not conflicts:
        return ()
    return (
        SourceTrustIssue(
            code="time_conflict",
            severity=SourceTrustIssueSeverity.WARNING,
            message="; ".join(conflicts),
        ),
    )


def _trust_issues(source: UnstructuredSourceInput) -> tuple[SourceTrustIssue, ...]:
    if source.source_type in {UnstructuredSourceType.SOCIAL_POST, UnstructuredSourceType.UNKNOWN}:
        return (
            SourceTrustIssue(
                code="low_trust_requires_corroboration",
                severity=SourceTrustIssueSeverity.WARNING,
                message="Low-trust unstructured source cannot independently support a strong conclusion.",
            ),
        )
    return ()


def _looks_like_external_instruction(line: str) -> bool:
    return any(pattern.search(line) is not None for pattern in _EXTERNAL_INSTRUCTION_PATTERNS)


def _is_tracking_query_key(key: str) -> bool:
    normalized = key.lower()
    return normalized.startswith("utm_") or normalized in {"fbclid", "gclid", "yclid", "mc_cid", "mc_eid"}


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _required_string(field_name: str, value: str) -> str:
    if type(value) is not str or not value.strip():
        raise SourceTrustError(f"{field_name} is required")
    return value


def _optional_string(field_name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _required_string(field_name, value)


def _aware_datetime(field_name: str, value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise SourceTrustError(f"{field_name} must be timezone-aware")
    return value


_EXTERNAL_INSTRUCTION_PATTERNS = (
    re.compile(r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|system|developer)\s+instructions\b", re.I),
    re.compile(r"\b(system|developer)\s+prompt\b", re.I),
    re.compile(r"\b(call|use|invoke|run)\s+(the\s+)?[\w -]*(tool|function|api|shell)\b", re.I),
    re.compile(r"\b(admin|root)\s*=\s*true\b", re.I),
    re.compile(r"\breveal\b.*\b(prompt|instructions|secret|token)\b", re.I),
)
