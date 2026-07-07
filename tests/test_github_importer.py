from datetime import date
from pathlib import Path

from serenity_alpha_lab.evidence import load_evidence
from serenity_alpha_lab.github_importer import (
    GitHubDocument,
    documents_to_evidence,
    import_github_repos,
    load_repo_specs,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_load_repo_specs_from_manifest():
    specs = load_repo_specs(FIXTURES / "github_repo_manifest.json")

    assert len(specs) == 1
    assert specs[0].full_name == "example/serenity-skill"
    assert specs[0].candidate_paths == ["README.md"]
    assert specs[0].published_at.isoformat() == "2026-07-04"


def test_documents_to_evidence_extracts_cpo_bottleneck_section():
    repo = load_repo_specs(FIXTURES / "github_repo_manifest.json")[0]
    doc = GitHubDocument(
        repo=repo,
        path="README.md",
        source_url="https://github.com/example/serenity-skill/blob/main/README.md",
        content=(FIXTURES / "github_readme.md").read_text(encoding="utf-8"),
    )

    items = documents_to_evidence([doc], imported_at=date(2026, 7, 4))

    assert len(items) >= 2
    cpo_item = next(item for item in items if "CPO" in item.themes)
    assert cpo_item.source_url.endswith("/README.md")
    assert "SIVE" in cpo_item.tickers
    assert "LITE" in cpo_item.tickers
    assert cpo_item.direction == "positive"
    assert cpo_item.claim_type == "inference"
    assert cpo_item.factor_impacts["bottleneck_scarcity"] > 0
    assert "MIT" not in cpo_item.tickers
    assert "AD" not in cpo_item.tickers


def test_documents_to_evidence_marks_skeptic_sections_as_negative():
    repo = load_repo_specs(FIXTURES / "github_repo_manifest.json")[0]
    doc = GitHubDocument(
        repo=repo,
        path="README.md",
        source_url="https://github.com/example/serenity-skill/blob/main/README.md",
        content=(FIXTURES / "github_readme.md").read_text(encoding="utf-8"),
    )

    items = documents_to_evidence([doc], imported_at=date(2026, 7, 4))
    risk_item = next(item for item in items if "crowding" in item.theme_tokens)

    assert risk_item.direction == "negative"
    assert risk_item.claim_type == "risk"
    assert risk_item.factor_impacts["crowding_risk"] > 0


def test_documents_to_evidence_does_not_mark_methodology_as_negative_for_generic_risk_word():
    repo = load_repo_specs(FIXTURES / "github_repo_manifest.json")[0]
    doc = GitHubDocument(
        repo=repo,
        path="README.md",
        source_url="https://github.com/example/serenity-skill/blob/main/README.md",
        content=(
            "# Serenity method\n\n"
            "This Serenity method asks the analyst to list evidence, main risk, and invalidation checks "
            "while mapping $SIVE through the CPO supply chain."
        ),
    )

    items = documents_to_evidence([doc], imported_at=date(2026, 7, 4))

    assert len(items) == 1
    assert items[0].direction == "positive"
    assert items[0].claim_type == "methodology"
    assert "crowding_risk" not in items[0].factor_impacts


def test_import_github_repos_writes_deduped_jsonl(tmp_path):
    repo = load_repo_specs(FIXTURES / "github_repo_manifest.json")[0]
    content = (FIXTURES / "github_readme.md").read_text(encoding="utf-8")

    def fake_fetcher(_repo):
        return [
            GitHubDocument(
                repo=repo,
                path="README.md",
                source_url="https://github.com/example/serenity-skill/blob/main/README.md",
                content=content,
            ),
            GitHubDocument(
                repo=repo,
                path="README.md",
                source_url="https://github.com/example/serenity-skill/blob/main/README.md",
                content=content,
            ),
        ]

    out = tmp_path / "github_evidence.jsonl"
    items = import_github_repos([repo], out, fetcher=fake_fetcher, imported_at=date(2026, 7, 4))

    assert len(items) == len({item.id for item in items})
    loaded = load_evidence(out)
    assert len(loaded) == len(items)


def test_import_github_repos_semantically_dedupes_same_claim_with_different_heading(tmp_path):
    repo = load_repo_specs(FIXTURES / "github_repo_manifest.json")[0]
    content_a = "# First\n\n$SIVE is a CPO laser bottleneck candidate in the optical supply chain."
    content_b = "# Second\n\nSIVE is a CPO laser bottleneck candidate in the optical supply chain."

    def fake_fetcher(_repo):
        return [
            GitHubDocument(
                repo=repo,
                path="README.md",
                source_url="https://github.com/example/serenity-skill/blob/main/README.md",
                content=content_a,
            ),
            GitHubDocument(
                repo=repo,
                path="SKILL.md",
                source_url="https://github.com/example/serenity-skill/blob/main/SKILL.md",
                content=content_b,
            ),
        ]

    out = tmp_path / "github_evidence.jsonl"
    items = import_github_repos([repo], out, fetcher=fake_fetcher, imported_at=date(2026, 7, 4))

    assert len(items) == 1
