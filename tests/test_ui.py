from pathlib import Path

from serenity_alpha_lab import ui as ui_module
from serenity_alpha_lab.ui import (
    ReusableTCPServer,
    _copy_pack_for_serving,
    build_dashboard,
    load_metrics_catalog,
    render_dashboard_html,
)


def _write_pack(tmp_path: Path) -> tuple[Path, Path]:
    readiness = tmp_path / "readiness.md"
    readiness.write_text(
        "\n".join(
            [
                "# Batch Readiness Report",
                "",
                "**Research question:** CPO laser bottleneck revenue profitability",
                "**Retrieval limit per ticker:** 16",
                "",
                "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |",
                "|---:|---|---|---:|---:|---:|---:|---:|---|",
                "| 1 | SIVE | ready | 16 | 3 | 6 | 6% | 0% | none |",
                "| 2 | AAOI | ready | 15 | 3 | 5 | 6% | 0% | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "index.md").write_text(
        "\n".join(
            [
                "# Serenity Alpha Lab Memo Pack",
                "",
                "**Research question:** CPO laser bottleneck revenue profitability",
                "**Retrieval limit per ticker:** 16",
                "",
                "| Ticker | Status | Memo File | Evidence | Primary/Fact | Risk | Flags |",
                "|---|---|---|---:|---:|---:|---|",
                "| SIVE | ready | sive-memo.md | 16 | 3 | 6 | none |",
                "| AAOI | ready | aaoi-memo.md | 15 | 3 | 5 | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sources.md").write_text(
        "\n".join(
            [
                "# Evidence Provenance Index",
                "",
                "## Primary Evidence",
                "",
                "- **official-report:SIVE:net-sales-2025** [Sivers Annual Report](https://example.com/sive.pdf) (2026-05-01, primary, fact)",
                "  - **Tickers:** SIVE",
                "  - **Used in memos:** sive-memo.md",
                "  - **Claim:** Sivers reported 2025 net sales growth.",
                "  - **Source excerpt:** Net sales increased by 40% year over year.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sive-memo.md").write_text(
        "\n".join(
            [
                "# Serenity Alpha Lab Memo",
                "",
                "**Ticker focus:** SIVE",
                "**Evidence count:** 16",
                "**Composite research score:** 24/100",
                "**Serenity rating:** Watchlist Candidate",
                "**Research confidence:** low",
                "**Key gaps:** primary_source_depth, low_score",
                "",
                "## Thesis Summary",
                "",
                "SIVE has a provisional Serenity-style research case across optical components.",
                "",
                "## Source Coverage",
                "",
                "**Coverage counts:** evidence 16, focus ticker 16, primary/fact 3, risk 6, external non-Serenity 3",
                "",
                "## Skeptic Review",
                "",
                "- Risk evidence remains material.",
                "",
                "## Invalidation Conditions",
                "",
                "- SIVE fails to show customer qualification progress.",
                "",
                "## Disclaimer",
                "",
                "This memo is research only.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "aaoi-memo.md").write_text(
        "# Serenity Alpha Lab Memo\n\n**Ticker focus:** AAOI\n\n## Thesis Summary\n\nAAOI memo preview.\n",
        encoding="utf-8",
    )
    return readiness, pack_dir


def test_load_metrics_catalog_normalizes_tickers_and_values(tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text(
        '[{"ticker":" sive ","revenue_growth":"40%","gross_margin":"52%","valuation":"7.2x EV/Sales","momentum":"positive","cycle_position":"early ramp"}]',
        encoding="utf-8",
    )

    catalog = load_metrics_catalog(path)

    assert catalog["SIVE"]["revenue_growth"] == "40%"
    assert catalog["SIVE"]["gross_margin"] == "52%"
    assert catalog["SIVE"]["valuation"] == "7.2x EV/Sales"
    assert catalog["SIVE"]["momentum"] == "positive"
    assert catalog["SIVE"]["cycle_position"] == "early ramp"


def test_render_dashboard_html_contains_product_sections():
    html = render_dashboard_html(
        title="Serenity Alpha Lab",
        query="CPO laser bottleneck revenue profitability",
        readiness_rows=[
            {
                "ticker": "SIVE",
                "status": "ready",
                "evidence": "16",
                "primary": "3",
                "risk": "6",
                "flags": "none",
            }
        ],
        memo_rows=[
            {
                "ticker": "SIVE",
                "status": "ready",
                "memo_file": "sive-memo.md",
                "evidence": "16",
                "primary": "3",
                "risk": "6",
                "rating": "Watchlist Candidate",
                "confidence": "low",
                "gaps": "primary_source_depth, low_score",
                "flags": "none",
            }
        ],
        memo_previews=[
            {
                "ticker": "SIVE",
                "memo_file": "sive-memo.md",
                "score": "24/100",
                "rating": "Watchlist Candidate",
                "confidence": "low",
                "gaps": "primary_source_depth, low_score",
                "thesis": "SIVE has a provisional Serenity-style research case.",
                "coverage": "evidence 16, primary/fact 3, risk 6",
                "risks": ["Risk evidence remains material."],
                "invalidations": ["SIVE fails to show customer qualification progress."],
            }
        ],
        metrics_by_ticker={
            "SIVE": {
                "revenue_growth": "40%",
                "gross_margin": "52%",
                "valuation": "7.2x EV/Sales",
                "momentum": "positive",
                "cycle_position": "early ramp",
            }
        },
        analysis_history=[
            {
                "query": "存储芯片",
                "intent": "industry",
                "canonical_theme": "memory",
                "href_zh": "analyses/topic-602483dcf3/index.zh.html",
                "href_en": "analyses/topic-602483dcf3/index.html",
                "candidate_tickers": "MU, SNDK, GIGADEVICE",
            }
        ],
        primary_sources=[
            {
                "id": "official-report:SIVE:net-sales-2025",
                "title": "Sivers Annual Report",
                "url": "https://example.com/sive.pdf",
                "claim": "Sivers reported 2025 net sales growth.",
                "excerpt": "Net sales increased by 40% year over year.",
                "tickers": "SIVE",
                "memos": "sive-memo.md",
            }
        ],
        operational_reports=[
            {
                "title_key": "coverage_matrix_title",
                "href": "reports/universe-coverage-matrix.md",
            },
            {
                "title_key": "analysis_manifest_title",
                "href": "analysis-manifest.json",
            },
            {
                "title_key": "acquisition_queue_title",
                "href": "reports/evidence-acquisition-queue.md",
                "tasks": [
                    {
                        "priority": "high",
                        "ticker": "MU",
                        "gap": "missing_primary_source",
                        "source_target": "Primary filing, company release, audited fact, or official investor material",
                        "search_prompt": "MU primary filing HBM",
                        "rationale": "Primary/fact evidence is required before this candidate can clear the research confidence gate.",
                        "acceptance_criteria": "Source title, URL, and source excerpt must directly support the task claim.",
                        "after_import": "Import the evidence, rerun the analysis, and confirm the quality gate improves.",
                    }
                ],
            }
        ],
    )

    assert "<!doctype html>" in html.lower()
    assert "Serenity Alpha Lab" in html
    assert "Research Workflow" in html
    assert "Define scope" in html
    assert "Compare candidates" in html
    assert "Read reports" in html
    assert "Close evidence gaps" in html
    assert "Try HBM" in html
    assert "Try memory chips" in html
    assert 'data-example-query="HBM"' in html
    assert 'data-example-query="memory chips"' in html
    assert "launchExampleAnalysis" in html
    assert "Run Center" in html
    assert "Current run" in html
    assert "Waiting for an analysis request." in html
    assert "Queued analysis:" in html
    assert "Analysis queued..." in html
    assert "Resolve universe" in html
    assert "Build memo pack" in html
    assert "Publish dashboard" in html
    assert "Open report" in html
    assert "Retry last run" in html
    assert 'id="run-center"' in html
    assert 'data-run-step="resolve"' in html
    assert 'data-run-step="publish"' in html
    assert "initializeRunCenter" in html
    assert "updateRunCenter" in html
    assert "syncRunCenterFromServer" in html
    assert "/api/runs" in html
    assert "/api/analyze-jobs" in html
    assert "submitAnalyzeJob" in html
    assert "job_id" in html
    assert "retry_job_id" in html
    assert "retryAnalyzeJob" in html
    assert "openJobDetailPanel" in html
    assert "cancelAnalyzeJob" in html
    assert "Job detail" in html
    assert "Cancel job" in html
    assert "queued_at" in html
    assert "completed_at" in html
    assert "startRunPolling" in html
    assert "stopRunPolling" in html
    assert "scheduleRunPolling" in html
    assert "runPollInterval" in html
    assert "data-run-polling=\"idle\"" in html
    assert "Polling run status..." in html
    assert "Report ready." in html
    assert "Open latest report" in html
    assert "Run History" in html
    assert "No run history yet." in html
    assert "Queued" in html
    assert "Quality in run history" in html
    assert "Candidate tickers in run history" in html
    assert "Open analysis manifest" in html
    assert 'id="run-history-list"' in html
    assert "renderRunHistory" in html
    assert "openRunManifest" in html
    assert "manifest_href" in html
    assert "Analysis Briefing" in html
    assert "Top candidate" in html
    assert "Coverage state" in html
    assert "Primary gap" in html
    assert "Next actions" in html
    assert "Open top report" in html
    assert "Review evidence tasks" in html
    assert 'id="analysis-briefing"' in html
    assert 'data-briefing-top-ticker="SIVE"' in html
    assert "Research Action Workbench" in html
    assert "Action queue" in html
    assert "Quality gap to close" in html
    assert "Open evidence tasks" in html
    assert "Open deliverable report" in html
    assert "Open acquisition queue" in html
    assert "Copy next research prompt" in html
    assert "SIVE primary_source_depth low_score evidence" in html
    assert 'id="research-action-workbench"' in html
    assert 'data-research-action-gap="primary_source_depth, low_score"' in html
    assert 'data-research-action-ticker="SIVE"' in html
    assert 'data-copy-text="SIVE primary_source_depth low_score evidence"' in html
    assert "Decision Workbench" in html
    assert "Ranking rationale" in html
    assert "Key drivers" in html
    assert "Counter-thesis risks" in html
    assert "Why not other candidates" in html
    assert "Research triage only" in html
    assert 'id="decision-workbench"' in html
    assert 'data-decision-top-ticker="SIVE"' in html
    assert "Sort candidates by" in html
    assert "Serenity score" in html
    assert "Evidence coverage" in html
    assert "Primary source coverage" in html
    assert "Risk coverage" in html
    assert "Sort explanation" in html
    assert "Interactive candidate ranking" in html
    assert 'id="decision-sort"' in html
    assert 'id="decision-sort-explanation"' in html
    assert 'data-decision-candidate' in html
    assert "initializeDecisionRanking" in html
    assert "updateDecisionRanking" in html
    assert "Report Quality Gate" in html
    assert "Publish status" in html
    assert "Needs evidence" in html
    assert "Quality score" in html
    assert "Quality checklist" in html
    assert "Evidence depth" in html
    assert "Primary source depth" in html
    assert "Risk coverage" in html
    assert 'id="report-quality-gate"' in html
    assert 'data-quality-status="needs-evidence"' in html
    assert "Saved Research Workspace" in html
    assert "Saved reports" in html
    assert "Candidate marks" in html
    assert "Saved sort preference" in html
    assert "Quality gate snapshot" in html
    assert "Save workspace" in html
    assert "Clear workspace" in html
    assert 'id="saved-workspace"' in html
    assert "initializeSavedWorkspace" in html
    assert "saveWorkspaceState" in html
    assert "renderSavedWorkspace" in html
    assert "workspaceStorageKey" in html
    assert "data-workspace-report" in html
    assert "data-workspace-candidate" in html
    assert "Research Project Library" in html
    assert "Save as project" in html
    assert "Project status" in html
    assert "Pending evidence" in html
    assert "Reviewable" in html
    assert "Delivered" in html
    assert "Needs rerun" in html
    assert 'id="research-project-library"' in html
    assert 'id="project-library-list"' in html
    assert "projectLibraryStorageKey" in html
    assert "saveResearchProject" in html
    assert "renderResearchProjectLibrary" in html
    assert "syncResearchProjectLibraryFromServer" in html
    assert "writeResearchProjectToServer" in html
    assert "clearResearchProjectsOnServer" in html
    assert "/api/projects" in html
    assert "Server-backed project library" in html
    assert "Filter projects by status" in html
    assert "All project statuses" in html
    assert "Project comparison summary" in html
    assert "Total projects" in html
    assert "Average quality score" in html
    assert "Evidence backlog" in html
    assert "Delivered projects" in html
    assert "Search saved projects" in html
    assert "Sort saved projects" in html
    assert "Project tags" in html
    assert "All project tags" in html
    assert "Tag: needs evidence" in html
    assert "Tag: high quality" in html
    assert "Tag: delivered" in html
    assert "Project next action" in html
    assert "All next actions" in html
    assert "Collect evidence projects" in html
    assert "Review report projects" in html
    assert "Rerun analysis projects" in html
    assert "Archive projects" in html
    assert "Next-action queue" in html
    assert "Queue by workflow step" in html
    assert "Filter to collect evidence" in html
    assert "Filter to review reports" in html
    assert "Filter to rerun analysis" in html
    assert "Filter to archive projects" in html
    assert "Project queue handoff" in html
    assert "Copy queue handoff" in html
    assert "Queue handoff copied" in html
    assert "Research-only queue handoff" in html
    assert "Queue handoff action" in html
    assert "Queue handoff preview" in html
    assert "Filtered project handoff" in html
    assert "Copy filtered handoff" in html
    assert "Filtered handoff copied" in html
    assert "Filtered handoff preview" in html
    assert "Filtered item count" in html
    assert "Review handoff before copying" in html
    assert "Handoff item count" in html
    assert "Project owner queue" in html
    assert "Filter by owner" in html
    assert "All owners" in html
    assert "Unassigned owner" in html
    assert "Evidence owner" in html
    assert "Report reviewer" in html
    assert "Rerun owner" in html
    assert "Archive owner" in html
    assert "Assign project owner" in html
    assert "Owner changed" in html
    assert "Project detail drawer" in html
    assert "Review project" in html
    assert "Project review panel" in html
    assert "Project detail quality" in html
    assert "Project detail gap" in html
    assert "Project detail status" in html
    assert "Next review action" in html
    assert "Open report from detail" in html
    assert "Project review action panel" in html
    assert "Recommended review actions" in html
    assert "Close evidence gap" in html
    assert "Rerun analysis" in html
    assert "Mark delivered" in html
    assert "Open report from action panel" in html
    assert "Action logged" in html
    assert "Evidence gap linked task" in html
    assert "Jump to evidence task" in html
    assert "Rerun with project context" in html
    assert "Quality after rerun" in html
    assert "Evidence verification rerun loop" in html
    assert "Auto-rerun after verification" in html
    assert "Rerun verified task" in html
    assert "Quality delta after rerun" in html
    assert "Project evidence audit log" in html
    assert "Evidence contribution history" in html
    assert "Verified task audit trail" in html
    assert "Quality contribution" in html
    assert "Project review timeline" in html
    assert "Review event history" in html
    assert "Collaboration event view" in html
    assert "Filter review events" in html
    assert "All review events" in html
    assert "Status events" in html
    assert "Owner events" in html
    assert "Detail events" in html
    assert "Comparison events" in html
    assert "Queue handoff events" in html
    assert "Latest project activity" in html
    assert "Project activity summary" in html
    assert "Activity count" in html
    assert "Latest activity" in html
    assert "No activity yet" in html
    assert "Project activity filter" in html
    assert "All activity states" in html
    assert "Has activity" in html
    assert "No activity" in html
    assert "Most active" in html
    assert "No review events yet." in html
    assert "Log review event" in html
    assert "Server-backed review event log" in html
    assert "Status changed" in html
    assert "Owner changed" in html
    assert "Detail opened" in html
    assert "Comparison brief copied" in html
    assert "Queue handoff copied" in html
    assert "queue-handoff-copied" in html
    assert "Historical comparison matrix" in html
    assert "Select for comparison" in html
    assert "Compare selected projects" in html
    assert "Copy comparison brief" in html
    assert "Comparison brief copied" in html
    assert "Research-only comparison brief" in html
    assert "Comparison topic" in html
    assert "Comparison top candidate" in html
    assert "Comparison quality" in html
    assert "Comparison gap" in html
    assert "Comparison status" in html
    assert "Comparison report" in html
    assert 'id="project-status-filter"' in html
    assert 'id="project-library-search"' in html
    assert 'id="project-library-sort"' in html
    assert 'id="project-tag-filter"' in html
    assert 'id="project-next-action-filter"' in html
    assert 'id="project-owner-filter"' in html
    assert 'id="project-activity-filter"' in html
    assert 'id="project-next-action-queue-summary"' in html
    assert 'id="project-owner-queue-summary"' in html
    assert 'id="project-queue-handoff-preview"' in html
    assert 'id="project-comparison-summary"' in html
    assert 'id="project-detail-drawer"' in html
    assert 'id="project-detail-title"' in html
    assert 'id="project-detail-body"' in html
    assert 'id="project-detail-quality"' in html
    assert 'id="project-detail-actions"' in html
    assert 'id="project-review-action-panel"' in html
    assert 'id="project-review-action-list"' in html
    assert 'id="project-review-loop-status"' in html
    assert 'id="project-review-timeline"' in html
    assert 'id="project-review-event-filter"' in html
    assert 'id="project-review-event-summary"' in html
    assert 'id="project-review-timeline-list"' in html
    assert 'id="project-comparison-matrix"' in html
    assert 'id="project-comparison-table"' in html
    assert "filterResearchProjects" in html
    assert "sortResearchProjects" in html
    assert "projectTagForRecord" in html
    assert "projectNextActionLabel" in html
    assert "renderProjectNextActionQueueSummary" in html
    assert "filterProjectNextActionQueue" in html
    assert "projectOwnerLabel" in html
    assert "projectOwnerForRecord" in html
    assert "renderProjectOwnerQueueSummary" in html
    assert "filterProjectOwnerQueue" in html
    assert "projectOwnerOptions" in html
    assert "updateResearchProjectOwner" in html
    assert "buildProjectQueueHandoffBrief" in html
    assert "copyProjectQueueHandoffBrief" in html
    assert "renderProjectQueueHandoffPreview" in html
    assert "buildFilteredProjectQueueHandoffBrief" in html
    assert "copyFilteredProjectQueueHandoffBrief" in html
    assert "renderFilteredProjectQueueHandoffPreview" in html
    assert "projectLibraryFilteredRecords" in html
    assert "openProjectDetailDrawer" in html
    assert "closeProjectDetailDrawer" in html
    assert "renderProjectDetailDrawer" in html
    assert "projectReviewActionPanelItems" in html
    assert "renderProjectReviewActionPanel" in html
    assert "handleProjectReviewAction" in html
    assert "markProjectDeliveredFromDrawer" in html
    assert "rerunProjectAnalysisFromDrawer" in html
    assert "projectEvidenceTaskTarget" in html
    assert "focusProjectEvidenceTask" in html
    assert "projectRerunUrl" in html
    assert "persistProjectRerunContext" in html
    assert "applyProjectRerunContext" in html
    assert "verifiedTaskRerunContext" in html
    assert "handleVerifiedTaskRerun" in html
    assert "updateVerifiedTaskRerunLoop" in html
    assert "qualityDeltaAfterRerun" in html
    assert "projectEvidenceAuditLogStorageKey" in html
    assert "readProjectEvidenceAuditLog" in html
    assert "writeProjectEvidenceAuditLog" in html
    assert "appendProjectEvidenceAuditEntry" in html
    assert "renderProjectEvidenceAuditLog" in html
    assert "renderProjectEvidenceQualityDeltaSummary" in html
    assert "projectEvidenceQualitySummary" in html
    assert "renderProjectEvidenceImpactSummary" in html
    assert "Latest evidence impact" in html
    assert "projectEvidenceProgressSummary" in html
    assert "renderProjectEvidenceProgressSummary" in html
    assert "Evidence progress" in html
    assert "projectNextActionSummary" in html
    assert "renderProjectNextActionSummary" in html
    assert "Workflow next step" in html
    assert 'id="project-evidence-quality-delta-summary"' in html
    assert "Latest quality delta" in html
    assert "syncProjectEvidenceAuditLogFromServer" in html
    assert "writeProjectEvidenceAuditEntryToServer" in html
    assert "clearProjectEvidenceAuditLogOnServer" in html
    assert "/api/project-evidence-audits" in html
    assert "projectReviewTimelineStorageKey" in html
    assert "readProjectReviewTimeline" in html
    assert "writeProjectReviewTimeline" in html
    assert "appendProjectReviewEvent" in html
    assert "projectReviewActivitySummary" in html
    assert "renderProjectActivitySummary" in html
    assert "projectActivityState" in html
    assert "projectActivityStateLabel" in html
    assert "filterProjectActivity" in html
    assert "projectReviewEventTypeLabel" in html
    assert "renderProjectReviewEventSummary" in html
    assert "filterProjectReviewEvents" in html
    assert "renderProjectReviewTimeline" in html
    assert "syncProjectReviewTimelineFromServer" in html
    assert "writeProjectReviewEventToServer" in html
    assert "clearProjectReviewEventsOnServer" in html
    assert "/api/project-events" in html
    assert "renderProjectComparisonSummary" in html
    assert "renderProjectComparisonMatrix" in html
    assert "toggleProjectComparisonSelection" in html
    assert "updateProjectComparisonMatrix" in html
    assert "buildProjectComparisonBrief" in html
    assert "copyProjectComparisonBrief" in html
    assert "data-project-filter-status" in html
    assert "data-project-quality-score" in html
    assert "data-project-tag" in html
    assert "data-project-next-action-filter" in html
    assert "data-project-owner-filter" in html
    assert "data-project-owner-value" in html
    assert "data-project-owner-select" in html
    assert "data-project-owner-queue" in html
    assert "data-project-owner-count" in html
    assert "data-project-review-event-filter" in html
    assert "data-project-review-event-count" in html
    assert "data-project-activity-summary" in html
    assert "data-project-activity-count" in html
    assert "data-project-latest-activity" in html
    assert "data-project-activity-filter" in html
    assert "data-project-activity-state" in html
    assert "data-project-next-action-queue" in html
    assert "data-project-next-action-count" in html
    assert "data-project-queue-handoff" in html
    assert "data-project-queue-handoff-action" in html
    assert "data-project-queue-handoff-preview" in html
    assert "data-project-queue-handoff-items" in html
    assert "data-filtered-project-handoff" in html
    assert "data-filtered-project-handoff-action" in html
    assert "data-filtered-project-handoff-preview" in html
    assert "data-filtered-project-handoff-items" in html
    assert "data-project-search-text" in html
    assert "data-project-detail-id" in html
    assert "data-project-detail-quality" in html
    assert "data-project-detail-gap" in html
    assert "data-project-review-action" in html
    assert "data-project-review-action-type" in html
    assert "data-project-review-action-project" in html
    assert "data-project-evidence-task-target" in html
    assert "data-project-rerun-context" in html
    assert "data-project-quality-after-rerun" in html
    assert "data-verified-task-rerun" in html
    assert "data-verified-task-rerun-context" in html
    assert "data-quality-delta-after-rerun" in html
    assert "data-project-evidence-audit" in html
    assert "data-project-evidence-audit-type" in html
    assert "data-project-quality-delta" in html
    assert "data-project-evidence-impact" in html
    assert "data-project-evidence-progress" in html
    assert "data-project-verified-tasks" in html
    assert "data-project-next-action" in html
    assert "data-project-next-action-priority" in html
    assert "data-project-evidence-audit-quality-delta" in html
    assert "data-project-review-event" in html
    assert "data-project-review-event-type" in html
    assert "data-project-review-event-project" in html
    assert "data-project-compare-id" in html
    assert "data-project-compare-selected" in html
    assert "data-project-comparison-brief" in html
    assert "data-project-status" in html
    assert "data-project-query" in html
    assert "Deliverable Research Report" in html
    assert "Export-ready brief" in html
    assert "Open deliverable report" in html
    assert "Print / Save PDF" in html
    assert "Share handoff" in html
    assert "Copy report link" in html
    assert "Copy manifest link" in html
    assert "copyShareLink" in html
    assert 'data-share-href="reports/deliverable-research-report.md"' in html
    assert 'data-share-href="analysis-manifest.json"' in html
    assert "Report Delivery Package" in html
    assert "Open or copy the deliverable, manifest, coverage matrix, and evidence queue from one compact panel." in html
    assert "Delivery quality summary" in html
    assert "Research-only package" in html
    assert "Top candidate" in html
    assert "Remaining gaps" in html
    assert 'data-delivery-quality-status="needs-evidence"' in html
    assert 'data-delivery-quality-score="70"' in html
    assert 'data-delivery-quality-candidate="SIVE"' in html
    assert "Copy handoff bundle" in html
    assert "copyHandoffBundle" in html
    assert 'data-handoff-artifact-title="Deliverable Research Report"' in html
    assert 'data-handoff-artifact-href="reports/deliverable-research-report.md"' in html
    assert 'id="delivery-package"' in html
    assert 'data-package-artifact="deliverable-report"' in html
    assert 'data-package-artifact="analysis-manifest"' in html
    assert 'data-package-artifact="coverage-matrix"' in html
    assert 'data-package-artifact="evidence-queue"' in html
    assert 'data-memo-href="analysis-manifest.json"' in html
    assert 'data-memo-href="reports/universe-coverage-matrix.md"' in html
    assert 'data-memo-href="reports/evidence-acquisition-queue.md"' in html
    assert "deliverable-research-report.md" in html
    assert 'id="deliverable-report"' in html
    assert "printDeliverableReport" in html
    assert 'data-report-type="deliverable"' in html
    assert "openRunReport" in html
    assert "rerunRunRecord" in html
    assert "Open report" in html
    assert "Rerun" in html
    assert "Failure details" in html
    assert "retryLastRun" in html
    assert "Readiness" in html
    assert "Memo Pack" in html
    assert "Candidate Comparison" in html
    assert "Revenue Growth" in html
    assert "Gross Margin" in html
    assert "Valuation" in html
    assert "Momentum" in html
    assert "Cycle Position" in html
    assert "Evidence Provenance" in html
    assert "Research only" in html
    assert "Recent Reports" in html
    assert "Report Workbench" in html
    assert "Filter by report type" in html
    assert "All report types" in html
    assert "Generated analyses" in html
    assert "Operational reports" in html
    assert "Open in reader" in html
    assert "Open full page" in html
    assert 'id="memo-drawer-toolbar"' in html
    assert 'id="memo-drawer-current-link"' in html
    assert "Current report link" in html
    assert "Copy current link" in html
    assert 'id="memo-drawer-outline"' in html
    assert 'id="memo-drawer-highlights"' in html
    assert "Reader outline" in html
    assert "Report highlights" in html
    assert "Jump to section" in html
    assert "copyCurrentReaderLink" in html
    assert "openCurrentReaderReport" in html
    assert "renderReaderOutline" in html
    assert "extractReaderHighlights" in html
    assert "scrollReaderSection" in html
    assert "reviewReportWorkbench" in html
    assert "filterReportWorkbench" in html
    assert "report-workbench-type" in html
    assert "data-report-workbench-item" in html
    assert 'data-report-type="generated"' in html
    assert 'data-report-type="operational"' in html
    assert 'data-memo-href="analyses/topic-602483dcf3/index.html"' in html
    assert 'onclick="openMemoDrawer(this)"' in html
    assert "存储芯片" in html
    assert 'href="analyses/topic-602483dcf3/index.html"' in html
    assert "Watchlist Candidate" in html
    assert "40%" in html
    assert "7.2x EV/Sales" in html
    assert "early ramp" in html
    assert "primary_source_depth" in html
    assert "<td>SIVE</td>" in html
    assert "primary_source_depth, low_score" in html
    assert "SIVE" in html
    assert "sive-memo.md" in html
    assert "official-report:SIVE:net-sales-2025" in html
    assert "viewport" in html
    assert 'type="search"' in html
    assert 'action="/analyze"' in html
    assert "Start analysis" in html
    assert "Preview analysis scope" in html
    assert "Confirm and generate" in html
    assert "Input Preview" in html
    assert "Detected input type" in html
    assert "Canonical theme" in html
    assert "Candidate tickers" in html
    assert "Evidence coverage" in html
    assert "Expected outputs" in html
    assert "parseAnalysisInputPreview" in html
    assert "fetchAnalysisInputPreview" in html
    assert "/api/resolve-topic" in html
    assert "Backend-backed resolver" in html
    assert "Preview unavailable; using local fallback." in html
    assert "renderAnalysisInputPreview" in html
    assert "confirmAnalysisLaunch" in html
    assert "data-preview-intent" in html
    assert "Report, comparison table, evidence tasks, and operational reports" in html
    assert "Generating analysis..." in html
    assert 'id="launch-status"' in html
    assert 'aria-live="polite"' in html
    assert "handleLaunchSubmit" in html
    assert 'data-filter-status="ready"' in html
    assert 'data-ticker="SIVE"' in html
    assert "filterDashboard" in html
    assert "Showing" in html
    assert "Evidence Tasks" in html
    assert "Primary filing, company release, audited fact, or official investor material" in html
    assert "MU primary filing HBM" in html
    assert 'data-copy-text="MU primary filing HBM"' in html
    assert "copyTaskPrompt" in html
    assert "Task Status" in html
    assert "To collect" in html
    assert "Collected" in html
    assert "Verified" in html
    assert "Add Evidence" in html
    assert "Paste a short primary-source excerpt that directly supports this task." in html
    assert "Submitting evidence..." in html
    assert "Required: source title, source URL, and a traceable excerpt." in html
    assert "Imported Evidence" in html
    assert 'action="/ingest-evidence"' in html
    assert 'onsubmit="return handleEvidenceImportSubmit(this);"' in html
    assert 'name="source_title"' in html
    assert 'name="source_url"' in html
    assert 'name="source_excerpt"' in html
    assert 'name="query" value="CPO laser bottleneck revenue profitability"' in html
    assert 'name="ticker" value="MU"' in html
    assert 'data-loading-text="Submitting evidence..."' in html
    assert 'aria-live="polite"' in html
    assert "handleEvidenceImportSubmit" in html
    assert "data-task-status" in html
    assert "initializeTaskStatuses" in html
    assert "updateTaskStatus" in html
    assert "syncTaskStatusesFromServer" in html
    assert "writeTaskStatusToServer" in html
    assert "clearTaskStatusesOnServer" in html
    assert "/api/task-statuses" in html
    assert "localStorage" in html


def test_render_dashboard_html_localizes_chinese_metric_values():
    html = render_dashboard_html(
        title="Serenity Alpha Lab",
        query="半导体设备",
        readiness_rows=[],
        memo_rows=[
            {
                "ticker": "COHR",
                "status": "ready",
                "memo_file": "cohr-memo.md",
                "evidence": "16",
                "primary": "3",
                "risk": "2",
                "rating": "Watchlist Candidate",
                "confidence": "medium",
                "gaps": "none",
                "flags": "none",
            },
            {
                "ticker": "AAOI",
                "status": "ready",
                "memo_file": "aaoi-memo.md",
                "evidence": "16",
                "primary": "3",
                "risk": "5",
                "rating": "Watchlist Candidate",
                "confidence": "low",
                "gaps": "profitability",
                "flags": "none",
            },
        ],
        memo_previews=[],
        metrics_by_ticker={
            "COHR": {
                "revenue_growth": "source-backed revenue $5.8B",
                "gross_margin": "n/a",
                "valuation": "n/a",
                "momentum": "reported profitable",
                "cycle_position": "source-backed revenue base",
            },
            "AAOI": {
                "revenue_growth": "source-backed revenue $455.7M",
                "gross_margin": "n/a",
                "valuation": "n/a",
                "momentum": "reported loss",
                "cycle_position": "revenue ramp / loss-making",
            },
        },
        primary_sources=[],
        language="zh",
    )

    assert "来源支持收入 $5.8B" in html
    assert "已披露盈利" in html
    assert "来源支持收入基数" in html
    assert "来源支持收入 $455.7M" in html
    assert "已披露亏损" in html
    assert "收入爬坡 / 仍处亏损" in html
    assert "source-backed revenue base" not in html
    assert "reported profitable" not in html


def test_render_dashboard_html_localizes_visible_evidence_tasks():
    html = render_dashboard_html(
        title="Serenity Alpha Lab",
        query="HBM",
        readiness_rows=[],
        memo_rows=[],
        memo_previews=[],
        primary_sources=[],
        operational_reports=[
            {
                "title_key": "acquisition_queue_title",
                "href": "reports/evidence-acquisition-queue.md",
                "tasks": [
                    {
                        "priority": "high",
                        "ticker": "MU",
                        "gap": "missing_primary_source",
                        "source_target": "Primary filing, company release, audited fact, or official investor material",
                        "search_prompt": "MU primary filing HBM",
                    }
                ],
            }
        ],
        language="zh",
    )

    assert "证据任务" in html
    assert "缺少 primary/fact 来源" in html
    assert "Primary filing、公司公告、审计事实或官方投资者材料" in html
    assert "MU primary filing HBM" in html
    assert "复制搜索提示" in html
    assert "任务状态" in html
    assert "待采集" in html
    assert "已采集" in html
    assert "已验证" in html
    assert "补充证据" in html
    assert "来源标题" in html
    assert "来源链接" in html
    assert "来源摘录" in html
    assert "补证原因" in html
    assert "验收标准" in html
    assert "导入后动作" in html
    assert "需要 primary/fact 证据才能提升研究置信度门禁。" in html
    assert "来源标题、链接和原文摘录必须能直接支撑任务声明。" in html
    assert "导入证据后重新生成分析，并确认质量门禁改善。" in html


def test_render_dashboard_html_keeps_evidence_tasks_empty_state_visible():
    html = render_dashboard_html(
        title="Serenity Alpha Lab",
        query="HBM",
        readiness_rows=[],
        memo_rows=[],
        memo_previews=[],
        primary_sources=[],
        operational_reports=[
            {
                "title_key": "acquisition_queue_title",
                "href": "reports/evidence-acquisition-queue.md",
                "tasks": [],
            }
        ],
        language="zh",
    )

    assert "证据任务" in html
    assert "暂无待处理证据任务" in html
    assert "打开采集队列" in html


def test_render_dashboard_html_shows_imported_evidence_history_and_resolved_task():
    html = render_dashboard_html(
        title="Serenity Alpha Lab",
        query="HBM",
        readiness_rows=[],
        memo_rows=[],
        memo_previews=[],
        primary_sources=[],
        operational_reports=[
            {
                "title_key": "acquisition_queue_title",
                "href": "reports/evidence-acquisition-queue.md",
                "tasks": [
                    {
                        "priority": "high",
                        "ticker": "MU",
                        "gap": "missing_primary_source",
                        "source_target": "Primary filing, company release, audited fact, or official investor material",
                        "search_prompt": "MU primary filing HBM",
                    },
                    {
                        "priority": "high",
                        "ticker": "MU",
                        "gap": "missing_risk_evidence",
                        "source_target": "Risk disclosure, litigation, customer concentration, or invalidation source",
                        "search_prompt": "MU risk invalidation HBM",
                    },
                ],
            }
        ],
        imported_evidence=[
            {
                "id": "manual:MU:hbm-primary-source",
                "source_title": "Micron HBM investor update",
                "source_url": "https://investors.micron.com/news-releases/news-release-details/micron-hbm-update",
                "claim": "Micron disclosed a primary-source HBM update relevant to the HBM analysis.",
                "tickers": ["MU"],
                "strength": "primary",
                "claim_type": "fact",
                "published_at": "2026-07-05",
            }
        ],
    )

    assert "Micron HBM investor update" in html
    assert "manual:MU:hbm-primary-source" in html
    assert "Resolved" in html
    assert "Resolved by imported evidence" in html
    assert "Import Impact" in html
    assert "Closed gap: missing_primary_source" in html
    assert "Quality gate impact: rerun complete; review the updated publish status and quality score." in html
    assert "Remaining evidence work: review the next visible task cards before publishing." in html
    assert "Quality before import: not available" in html
    assert "Quality after import: not available" in html
    assert "Quality score change: not available" in html
    assert 'data-task-status="verified"' in html
    assert "No evidence has been imported from this task yet." in html


def test_build_dashboard_loads_manual_intake_history_for_analysis_page(tmp_path, monkeypatch):
    readiness, pack_dir = _write_pack(tmp_path)
    analysis_dir = tmp_path / "ui" / "analyses" / "hbm-6f259a8f14"
    out = analysis_dir / "index.html"
    reports_dir = analysis_dir / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "evidence-acquisition-queue.md").write_text(
        "\n".join(
            [
                "# Evidence Acquisition Queue",
                "",
                "**Research question:** HBM",
                "",
                "| Priority | Ticker | Gap | Source Target | Search Prompt | Why It Matters | Acceptance Criteria | After Import |",
                "|---|---|---|---|---|---|---|---|",
                "| high | MU | missing_primary_source | Primary filing, company release, audited fact, or official investor material | MU primary filing HBM | Primary/fact evidence is required before this candidate can clear the research confidence gate. | Source title, URL, and source excerpt must directly support the task claim. | Import the evidence, rerun the analysis, and confirm the quality gate improves. |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manual = tmp_path / "ui" / "manual_intake_guarded.jsonl"
    manual.parent.mkdir(parents=True, exist_ok=True)
    manual.write_text(
        '{"id":"manual:MU:hbm-primary-source","source_title":"Micron HBM investor update","source_url":"https://investors.micron.com/news-releases/news-release-details/micron-hbm-update","published_at":"2026-07-05","claim":"Micron disclosed a primary-source HBM update relevant to the HBM analysis.","summary":"Manual intake adds a primary-source HBM evidence item for MU.","tickers":["MU"],"themes":["HBM","manual-intake"],"supply_chain_layer":"semiconductors","direction":"neutral","strength":"primary","confidence":0.82,"factor_impacts":{"evidence_quality":12},"claim_type":"fact","source_excerpt":"Micron investor update text directly supports the HBM production and demand claim."}\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    html = out.read_text(encoding="utf-8")
    zh_html = out.with_name("index.zh.html").read_text(encoding="utf-8")
    assert "Micron HBM investor update" in html
    assert "Resolved by imported evidence" in html
    assert "Import Impact" in html
    assert "Closed gap: missing_primary_source" in html
    assert "Quality gate impact: rerun complete; review the updated publish status and quality score." in html
    assert 'name="quality_before_score"' in html
    assert "Quality before import: not available" in html
    assert "Quality after import: not available" in html
    assert "Quality score change: not available" in html
    assert 'data-task-status="verified"' in html
    assert "Micron HBM investor update" in zh_html
    assert "已由导入证据解决" in zh_html
    assert "导入影响" in zh_html
    assert "已关闭缺口：缺少 primary/fact 来源" in zh_html
    assert "质量门禁影响：已重新生成分析；请复核更新后的发布状态和质量评分。" in zh_html
    assert 'name="quality_before_score"' in zh_html
    assert "导入前质量评分：待对比" in zh_html
    assert "导入后质量评分：待对比" in zh_html
    assert "质量评分变化：待对比" in zh_html


def test_build_dashboard_writes_static_html(tmp_path):
    readiness, pack_dir = _write_pack(tmp_path)
    out = tmp_path / "ui" / "index.html"
    manifest_dir = out.parent / "analyses"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.json").write_text(
        '[{"query":"HBM","intent":"industry","canonical_theme":"HBM","href_en":"analyses/hbm-6f259a8f14/index.html","href_zh":"analyses/hbm-6f259a8f14/index.zh.html","candidate_tickers":["MU","SKHYNIX"]}]',
        encoding="utf-8",
    )
    (out.parent / "metrics.json").write_text(
        '[{"ticker":"SIVE","revenue_growth":"40%","gross_margin":"52%","valuation":"7.2x EV/Sales","momentum":"positive","cycle_position":"early ramp"}]',
        encoding="utf-8",
    )

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    html = out.read_text(encoding="utf-8")
    zh_html = (out.parent / "index.zh.html").read_text(encoding="utf-8")
    assert "Serenity Alpha Lab" in html
    assert "CPO laser bottleneck revenue profitability" in html
    assert "Ready Memos" in html
    assert "Candidate Comparison" in html
    assert "Rating" in html
    assert "Confidence" in html
    assert "Key Gaps" in html
    assert "Revenue Growth" in html
    assert "40%" in html
    assert "7.2x EV/Sales" in html
    assert "SIVE" in html
    assert "AAOI" in html
    assert 'data-memo-href="pack/sive-memo.md"' in html
    assert 'href="../pack/sive-memo.md"' not in html
    assert (out.parent / "pack" / "sive-memo.md").exists()
    assert "Sivers reported 2025 net sales growth." in html
    assert "Research only" in html
    assert "Recent Reports" in html
    assert "HBM" in html
    assert 'href="analyses/hbm-6f259a8f14/index.html"' in html
    assert "Start analysis" in html
    assert "Generating analysis..." in html
    assert 'id="memo-drawer"' in html
    assert "openMemoDrawer" in html
    assert "renderMemoMarkdown" in html
    assert "escapeHtml" in html
    assert "body.classList.add('is-rendered')" in html
    assert "body.querySelector('pre').textContent = text" not in html
    assert "Close report" in html
    assert "View Report" in html
    assert "Search tickers, flags, memo text, or source claims" in html
    assert "All Statuses" in html
    assert "Reset filters" in html
    assert 'href="index.zh.html"' in html
    assert '<html lang="zh-CN">' in zh_html
    assert "本地研究仪表盘" in zh_html
    assert "研究工作台" in zh_html
    assert "定义范围" in zh_html
    assert "比较候选标的" in zh_html
    assert "阅读报告" in zh_html
    assert "补齐证据缺口" in zh_html
    assert "试试 HBM" in zh_html
    assert "试试 存储芯片" in zh_html
    assert 'data-example-query="HBM"' in zh_html
    assert 'data-example-query="存储芯片"' in zh_html
    assert "运行中心" in zh_html
    assert "分析简报" in zh_html
    assert "首选候选" in zh_html
    assert "覆盖状态" in zh_html
    assert "主要缺口" in zh_html
    assert "下一步动作" in zh_html
    assert "打开首选报告" in zh_html
    assert "复核证据任务" in zh_html
    assert "决策工作台" in zh_html
    assert "排序理由" in zh_html
    assert "关键驱动因子" in zh_html
    assert "反证风险" in zh_html
    assert "为什么不是其他候选" in zh_html
    assert "仅用于研究分诊" in zh_html
    assert "按维度排序候选" in zh_html
    assert "Serenity 评分" in zh_html
    assert "证据覆盖" in zh_html
    assert "Primary source 覆盖" in zh_html
    assert "风险覆盖" in zh_html
    assert "排序解释" in zh_html
    assert "交互式候选排序" in zh_html
    assert "报告质量门禁" in zh_html
    assert "发布状态" in zh_html
    assert "需补证据" in zh_html
    assert "质量评分" in zh_html
    assert "质量检查清单" in zh_html
    assert "证据深度" in zh_html
    assert "Primary source 深度" in zh_html
    assert "风险覆盖" in zh_html
    assert "研究工作区" in zh_html
    assert "已保存报告" in zh_html
    assert "候选标记" in zh_html
    assert "已保存排序偏好" in zh_html
    assert "质量门禁快照" in zh_html
    assert "保存工作区" in zh_html
    assert "清空工作区" in zh_html
    assert "可交付研究报告" in zh_html
    assert "交付版摘要" in zh_html
    assert "打开交付版报告" in zh_html
    assert "打印 / 保存 PDF" in zh_html
    assert "deliverable-research-report.md" in zh_html
    deliverable_report = (out.parent / "reports" / "deliverable-research-report.md").read_text(encoding="utf-8")
    assert "## 关键来源与证据" in deliverable_report
    assert "Sivers Annual Report" in deliverable_report
    assert "official-report:SIVE:net-sales-2025" in deliverable_report
    assert "Sivers reported 2025 net sales growth." in deliverable_report
    assert "Net sales increased by 40% year over year." in deliverable_report
    assert "当前运行" in zh_html
    assert "等待启动分析。" in zh_html
    assert "解析股票池" in zh_html
    assert "生成备忘录包" in zh_html
    assert "发布仪表盘" in zh_html
    assert "打开报告" in zh_html
    assert "重试上次运行" in zh_html
    assert "就绪状态" in zh_html
    assert "备忘录包" in zh_html
    assert "候选对比" in zh_html
    assert "评级" in zh_html
    assert "置信层级" in zh_html
    assert "预览分析范围" in zh_html
    assert "确认并生成" in zh_html
    assert "输入解析预览" in zh_html
    assert "识别输入类型" in zh_html
    assert "标准主题" in zh_html
    assert "候选标的" in zh_html
    assert "证据覆盖" in zh_html
    assert "候选覆盖明细" in zh_html
    assert "renderCandidateCoverageSummary" in zh_html
    assert 'id="preview-candidate-coverage"' in zh_html
    assert "预检补证动作" in zh_html
    assert "renderPreflightEvidenceTasks" in zh_html
    assert "openEvidenceTaskImportHandoff" in zh_html
    assert "打开补证导入" in zh_html
    assert 'id="preview-evidence-gap-tasks"' in zh_html
    assert "复制补证提示" in zh_html
    assert "预计输出" in zh_html
    assert "报告、候选对比、证据任务和运营报告" in zh_html
    assert "报告工作台" in zh_html
    assert "按报告类型筛选" in zh_html
    assert "全部报告类型" in zh_html
    assert "生成的分析" in zh_html
    assert "交付版报告" in zh_html
    assert "运营报告" in zh_html
    assert "在阅读器打开" in zh_html
    assert "打开完整页面" in zh_html
    assert "收入增速" in zh_html
    assert "毛利率" in zh_html
    assert "估值" in zh_html
    assert "周期位置" in zh_html
    assert "证据溯源" in zh_html
    assert "搜索股票代码、标记、备忘录文本或来源声明" in zh_html
    assert "启动分析" in zh_html
    assert "正在生成分析..." in zh_html
    assert "查看报告" in zh_html
    assert "关闭报告" in zh_html
    assert "存储芯片" in zh_html
    assert "仅供研究" in zh_html
    assert "最近报告" in zh_html
    assert 'href="analyses/hbm-6f259a8f14/index.zh.html"' in zh_html
    assert 'href="index.html"' in zh_html


def test_report_drawer_renders_markdown_safely(tmp_path):
    readiness, pack_dir = _write_pack(tmp_path)
    out = tmp_path / "ui" / "index.html"

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    html = out.read_text(encoding="utf-8")
    assert "function renderMemoMarkdown(markdown)" in html
    assert "function renderReaderOutline(sections)" in html
    assert "function extractReaderHighlights(lines)" in html
    assert "function scrollReaderSection(sectionId)" in html
    assert 'data-reader-section-id' in html
    assert 'data-reader-outline' in html
    assert "function escapeHtml(value)" in html
    assert ".replace(/&/g, '&amp;')" in html
    assert ".replace(/</g, '&lt;')" in html
    assert "markdown-body" in html
    assert "line.startsWith('## ')" in html
    assert "line.startsWith('- ')" in html
    assert "formatInlineMarkdown(line.slice(3))" in html


def test_build_dashboard_copies_config_metrics_catalog(tmp_path, monkeypatch):
    readiness, pack_dir = _write_pack(tmp_path)
    out = tmp_path / "ui" / "index.html"
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "financial_metrics.json").write_text(
        '[{"ticker":"SIVE","revenue_growth":"40%","gross_margin":"52%","valuation":"7.2x EV/Sales","momentum":"positive","cycle_position":"early ramp"}]',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    copied = out.parent / "metrics.json"
    html = out.read_text(encoding="utf-8")
    assert copied.exists()
    assert "7.2x EV/Sales" in copied.read_text(encoding="utf-8")
    assert "7.2x EV/Sales" in html


def test_build_dashboard_refreshes_stale_output_metrics_from_config(tmp_path, monkeypatch):
    readiness, pack_dir = _write_pack(tmp_path)
    out = tmp_path / "ui" / "index.html"
    out.parent.mkdir(parents=True)
    (out.parent / "metrics.json").write_text(
        '[{"ticker":"SIVE","revenue_growth":"old stale metric","gross_margin":"n/a","valuation":"n/a","momentum":"watch","cycle_position":"old"}]',
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "financial_metrics.json").write_text(
        '[{"ticker":"SIVE","revenue_growth":"40% YoY official report","gross_margin":"n/a","valuation":"n/a","momentum":"reported loss","cycle_position":"revenue ramp / loss-making"}]',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    copied = out.parent / "metrics.json"
    html = out.read_text(encoding="utf-8")
    assert "old stale metric" not in copied.read_text(encoding="utf-8")
    assert "40% YoY official report" in copied.read_text(encoding="utf-8")
    assert "40% YoY official report" in html


def test_build_dashboard_uses_parent_ui_metrics_for_analysis_pages(tmp_path, monkeypatch):
    readiness, pack_dir = _write_pack(tmp_path)
    analysis_dir = tmp_path / "ui" / "analyses" / "topic-abc123"
    out = analysis_dir / "index.html"
    metrics_path = tmp_path / "ui" / "metrics.json"
    metrics_path.parent.mkdir(parents=True)
    metrics_path.write_text(
        '[{"ticker":"SIVE","revenue_growth":"40%","gross_margin":"52%","valuation":"7.2x EV/Sales","momentum":"positive","cycle_position":"early ramp"}]',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    html = out.read_text(encoding="utf-8")
    zh_html = out.with_name("index.zh.html").read_text(encoding="utf-8")
    assert "Revenue Growth" in html
    assert "40%" in html
    assert "7.2x EV/Sales" in html
    assert "收入增速" in zh_html
    assert "40%" in zh_html
    assert "7.2x EV/Sales" in zh_html


def test_build_dashboard_publishes_coverage_matrix_report(tmp_path, monkeypatch):
    readiness, pack_dir = _write_pack(tmp_path)
    out = tmp_path / "output" / "ui" / "index.html"
    reports_dir = tmp_path / "output" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "universe-coverage-matrix.md").write_text(
        "# Universe Coverage Matrix\n\n**Query:** 存储芯片\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    published = out.parent / "reports" / "universe-coverage-matrix.md"
    html = out.read_text(encoding="utf-8")
    zh_html = out.with_name("index.zh.html").read_text(encoding="utf-8")
    assert published.exists()
    assert "Universe Coverage Matrix" in published.read_text(encoding="utf-8")
    assert 'data-memo-href="reports/universe-coverage-matrix.md"' in html
    assert "Universe Coverage Matrix" in html
    assert "Open Coverage Matrix" in html
    assert 'data-memo-href="reports/universe-coverage-matrix.md"' in zh_html
    assert "覆盖矩阵" in zh_html
    assert "打开覆盖矩阵" in zh_html


def test_build_dashboard_surfaces_acquisition_queue_tasks(tmp_path, monkeypatch):
    readiness, pack_dir = _write_pack(tmp_path)
    out = tmp_path / "output" / "ui" / "index.html"
    reports_dir = tmp_path / "output" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "evidence-acquisition-queue.md").write_text(
        "\n".join(
            [
                "# Evidence Acquisition Queue",
                "",
                "**Research question:** HBM",
                "",
                "| Priority | Ticker | Gap | Source Target | Search Prompt |",
                "|---|---|---|---|---|",
                "| high | MU | missing_primary_source | Primary filing, company release, audited fact, or official investor material | MU primary filing HBM |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    html = out.read_text(encoding="utf-8")
    zh_html = out.with_name("index.zh.html").read_text(encoding="utf-8")
    assert "Evidence Tasks" in html
    assert "MU primary filing HBM" in html
    assert 'data-copy-text="MU primary filing HBM"' in html
    assert "Task Status" in html
    assert "data-task-id=" in html
    assert "initializeTaskStatuses" in html
    assert 'action="/ingest-evidence"' in html
    assert "证据任务" in zh_html
    assert "缺少 primary/fact 来源" in zh_html
    assert "复制搜索提示" in zh_html
    assert "任务状态" in zh_html
    assert "待采集" in zh_html
    assert "补充证据" in zh_html
    assert "补证原因" in zh_html
    assert "验收标准" in zh_html
    assert "导入后动作" in zh_html
    assert "需要 primary/fact 证据才能提升研究置信度门禁。" in zh_html
    assert "来源标题、链接和原文摘录必须能直接支撑任务声明。" in zh_html
    assert "导入证据后重新生成分析，并确认质量门禁改善。" in zh_html


def test_build_dashboard_empty_evidence_tasks_keep_rerun_loop_hooks(tmp_path, monkeypatch):
    readiness, pack_dir = _write_pack(tmp_path)
    out = tmp_path / "output" / "ui" / "index.html"
    reports_dir = tmp_path / "output" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "evidence-acquisition-queue.md").write_text(
        "# Evidence Acquisition Queue\n\n**Research question:** HBM\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out)

    html = out.read_text(encoding="utf-8")
    zh_html = out.with_name("index.zh.html").read_text(encoding="utf-8")
    assert "Evidence verification rerun loop" in html
    assert "Auto-rerun after verification" in html
    assert "Rerun verified task" in html
    assert "Quality delta after rerun" in html
    assert "data-verified-task-rerun" in html
    assert "data-verified-task-rerun-context" in html
    assert "data-quality-delta-after-rerun" in html
    assert "证据验证重跑闭环" in zh_html
    assert "验证后自动重跑" in zh_html
    assert "重跑已验证任务" in zh_html
    assert "重跑后质量变化" in zh_html


def test_preview_server_reuses_recently_released_port():
    assert ReusableTCPServer.allow_reuse_address is True
    assert ReusableTCPServer.daemon_threads is True


def test_copy_pack_for_serving_recovers_from_stale_destination_files(tmp_path, monkeypatch):
    source_dir = tmp_path / "source-pack"
    destination_dir = tmp_path / "ui" / "pack"
    source_dir.mkdir()
    destination_dir.mkdir(parents=True)
    (source_dir / "index.md").write_text("# Fresh pack\n", encoding="utf-8")
    stale_file = destination_dir / "sources.md"
    stale_file.write_text("# Stale provenance\n", encoding="utf-8")
    original_rmtree = ui_module.shutil.rmtree
    calls = {"count": 0}

    def flaky_rmtree(path):
        calls["count"] += 1
        if calls["count"] == 1:
            stale_file.unlink()
            raise FileNotFoundError(stale_file)
        return original_rmtree(path)

    monkeypatch.setattr(ui_module.shutil, "rmtree", flaky_rmtree)

    copied = _copy_pack_for_serving(source_dir, destination_dir)

    assert copied == destination_dir
    assert calls["count"] == 2
    assert (destination_dir / "index.md").read_text(encoding="utf-8") == "# Fresh pack\n"
