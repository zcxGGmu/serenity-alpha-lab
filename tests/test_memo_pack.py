from __future__ import annotations

from datetime import date

from serenity_alpha_lab.evidence import EvidenceItem
from serenity_alpha_lab.memo_pack import (
    build_memo_pack,
    render_memo_pack_index,
    render_memo_pack_sources,
    write_memo_pack,
)


def item(
    item_id: str,
    tickers: list[str],
    *,
    direction: str = "positive",
    strength: str = "derived",
    claim_type: str = "inference",
    themes: list[str] | None = None,
    source_excerpt: str = "",
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        source_title=f"Source {item_id}",
        source_url="https://example.com",
        published_at=date(2026, 1, 1),
        claim=f"Claim {item_id}",
        summary=f"Summary {item_id}",
        tickers=tickers,
        themes=themes or ["CPO"],
        supply_chain_layer="optical components",
        direction=direction,
        strength=strength,
        confidence=0.75,
        factor_impacts={"evidence_quality": 10},
        claim_type=claim_type,
        source_excerpt=source_excerpt,
    )


def test_build_memo_pack_generates_memos_only_for_ready_tickers():
    evidence = [
        item("sec:AAOI:revenue", ["AAOI"], strength="primary", claim_type="fact", themes=["primary-source"]),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
        item("github:AAOI:cpo", ["AAOI"]),
        item("github:SIVE:cpo", ["SIVE"]),
        item("risk:SIVE", ["SIVE"], direction="negative", claim_type="risk"),
    ]

    pack = build_memo_pack(evidence, query="CPO", tickers=["SIVE", "AAOI"], limit=8)

    assert [memo.ticker for memo in pack.memos] == ["AAOI"]
    assert "AAOI" in pack.memos[0].markdown
    assert [skipped.ticker for skipped in pack.skipped] == ["SIVE"]
    assert pack.skipped[0].status == "blocked"
    assert "missing_primary_source" in pack.skipped[0].flag_codes


def test_render_memo_pack_index_lists_memos_and_gap_reasons():
    evidence = [
        item("sec:AAOI:revenue", ["AAOI"], strength="primary", claim_type="fact", themes=["primary-source"]),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
        item("github:SIVE:cpo", ["SIVE"]),
    ]
    pack = build_memo_pack(evidence, query="CPO", tickers=["AAOI", "SIVE"], limit=8)

    index = render_memo_pack_index(pack)

    assert "# Serenity Alpha Lab Memo Pack" in index
    assert "| Ticker | Status | Serenity Rating | Confidence | Key Gaps | Memo File | Evidence | Primary/Fact | Risk | Flags |" in index
    assert "| AAOI | ready |" in index
    assert "| SIVE | blocked | not generated | not generated | missing_primary_source, missing_risk_coverage | not generated | 1 | 0 | 0 | missing_primary_source, missing_risk_coverage |" in index


def test_render_memo_pack_sources_lists_primary_evidence_provenance():
    evidence = [
        item(
            "official-report:AAOI:revenue",
            ["AAOI"],
            strength="primary",
            claim_type="fact",
            themes=["annual-report", "primary-source", "revenue"],
            source_excerpt="The Group reported revenue growth from customer demand.",
        ),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
        item("github:AAOI:cpo", ["AAOI"]),
    ]
    pack = build_memo_pack(evidence, query="CPO", tickers=["AAOI"], limit=8)

    sources = render_memo_pack_sources(pack)

    assert "# Evidence Provenance Index" in sources
    assert "## Primary Evidence" in sources
    assert "**Used in memos:** aaoi-memo.md" in sources
    assert "official-report:AAOI:revenue" in sources
    assert "**Source excerpt:** The Group reported revenue growth from customer demand." in sources


def test_render_memo_pack_sources_deduplicates_shared_evidence_usage():
    evidence = [
        item(
            "official-report:shared:revenue",
            ["AAOI", "SIVE"],
            strength="primary",
            claim_type="fact",
            themes=["annual-report", "primary-source", "revenue", "CPO"],
            source_excerpt="Shared source excerpt used by more than one memo.",
        ),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
        item("risk:SIVE", ["SIVE"], direction="negative", claim_type="risk"),
    ]
    pack = build_memo_pack(evidence, query="CPO", tickers=["AAOI", "SIVE"], limit=8)

    sources = render_memo_pack_sources(pack)

    assert sources.count("- **official-report:shared:revenue**") == 1
    assert "**Tickers:** AAOI, SIVE" in sources
    assert "**Used in memos:** aaoi-memo.md, sive-memo.md" in sources


def test_write_memo_pack_writes_sources_index(tmp_path):
    evidence = [
        item(
            "official-report:AAOI:revenue",
            ["AAOI"],
            strength="primary",
            claim_type="fact",
            themes=["annual-report", "primary-source", "revenue"],
            source_excerpt="The Group reported revenue growth from customer demand.",
        ),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
    ]
    pack = build_memo_pack(evidence, query="CPO", tickers=["AAOI"], limit=8)

    write_memo_pack(pack, tmp_path)

    sources_path = tmp_path / "sources.md"
    assert sources_path.exists()
    assert "official-report:AAOI:revenue" in sources_path.read_text(encoding="utf-8")


def test_write_memo_pack_removes_stale_generated_memos(tmp_path):
    stale_memo = tmp_path / "sive-memo.md"
    stale_memo.write_text("stale memo", encoding="utf-8")
    (tmp_path / "index.md").write_text("stale index", encoding="utf-8")
    (tmp_path / "sources.md").write_text("stale sources", encoding="utf-8")
    evidence = [
        item("sec:AAOI:revenue", ["AAOI"], strength="primary", claim_type="fact", themes=["primary-source"]),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
    ]
    pack = build_memo_pack(evidence, query="CPO", tickers=["AAOI"], limit=8)

    write_memo_pack(pack, tmp_path)

    assert not stale_memo.exists()
    assert (tmp_path / "aaoi-memo.md").exists()
    assert "# Serenity Alpha Lab Memo Pack" in (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "# Evidence Provenance Index" in (tmp_path / "sources.md").read_text(encoding="utf-8")


def test_build_memo_pack_can_generate_chinese_memos():
    evidence = [
        item("sec:AAOI:revenue", ["AAOI"], strength="primary", claim_type="fact", themes=["primary-source"]),
        item("risk:AAOI", ["AAOI"], direction="negative", claim_type="risk"),
    ]

    pack = build_memo_pack(evidence, query="存储芯片", tickers=["AAOI"], limit=8, language="zh")

    assert len(pack.memos) == 1
    assert "# Serenity Alpha Lab 研究备忘录" in pack.memos[0].markdown
    assert "**研究问题:** 存储芯片" in pack.memos[0].markdown
    assert "## 怀疑者复核" in pack.memos[0].markdown
