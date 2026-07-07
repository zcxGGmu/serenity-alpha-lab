from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from serenity_alpha_lab.cli import _build_theme_analysis_dashboard
from serenity_alpha_lab.evidence import load_evidence_files
from serenity_alpha_lab.stock_universe import load_stock_universe
from serenity_alpha_lab.ui import ReusableTCPServer, _build_dashboard_handler, build_dashboard, build_topic_resolution_preview


FIXTURE = Path(__file__).parent / "fixtures" / "evidence.jsonl"


def _write_home_pack(tmp_path: Path) -> tuple[Path, Path]:
    readiness = tmp_path / "readiness.md"
    readiness.write_text(
        "\n".join(
            [
                "# Batch Readiness Report",
                "",
                "**Research question:** CPO laser bottleneck revenue profitability",
                "",
                "| Rank | Ticker | Status | Evidence | Primary/Fact | Risk | Methodology | SERENITY Placeholder | Flags |",
                "|---:|---|---|---:|---:|---:|---:|---:|---|",
                "| 1 | SIVE | ready | 16 | 3 | 6 | 6% | 0% | none |",
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
                "| Ticker | Status | Memo File | Evidence | Primary/Fact | Risk | Flags |",
                "|---|---|---|---:|---:|---|",
                "| SIVE | ready | sive-memo.md | 16 | 3 | 6 | none |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pack_dir / "sources.md").write_text("# Evidence Provenance Index\n", encoding="utf-8")
    (pack_dir / "sive-memo.md").write_text(
        "# Serenity Alpha Lab Memo\n\n**Ticker focus:** SIVE\n\n## Thesis Summary\n\nSIVE preview.\n\nThis memo is research only.\n",
        encoding="utf-8",
    )
    return readiness, pack_dir


def _http_get(url: str) -> tuple[int, str, str]:
    request = Request(url, headers={"User-Agent": "serenity-alpha-lab-test"})
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, response.geturl(), response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.geturl(), exc.read().decode("utf-8")


def _http_post(url: str, data: dict[str, str]) -> tuple[int, str, str]:
    request = Request(
        url,
        data=urlencode(data).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "serenity-alpha-lab-test",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, response.geturl(), response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.geturl(), exc.read().decode("utf-8")


def _http_json_post(url: str, data: dict[str, object]) -> tuple[int, str, str]:
    request = Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "serenity-alpha-lab-test",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, response.geturl(), response.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.geturl(), exc.read().decode("utf-8")


def test_http_e2e_chinese_analysis_launch_opens_report_drawer_assets(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")
    stock_universe = tmp_path / "stock_universe.json"
    stock_universe.write_text(
        """[
  {"ticker":"MU","name":"Micron Technology","market":"US","sector":"Semiconductors","themes":["memory","HBM","DRAM"],"aliases":["HBM","存储芯片"]},
  {"ticker":"SNDK","name":"SanDisk","market":"US","sector":"Semiconductors","themes":["memory","NAND"],"aliases":["存储芯片","NAND"]},
  {"ticker":"SIVE","name":"Sivers Semiconductors","market":"SE","sector":"Semiconductors","themes":["CPO"],"aliases":["CPO"]}
]""",
        encoding="utf-8",
    )

    def analyze_theme(*, query: str, language: str = "en") -> Path:
        if query == "FAILME":
            raise RuntimeError("simulated analysis failure")
        return _build_theme_analysis_dashboard(
            query=query,
            language=language,
            data_paths=[FIXTURE, ui_dir / "manual_intake_guarded.jsonl"],
            tickers=["MU", "SNDK", "SIVE"],
            out_dir=ui_dir / "analyses",
            limit=8,
            stock_universe_path=stock_universe,
        )

    def ingest_evidence(form):
        from serenity_alpha_lab.evidence_intake import append_intake_evidence, build_intake_evidence

        ticker = str(form.get("ticker") or "").upper()
        item = build_intake_evidence(
            item_id=str(form.get("id") or f"manual:{ticker}:hbm-source"),
            source_title=str(form.get("source_title") or ""),
            source_url=str(form.get("source_url") or ""),
            published_at=str(form.get("published_at") or ""),
            claim=str(form.get("claim") or ""),
            summary=str(form.get("summary") or ""),
            source_excerpt=str(form.get("source_excerpt") or ""),
            tickers=[ticker],
            themes=["HBM", "manual-intake"],
            supply_chain_layer="semiconductors",
            direction="neutral",
            strength="primary",
            confidence=0.82,
            factor_impacts={"evidence_quality": 12},
            claim_type="fact",
        )
        append_intake_evidence(item, ui_dir / "manual_intake_guarded.jsonl")
        return analyze_theme(query=str(form.get("query") or "HBM"), language=str(form.get("language") or "zh"))

    def resolve_theme(*, query: str, language: str = "en") -> dict[str, object]:
        return build_topic_resolution_preview(
            query=query,
            language=language,
            evidence=load_evidence_files([FIXTURE]),
            fallback_tickers=["MU", "SNDK", "SIVE"],
            stock_universe=load_stock_universe(stock_universe),
        )

    handler = _build_dashboard_handler(ui_dir, analyze_theme, ingest_callback=ingest_evidence, resolve_callback=resolve_theme)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, home = _http_get(f"{base_url}/index.zh.html")
        assert status == 200
        assert "启动分析" in home
        assert "预览分析范围" in home
        assert "确认并生成" in home
        assert "输入解析预览" in home
        assert "识别输入类型" in home
        assert "标准主题" in home
        assert "候选标的" in home
        assert "证据覆盖" in home
        assert "预计输出" in home
        assert "parseAnalysisInputPreview" in home
        assert "fetchAnalysisInputPreview" in home
        assert "/api/resolve-topic" in home
        assert "后端解析器" in home
        assert "预览暂不可用，已使用本地兜底解析。" in home
        assert "renderAnalysisInputPreview" in home
        assert "confirmAnalysisLaunch" in home
        assert "报告、候选对比、证据任务和运营报告" in home
        assert "研究工作台" in home
        assert "定义范围" in home
        assert "比较候选标的" in home
        assert "补齐证据缺口" in home
        assert "试试 HBM" in home
        assert 'data-example-query="存储芯片"' in home
        assert "launchExampleAnalysis" in home
        assert "运行中心" in home
        assert "当前运行" in home
        assert "等待启动分析。" in home
        assert "解析股票池" in home
        assert "发布仪表盘" in home
        assert "重试上次运行" in home
        assert "initializeRunCenter" in home
        assert "syncRunCenterFromServer" in home
        assert "startRunPolling" in home
        assert "stopRunPolling" in home
        assert "scheduleRunPolling" in home
        assert 'data-run-polling="idle"' in home
        assert "正在刷新运行状态..." in home
        assert "报告已生成。" in home
        assert "打开最新报告" in home
        assert "运行历史" in home
        assert "暂无运行历史。" in home
        assert "分析简报" in home
        assert "首选候选" in home
        assert "下一步动作" in home
        assert "renderRunHistory" in home

        status, _, preview_body = _http_get(f"{base_url}/api/resolve-topic?query={quote('存储芯片')}&language=zh")
        assert status == 200
        preview = json.loads(preview_body)
        assert preview["original_query"] == "存储芯片"
        assert preview["intent"] == "industry"
        assert preview["intent_label"] == "行业"
        assert preview["canonical_theme"] == "memory"
        assert preview["candidate_tickers"][:2] == ["MU", "SNDK"]
        assert "evidence_count" in preview["coverage"]
        assert preview["coverage_label"].endswith("条证据")
        assert preview["candidate_coverage"][0]["ticker"] == "MU"
        assert preview["candidate_coverage"][0]["evidence_count"] >= 1
        assert "primary_count" in preview["candidate_coverage"][0]
        assert "risk_count" in preview["candidate_coverage"][0]
        assert preview["candidate_coverage"][0]["coverage_label"].endswith("条证据")
        assert preview["evidence_gap_tasks"][0]["ticker"] == "MU"
        assert preview["evidence_gap_tasks"][0]["priority"] in {"high", "medium"}
        assert preview["evidence_gap_tasks"][0]["gap"] in {"missing_primary_source", "missing_risk_coverage"}
        assert preview["evidence_gap_tasks"][0]["search_prompt"].startswith("MU ")
        assert preview["evidence_gap_tasks"][0]["copy_label"] == "复制补证提示"
        assert preview["source"] == "backend"
        assert "openRunReport" in home
        assert "rerunRunRecord" in home
        assert "打开报告" in home
        assert "报告工作台" in home
        assert "按报告类型筛选" in home
        assert "全部报告类型" in home
        assert "生成的分析" in home
        assert "运营报告" in home
        assert "在阅读器打开" in home
        assert "打开完整页面" in home
        assert 'id="memo-drawer-toolbar"' in home
        assert 'id="memo-drawer-current-link"' in home
        assert "当前报告链接" in home
        assert "复制当前链接" in home
        assert 'id="memo-drawer-outline"' in home
        assert 'id="memo-drawer-highlights"' in home
        assert "报告目录" in home
        assert "报告重点" in home
        assert "跳转章节" in home
        assert "copyCurrentReaderLink" in home
        assert "openCurrentReaderReport" in home
        assert "renderReaderOutline" in home
        assert "extractReaderHighlights" in home
        assert "scrollReaderSection" in home
        assert "filterReportWorkbench" in home
        assert "reviewReportWorkbench" in home
        assert 'data-report-type="generated"' in home
        assert 'data-report-type="operational"' in home
        assert "重新生成" in home
        assert "失败原因" in home
        assert 'action="/analyze"' in home
        assert 'id="memo-drawer"' in home

        query = quote("HBM")
        status, final_url, analysis = _http_get(f"{base_url}/analyze?query={query}&language=zh")
        assert status == 200
        assert final_url.endswith("/analyses/hbm-6f259a8f14/index.zh.html")
        assert "HBM" in analysis

        status, _, runs_body = _http_get(f"{base_url}/api/runs")
        assert status == 200
        runs = json.loads(runs_body)
        assert runs["runs"][0]["query"] == "HBM"
        assert runs["runs"][0]["language"] == "zh"
        assert runs["runs"][0]["status"] == "completed"
        assert runs["runs"][0]["href"].endswith("/analyses/hbm-6f259a8f14/index.zh.html")
        assert runs["runs"][0]["completed_at"]
        assert runs["runs"][0]["manifest_href"].endswith("/analyses/hbm-6f259a8f14/analysis-manifest.json")
        assert runs["runs"][0]["canonical_theme"] == "HBM"
        assert runs["runs"][0]["candidate_tickers"][:1] == ["MU"]
        assert runs["runs"][0]["quality_score"] >= 0
        assert runs["runs"][0]["quality_status"] in {"publishable", "needs-evidence", "not-publishable"}
        assert (ui_dir / "runs.json").exists()

        status, _, failed_body = _http_get(f"{base_url}/analyze?query=FAILME&language=zh")
        assert status == 500
        assert "Theme analysis failed" in failed_body

        status, _, runs_body = _http_get(f"{base_url}/api/runs")
        assert status == 200
        runs = json.loads(runs_body)
        assert len(runs["runs"]) >= 2
        assert runs["runs"][0]["query"] == "FAILME"
        assert runs["runs"][0]["status"] == "failed"
        assert runs["runs"][0]["error"]
        assert runs["runs"][1]["query"] == "HBM"
        assert runs["runs"][1]["status"] == "completed"

        assert "候选对比" in analysis
        assert "分析简报" in analysis
        assert "首选候选" in analysis
        assert "覆盖状态" in analysis
        assert "主要缺口" in analysis
        assert "下一步动作" in analysis
        assert "打开首选报告" in analysis
        assert "复核证据任务" in analysis
        assert "研究动作工作台" in analysis
        assert "动作队列" in analysis
        assert "待关闭质量缺口" in analysis
        assert "打开证据任务" in analysis
        assert "打开交付版报告" in analysis
        assert "打开采集队列" in analysis
        assert "复制下一步研究提示" in analysis
        assert 'id="research-action-workbench"' in analysis
        assert 'data-research-action-gap=' in analysis
        assert 'data-research-action-ticker=' in analysis
        assert 'data-copy-text=' in analysis
        assert "决策工作台" in analysis
        assert "排序理由" in analysis
        assert "关键驱动因子" in analysis
        assert "反证风险" in analysis
        assert "为什么不是其他候选" in analysis
        assert "仅用于研究分诊" in analysis
        assert "按维度排序候选" in analysis
        assert "排序解释" in analysis
        assert "交互式候选排序" in analysis
        assert "updateDecisionRanking" in analysis
        assert 'data-decision-candidate' in analysis
        assert "报告质量门禁" in analysis
        assert "发布状态" in analysis
        assert "质量评分" in analysis
        assert "质量检查清单" in analysis
        assert "Primary source 深度" in analysis
        assert 'id="report-quality-gate"' in analysis
        assert "研究工作区" in analysis
        assert "保存工作区" in analysis
        assert "已保存报告" in analysis
        assert "候选标记" in analysis
        assert "质量门禁快照" in analysis
        assert "initializeSavedWorkspace" in analysis
        assert "data-workspace-report" in analysis
        assert "研究项目库" in analysis
        assert "保存为项目" in analysis
        assert "项目状态" in analysis
        assert "待补证据" in analysis
        assert "可复核" in analysis
        assert "已交付" in analysis
        assert "需重跑" in analysis
        assert 'id="research-project-library"' in analysis
        assert 'id="project-library-list"' in analysis
        assert "projectLibraryStorageKey" in analysis
        assert "saveResearchProject" in analysis
        assert "renderResearchProjectLibrary" in analysis
        assert "按状态筛选项目" in analysis
        assert "全部项目状态" in analysis
        assert "项目对比摘要" in analysis
        assert "项目总数" in analysis
        assert "平均质量评分" in analysis
        assert "证据待办" in analysis
        assert "已交付项目" in analysis
        assert "搜索已保存项目" in analysis
        assert "排序已保存项目" in analysis
        assert "项目标签" in analysis
        assert "全部项目标签" in analysis
        assert "标签：待补证据" in analysis
        assert "标签：高质量" in analysis
        assert "标签：已交付" in analysis
        assert "项目详情抽屉" in analysis
        assert "复核项目" in analysis
        assert "项目复核面板" in analysis
        assert "项目详情质量" in analysis
        assert "项目详情缺口" in analysis
        assert "项目详情状态" in analysis
        assert "下一步复核动作" in analysis
        assert "从详情打开报告" in analysis
        assert "项目复核操作面板" in analysis
        assert "建议复核动作" in analysis
        assert "关闭证据缺口" in analysis
        assert "重新生成分析" in analysis
        assert "标记已交付" in analysis
        assert "从操作面板打开报告" in analysis
        assert "动作已记录" in analysis
        assert "证据缺口关联任务" in analysis
        assert "跳转到证据任务" in analysis
        assert "带项目上下文重跑" in analysis
        assert "重跑后质量" in analysis
        assert "证据验证重跑闭环" in analysis
        assert "验证后自动重跑" in analysis
        assert "重跑已验证任务" in analysis
        assert "重跑后质量变化" in analysis
        assert "项目证据审计日志" in analysis
        assert "证据贡献历史" in analysis
        assert "已验证任务审计轨迹" in analysis
        assert "质量贡献" in analysis
        assert "项目复核时间线" in analysis
        assert "复核事件历史" in analysis
        assert "暂无复核事件。" in analysis
        assert "记录复核事件" in analysis
        assert "服务端复核事件日志" in analysis
        assert "状态已更新" in analysis
        assert "已打开详情" in analysis
        assert "已复制对比简报" in analysis
        assert "已复制队列交接" in analysis
        assert "queue-handoff-copied" in analysis
        assert "项目负责人队列" in analysis
        assert "按负责人筛选" in analysis
        assert "全部负责人" in analysis
        assert "未分配负责人" in analysis
        assert "证据负责人" in analysis
        assert "报告复核人" in analysis
        assert "重跑负责人" in analysis
        assert "归档负责人" in analysis
        assert "分配项目负责人" in analysis
        assert "负责人已更新" in analysis
        assert "历史对比矩阵" in analysis
        assert "选择对比" in analysis
        assert "对比已选项目" in analysis
        assert "复制对比简报" in analysis
        assert "已复制对比简报" in analysis
        assert "仅供研究的对比简报" in analysis
        assert "对比主题" in analysis
        assert "首选候选" in analysis
        assert "质量评分" in analysis
        assert "证据缺口" in analysis
        assert "项目状态" in analysis
        assert "报告入口" in analysis
        assert 'id="project-status-filter"' in analysis
        assert 'id="project-library-search"' in analysis
        assert 'id="project-library-sort"' in analysis
        assert 'id="project-tag-filter"' in analysis
        assert 'id="project-next-action-filter"' in analysis
        assert 'id="project-owner-filter"' in analysis
        assert 'id="project-activity-filter"' in analysis
        assert 'id="project-next-action-queue-summary"' in analysis
        assert 'id="project-owner-queue-summary"' in analysis
        assert 'id="project-queue-handoff-preview"' in analysis
        assert 'id="project-comparison-summary"' in analysis
        assert 'id="project-detail-drawer"' in analysis
        assert 'id="project-detail-title"' in analysis
        assert 'id="project-detail-body"' in analysis
        assert 'id="project-detail-quality"' in analysis
        assert 'id="project-detail-actions"' in analysis
        assert 'id="project-review-action-panel"' in analysis
        assert 'id="project-review-action-list"' in analysis
        assert 'id="project-review-loop-status"' in analysis
        assert 'id="project-review-timeline"' in analysis
        assert 'id="project-review-event-filter"' in analysis
        assert 'id="project-review-event-summary"' in analysis
        assert 'id="project-review-timeline-list"' in analysis
        assert 'id="project-comparison-matrix"' in analysis
        assert 'id="project-comparison-table"' in analysis
        assert "filterResearchProjects" in analysis
        assert "sortResearchProjects" in analysis
        assert "projectTagForRecord" in analysis
        assert "projectNextActionLabel" in analysis
        assert "renderProjectNextActionQueueSummary" in analysis
        assert "filterProjectNextActionQueue" in analysis
        assert "projectOwnerLabel" in analysis
        assert "projectOwnerForRecord" in analysis
        assert "renderProjectOwnerQueueSummary" in analysis
        assert "filterProjectOwnerQueue" in analysis
        assert "projectOwnerOptions" in analysis
        assert "updateResearchProjectOwner" in analysis
        assert "buildProjectQueueHandoffBrief" in analysis
        assert "copyProjectQueueHandoffBrief" in analysis
        assert "renderProjectQueueHandoffPreview" in analysis
        assert "buildFilteredProjectQueueHandoffBrief" in analysis
        assert "copyFilteredProjectQueueHandoffBrief" in analysis
        assert "renderFilteredProjectQueueHandoffPreview" in analysis
        assert "projectLibraryFilteredRecords" in analysis
        assert "openProjectDetailDrawer" in analysis
        assert "closeProjectDetailDrawer" in analysis
        assert "renderProjectDetailDrawer" in analysis
        assert "projectReviewActionPanelItems" in analysis
        assert "renderProjectReviewActionPanel" in analysis
        assert "handleProjectReviewAction" in analysis
        assert "markProjectDeliveredFromDrawer" in analysis
        assert "rerunProjectAnalysisFromDrawer" in analysis
        assert "projectEvidenceTaskTarget" in analysis
        assert "focusProjectEvidenceTask" in analysis
        assert "projectRerunUrl" in analysis
        assert "persistProjectRerunContext" in analysis
        assert "applyProjectRerunContext" in analysis
        assert "verifiedTaskRerunContext" in analysis
        assert "handleVerifiedTaskRerun" in analysis
        assert "updateVerifiedTaskRerunLoop" in analysis
        assert "qualityDeltaAfterRerun" in analysis
        assert "syncTaskStatusesFromServer" in analysis
        assert "writeTaskStatusToServer" in analysis
        assert "clearTaskStatusesOnServer" in analysis
        assert "/api/task-statuses" in analysis
        assert "projectEvidenceAuditLogStorageKey" in analysis
        assert "readProjectEvidenceAuditLog" in analysis
        assert "writeProjectEvidenceAuditLog" in analysis
        assert "appendProjectEvidenceAuditEntry" in analysis
        assert "renderProjectEvidenceAuditLog" in analysis
        assert "syncProjectEvidenceAuditLogFromServer" in analysis
        assert "writeProjectEvidenceAuditEntryToServer" in analysis
        assert "clearProjectEvidenceAuditLogOnServer" in analysis
        assert "/api/project-evidence-audits" in analysis
        assert "projectReviewTimelineStorageKey" in analysis
        assert "readProjectReviewTimeline" in analysis
        assert "writeProjectReviewTimeline" in analysis
        assert "appendProjectReviewEvent" in analysis
        assert "projectReviewEventTypeLabel" in analysis
        assert "renderProjectReviewEventSummary" in analysis
        assert "filterProjectReviewEvents" in analysis
        assert "renderProjectReviewTimeline" in analysis
        assert "syncProjectReviewTimelineFromServer" in analysis
        assert "writeProjectReviewEventToServer" in analysis
        assert "clearProjectReviewEventsOnServer" in analysis
        assert "/api/project-events" in analysis
        assert "renderProjectComparisonSummary" in analysis
        assert "renderProjectComparisonMatrix" in analysis
        assert "toggleProjectComparisonSelection" in analysis
        assert "updateProjectComparisonMatrix" in analysis
        assert "buildProjectComparisonBrief" in analysis
        assert "copyProjectComparisonBrief" in analysis
        assert "data-project-filter-status" in analysis
        assert "data-project-quality-score" in analysis
        assert "data-project-tag" in analysis
        assert "data-project-next-action-filter" in analysis
        assert "data-project-owner-filter" in analysis
        assert "data-project-owner-value" in analysis
        assert "data-project-owner-select" in analysis
        assert "data-project-owner-queue" in analysis
        assert "data-project-owner-count" in analysis
        assert "data-project-review-event-filter" in analysis
        assert "data-project-review-event-count" in analysis
        assert "data-project-activity-summary" in analysis
        assert "data-project-activity-count" in analysis
        assert "data-project-latest-activity" in analysis
        assert "data-project-activity-filter" in analysis
        assert "data-project-activity-state" in analysis
        assert "projectReviewActivitySummary" in analysis
        assert "renderProjectActivitySummary" in analysis
        assert "projectActivityState" in analysis
        assert "projectActivityStateLabel" in analysis
        assert "filterProjectActivity" in analysis
        assert "data-project-next-action-queue" in analysis
        assert "data-project-next-action-count" in analysis
        assert "data-project-queue-handoff" in analysis
        assert "data-project-queue-handoff-action" in analysis
        assert "data-project-queue-handoff-preview" in analysis
        assert "data-project-queue-handoff-items" in analysis
        assert "data-filtered-project-handoff" in analysis
        assert "data-filtered-project-handoff-action" in analysis
        assert "data-filtered-project-handoff-preview" in analysis
        assert "data-filtered-project-handoff-items" in analysis
        assert "data-project-search-text" in analysis
        assert "data-project-detail-id" in analysis
        assert "data-project-detail-quality" in analysis
        assert "data-project-detail-gap" in analysis
        assert "data-project-review-action" in analysis
        assert "data-project-review-action-type" in analysis
        assert "data-project-review-action-project" in analysis
        assert "data-project-evidence-task-target" in analysis
        assert "data-project-rerun-context" in analysis
        assert "data-project-quality-after-rerun" in analysis
        assert "data-verified-task-rerun" in analysis
        assert "data-verified-task-rerun-context" in analysis
        assert "data-quality-delta-after-rerun" in analysis
        assert "data-project-evidence-audit" in analysis
        assert "data-project-evidence-audit-type" in analysis
        assert "data-project-evidence-audit-quality-delta" in analysis
        assert "data-project-review-event" in analysis
        assert "data-project-review-event-type" in analysis
        assert "data-project-review-event-project" in analysis
        assert "data-project-compare-id" in analysis
        assert "data-project-compare-selected" in analysis
        assert "data-project-comparison-brief" in analysis
        assert "data-project-status" in analysis
        assert "data-project-query" in analysis
        assert "可交付研究报告" in analysis
        assert "交付版摘要" in analysis
        assert "打开交付版报告" in analysis
        assert "打印 / 保存 PDF" in analysis
        assert "分享交接" in analysis
        assert "复制报告链接" in analysis
        assert "复制清单链接" in analysis
        assert "copyShareLink" in analysis
        assert 'data-share-href="reports/deliverable-research-report.md"' in analysis
        assert 'data-share-href="analysis-manifest.json"' in analysis
        assert "报告交付包" in analysis
        assert "在一个面板中打开或复制交付报告、分析清单、覆盖矩阵和证据采集队列。" in analysis
        assert "交付质量摘要" in analysis
        assert "仅供研究" in analysis
        assert "首选候选" in analysis
        assert "剩余缺口" in analysis
        assert 'data-delivery-quality-status=' in analysis
        assert 'data-delivery-quality-score=' in analysis
        assert "复制交接清单" in analysis
        assert "copyHandoffBundle" in analysis
        assert 'data-handoff-artifact-title="可交付研究报告"' in analysis
        assert 'data-handoff-artifact-href="reports/deliverable-research-report.md"' in analysis
        assert 'id="delivery-package"' in analysis
        assert 'data-package-artifact="deliverable-report"' in analysis
        assert 'data-package-artifact="analysis-manifest"' in analysis
        assert 'data-package-artifact="coverage-matrix"' in analysis
        assert 'data-package-artifact="evidence-queue"' in analysis
        assert 'data-memo-href="analysis-manifest.json"' in analysis
        assert "deliverable-research-report.md" in analysis
        assert "analysis-manifest.json" in analysis
        assert "分析清单" in analysis
        assert "printDeliverableReport" in analysis
        assert "查看报告" in analysis
        assert "打开覆盖矩阵" in analysis
        assert "打开采集队列" in analysis
        assert "证据任务" in analysis
        assert "补证原因" in analysis
        assert "验收标准" in analysis
        assert "导入后动作" in analysis
        assert "导入证据后重新生成分析，并确认质量门禁改善。" in analysis
        assert "复制搜索提示" in analysis
        assert "任务状态" in analysis
        assert "待采集" in analysis
        assert "补充证据" in analysis
        assert 'action="/ingest-evidence"' in analysis
        assert "请粘贴一段能直接支撑该任务的来源摘录。" in analysis
        assert "正在提交证据..." in analysis
        assert "必填：来源标题、来源链接和可追溯摘录。" in analysis
        assert "已导入证据" in analysis
        assert "renderMemoMarkdown" in analysis

        status, _, deliverable = _http_get(f"{base_url}/analyses/hbm-6f259a8f14/reports/deliverable-research-report.md")
        assert status == 200
        assert "# 可交付研究报告" in deliverable
        assert "**研究主题:** HBM" in deliverable
        assert "## 候选排序" in deliverable
        assert "## 质量门禁" in deliverable
        assert "## 关键来源与证据" in deliverable
        assert "暂无可展示 primary source" in deliverable
        assert "请先补充可追溯来源" in deliverable
        assert "## 证据缺口与下一步" in deliverable
        assert "仅供研究" in deliverable
        assert 'data-memo-href="pack/mu-memo.md"' in analysis
        assert 'data-memo-href="reports/universe-coverage-matrix.md"' in analysis
        assert 'data-memo-href="reports/evidence-acquisition-queue.md"' in analysis
        assert 'data-copy-text="MU primary filing HBM"' in analysis
        assert "initializeTaskStatuses" in analysis

        status, _, initial_matrix = _http_get(f"{base_url}/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md")
        assert status == 200
        assert "# 股票池覆盖矩阵" in initial_matrix
        assert "**查询:** HBM" in initial_matrix
        assert "缺少 primary/fact 来源" in initial_matrix
        assert "MU primary filing HBM" in initial_matrix
        assert "SNDK primary filing 存储芯片" not in initial_matrix
        assert "# Universe Coverage Matrix" not in initial_matrix

        status, _, analysis_manifest = _http_get(f"{base_url}/analyses/hbm-6f259a8f14/analysis-manifest.json")
        assert status == 200
        manifest_payload = json.loads(analysis_manifest)
        assert manifest_payload["query"] == "HBM"
        assert manifest_payload["language"] == "zh"
        assert manifest_payload["canonical_theme"] == "HBM"
        assert manifest_payload["candidate_tickers"][:1] == ["MU"]
        assert manifest_payload["quality"]["score"] >= 0
        assert manifest_payload["reports"]["dashboard_zh"] == "index.zh.html"
        assert manifest_payload["reports"]["deliverable"] == "reports/deliverable-research-report.md"
        assert manifest_payload["research_only"] is True

        status, _, invalid_import = _http_post(
            f"{base_url}/ingest-evidence",
            {
                "query": "HBM",
                "language": "zh",
                "ticker": "MU",
                "id": "manual:MU:invalid-source",
                "source_title": "Placeholder source",
                "source_url": "https://example.com/placeholder",
                "published_at": "2026-07-05",
                "claim": "Invalid placeholder source should be rejected.",
                "summary": "Invalid evidence should not enter manual intake.",
                "source_excerpt": "Placeholder excerpt is long enough but the URL must be rejected.",
            },
        )
        assert status == 400
        assert "证据导入失败" in invalid_import
        assert "请返回上一页修正来源标题、来源链接和来源摘录后重试。" in invalid_import
        assert "placeholder source URL is not allowed" in invalid_import

        status, final_url, imported = _http_post(
            f"{base_url}/ingest-evidence",
            {
                "query": "HBM",
                "language": "zh",
                "ticker": "MU",
                "id": "manual:MU:hbm-primary-source",
                "source_title": "Micron HBM investor update",
                "source_url": "https://investors.micron.com/news-releases/news-release-details/micron-hbm-update",
                "published_at": "2026-07-05",
                "claim": "Micron disclosed a primary-source HBM update relevant to the HBM analysis.",
                "summary": "Manual intake adds a primary-source HBM evidence item for MU.",
                "source_excerpt": "Micron investor update text directly supports the HBM production and demand claim.",
                "quality_before_score": "48",
            },
        )
        assert status == 200
        assert final_url.endswith("/analyses/hbm-6f259a8f14/index.zh.html")
        assert "manual:MU:hbm-primary-source" in (ui_dir / "manual_intake_guarded.jsonl").read_text(encoding="utf-8")
        assert "补充证据已纳入" in imported
        assert "已导入证据" in imported
        assert "Micron HBM investor update" in imported
        assert "已解决缺口：缺少 primary/fact 来源" in imported
        assert "已由导入证据解决" in imported
        assert "导入影响" in imported
        assert "已关闭缺口：缺少 primary/fact 来源" in imported
        assert "质量门禁影响：已重新生成分析；请复核更新后的发布状态和质量评分。" in imported
        assert "剩余补证工作：发布前请继续复核下一个可见证据任务。" in imported
        assert "导入前质量评分：48/100" in imported
        assert "导入后质量评分：" in imported
        assert "质量评分变化：" in imported

        status, _, task_status_body = _http_get(
            f"{base_url}/api/task-statuses?projectId=/analyses/hbm-6f259a8f14/index.zh.html"
        )
        assert status == 200
        task_status_payload = json.loads(task_status_body)
        assert task_status_payload["statuses"][0]["ticker"] == "MU"
        assert task_status_payload["statuses"][0]["status"] == "verified"
        assert task_status_payload["statuses"][0]["taskId"]
        assert (ui_dir / "task_statuses.json").exists()

        status, _, audit_body = _http_get(
            f"{base_url}/api/project-evidence-audits?projectId=/analyses/hbm-6f259a8f14/index.zh.html"
        )
        assert status == 200
        audit_payload = json.loads(audit_body)
        assert audit_payload["audits"][0]["ticker"] == "MU"
        assert audit_payload["audits"][0]["type"] == "import-verified-task"
        assert audit_payload["audits"][0]["taskId"] == task_status_payload["statuses"][0]["taskId"]
        assert audit_payload["audits"][0]["qualityBefore"] == "48/100"
        assert audit_payload["audits"][0]["qualityAfter"].endswith("/100")
        assert audit_payload["summary"]["projectId"] == "/analyses/hbm-6f259a8f14/index.zh.html"
        assert audit_payload["summary"]["ticker"] == "MU"
        assert audit_payload["summary"]["taskId"] == task_status_payload["statuses"][0]["taskId"]
        assert audit_payload["summary"]["qualityBefore"] == "48/100"
        assert audit_payload["summary"]["qualityAfter"].endswith("/100")
        assert audit_payload["summary"]["qualityDelta"]
        assert (ui_dir / "project_evidence_audits.json").exists()

        status, _, persisted = _http_get(f"{base_url}/analyses/hbm-6f259a8f14/index.zh.html")
        assert status == 200
        assert "Micron HBM investor update" in persisted
        assert "manual:MU:hbm-primary-source" in persisted
        assert "导入影响" in persisted
        assert "质量门禁影响：已重新生成分析；请复核更新后的发布状态和质量评分。" in persisted
        assert "已由导入证据解决" in persisted
        assert 'data-task-status="verified"' in persisted

        status, _, memo = _http_get(f"{base_url}/analyses/hbm-6f259a8f14/pack/mu-memo.md")
        assert status == 200
        assert "# Serenity Alpha Lab 研究备忘录" in memo
        assert "**研究问题:** HBM" in memo
        assert "## 证据补齐行动清单" in memo
        assert "仅供研究" in memo

        status, _, matrix = _http_get(f"{base_url}/analyses/hbm-6f259a8f14/reports/universe-coverage-matrix.md")
        assert status == 200
        assert "# 股票池覆盖矩阵" in matrix
        assert "**查询:** HBM" in matrix
        assert "缺少 primary/fact 来源" not in matrix
        assert "缺少风险证据" in matrix
        assert "MU risk invalidation HBM" in matrix
        assert "SNDK primary filing 存储芯片" not in matrix
        assert "# Universe Coverage Matrix" not in matrix

        status, _, queue = _http_get(f"{base_url}/analyses/hbm-6f259a8f14/reports/evidence-acquisition-queue.md")
        assert status == 200
        assert "# 证据采集队列" in queue
        assert "**研究问题:** HBM" in queue
        assert "| 优先级 | 股票代码 | 缺口 | 来源目标 | 搜索提示 | 补证原因 | 验收标准 | 导入后动作 |" in queue
        assert "缺少 primary/fact 来源" in queue
        assert "MU risk HBM" in queue
        assert "SNDK primary filing HBM" in queue
        assert "导入证据后重新生成分析，并确认质量门禁改善。" in queue
        assert "# Evidence Acquisition Queue" not in queue
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_analysis_failure_is_persisted_in_run_api(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    def analyze_theme(*, query: str, language: str = "en") -> Path:
        raise RuntimeError(f"fixture failure for {query}/{language}")

    handler = _build_dashboard_handler(ui_dir, analyze_theme)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_get(f"{base_url}/analyze?query=HBM&language=zh")
        assert status == 500
        assert "Theme analysis failed" in body

        status, _, runs_body = _http_get(f"{base_url}/api/runs")
        assert status == 200
        runs = json.loads(runs_body)
        assert runs["runs"][0]["query"] == "HBM"
        assert runs["runs"][0]["language"] == "zh"
        assert runs["runs"][0]["status"] == "failed"
        assert runs["runs"][0]["error"] == "fixture failure for HBM/zh"
        assert runs["runs"][0]["completed_at"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_analysis_writes_running_record_before_completion(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")
    observed_runs: list[dict[str, object]] = []

    def analyze_theme(*, query: str, language: str = "en") -> Path:
        runs_path = ui_dir / "runs.json"
        assert runs_path.exists()
        observed_runs.append(json.loads(runs_path.read_text(encoding="utf-8"))["runs"][0])
        analysis_dir = ui_dir / "analyses" / "running-demo"
        analysis_dir.mkdir(parents=True)
        output = analysis_dir / ("index.zh.html" if language == "zh" else "index.html")
        output.write_text(f"<html><body>{query}</body></html>", encoding="utf-8")
        return output

    handler = _build_dashboard_handler(ui_dir, analyze_theme)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, final_url, body = _http_get(f"{base_url}/analyze?query=HBM&language=zh")
        assert status == 200
        assert final_url.endswith("/analyses/running-demo/index.zh.html")
        assert "HBM" in body
        assert observed_runs
        assert observed_runs[0]["query"] == "HBM"
        assert observed_runs[0]["language"] == "zh"
        assert observed_runs[0]["status"] == "running"
        assert observed_runs[0]["queued_at"]
        assert observed_runs[0]["started_at"]
        assert not observed_runs[0]["completed_at"]

        status, _, runs_body = _http_get(f"{base_url}/api/runs")
        assert status == 200
        runs = json.loads(runs_body)["runs"]
        assert runs[0]["query"] == "HBM"
        assert runs[0]["status"] == "completed"
        assert runs[0]["queued_at"] == observed_runs[0]["queued_at"]
        assert runs[0]["started_at"] == observed_runs[0]["started_at"]
        assert runs[0]["completed_at"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_analyze_jobs_submit_runs_in_background(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")
    stock_universe = tmp_path / "stock_universe.json"
    stock_universe.write_text(
        """[
  {"ticker":"MU","name":"Micron Technology","market":"US","sector":"Semiconductors","themes":["memory","HBM","DRAM"],"aliases":["HBM","存储芯片"]},
  {"ticker":"SNDK","name":"SanDisk","market":"US","sector":"Semiconductors","themes":["memory","NAND"],"aliases":["存储芯片","NAND"]},
  {"ticker":"SIVE","name":"Sivers Semiconductors","market":"SE","sector":"Semiconductors","themes":["CPO"],"aliases":["CPO"]}
]""",
        encoding="utf-8",
    )
    release_job = threading.Event()
    observed_runs: list[dict[str, object]] = []

    def analyze_theme(*, query: str, language: str = "en") -> Path:
        runs_path = ui_dir / "runs.json"
        assert runs_path.exists()
        observed_runs.append(json.loads(runs_path.read_text(encoding="utf-8"))["runs"][0])
        release_job.wait(timeout=5)
        analysis_dir = ui_dir / "analyses" / "async-demo"
        analysis_dir.mkdir(parents=True)
        output = analysis_dir / ("index.zh.html" if language == "zh" else "index.html")
        output.write_text(f"<html><body>{query} async</body></html>", encoding="utf-8")
        return output

    def resolve_theme(*, query: str, language: str = "en") -> dict[str, object]:
        return build_topic_resolution_preview(
            query=query,
            language=language,
            evidence=load_evidence_files([FIXTURE]),
            fallback_tickers=["MU", "SNDK", "SIVE"],
            stock_universe=load_stock_universe(stock_universe),
        )

    handler = _build_dashboard_handler(ui_dir, analyze_theme, resolve_callback=resolve_theme)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_json_post(
            f"{base_url}/api/analyze-jobs",
            {"query": "HBM", "language": "zh"},
        )
        assert status == 202
        payload = json.loads(body)
        assert payload["job"]["query"] == "HBM"
        assert payload["job"]["language"] == "zh"
        assert payload["job"]["status"] in {"queued", "running"}
        assert payload["job"]["job_id"]
        assert payload["job"]["queued_at"]
        assert payload["job"]["poll_href"] == "/api/runs"
        assert payload["job"]["canonical_theme"] == "HBM"
        assert payload["job"]["candidate_tickers"][:1] == ["MU"]
        assert payload["job"]["coverage_label"].endswith("条证据")
        assert payload["job"]["candidate_coverage"][0]["ticker"] == "MU"
        assert payload["job"]["candidate_coverage"][0]["evidence_count"] >= 1
        assert "primary_count" in payload["job"]["candidate_coverage"][0]
        assert "risk_count" in payload["job"]["candidate_coverage"][0]
        assert payload["job"]["evidence_gap_tasks"][0]["ticker"] == "MU"
        assert payload["job"]["evidence_gap_tasks"][0]["search_prompt"].startswith("MU ")
        assert payload["job"]["preflight_source"] == "backend"
        assert not payload["job"].get("href")

        status, _, runs_body = _http_get(f"{base_url}/api/runs")
        assert status == 200
        runs = json.loads(runs_body)["runs"]
        assert runs[0]["query"] == "HBM"
        assert runs[0]["job_id"] == payload["job"]["job_id"]
        assert runs[0]["status"] in {"queued", "running"}
        assert not runs[0]["completed_at"]
        assert runs[0]["canonical_theme"] == "HBM"
        assert runs[0]["candidate_tickers"][:1] == ["MU"]
        assert runs[0]["coverage_label"].endswith("条证据")
        assert runs[0]["candidate_coverage"][0]["ticker"] == "MU"
        assert runs[0]["candidate_coverage"][0]["evidence_count"] >= 1
        assert runs[0]["evidence_gap_tasks"][0]["ticker"] == "MU"

        release_job.set()
        for _ in range(20):
            status, _, runs_body = _http_get(f"{base_url}/api/runs")
            assert status == 200
            runs = json.loads(runs_body)["runs"]
            if runs[0]["status"] == "completed":
                break
        assert observed_runs
        assert observed_runs[0]["job_id"] == payload["job"]["job_id"]
        assert observed_runs[0]["canonical_theme"] == "HBM"
        assert observed_runs[0]["candidate_tickers"][:1] == ["MU"]
        assert observed_runs[0]["coverage_label"].endswith("条证据")
        assert observed_runs[0]["candidate_coverage"][0]["ticker"] == "MU"
        assert observed_runs[0]["candidate_coverage"][0]["evidence_count"] >= 1
        assert observed_runs[0]["evidence_gap_tasks"][0]["ticker"] == "MU"
        assert runs[0]["status"] == "completed"
        assert runs[0]["href"].endswith("/analyses/async-demo/index.zh.html")
        assert runs[0]["completed_at"]
        assert runs[0]["canonical_theme"] == "HBM"
        assert runs[0]["candidate_tickers"][:1] == ["MU"]
        assert runs[0]["coverage_label"].endswith("条证据")
        assert runs[0]["candidate_coverage"][0]["ticker"] == "MU"
        assert runs[0]["candidate_coverage"][0]["evidence_count"] >= 1
        assert runs[0]["evidence_gap_tasks"][0]["ticker"] == "MU"
        assert runs[0]["evidence_gap_tasks"][0]["import_handoff_href"].endswith(
            "/analyses/async-demo/index.zh.html#evidence-tasks"
        )
        status, _, detail_body = _http_get(f"{base_url}/api/analyze-jobs?jobId={payload['job']['job_id']}")
        assert status == 200
        detail = json.loads(detail_body)["job"]
        assert detail["evidence_gap_tasks"][0]["ticker"] == "MU"
        assert detail["href"].endswith("/analyses/async-demo/index.zh.html")
        assert detail["evidence_gap_tasks"][0]["import_handoff_href"].endswith(
            "/analyses/async-demo/index.zh.html#evidence-tasks"
        )
        status, _, refreshed_home = _http_get(f"{base_url}/index.zh.html")
        assert status == 200
        assert "打开补证导入" in refreshed_home
        assert "openEvidenceTaskImportHandoff" in refreshed_home
    finally:
        release_job.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_analyze_jobs_lookup_and_retry_failed_job(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")
    attempts: list[str] = []

    def analyze_theme(*, query: str, language: str = "en") -> Path:
        attempts.append(query)
        if len(attempts) == 1:
            raise RuntimeError("first async attempt failed")
        analysis_dir = ui_dir / "analyses" / "retry-demo"
        analysis_dir.mkdir(parents=True)
        output = analysis_dir / ("index.zh.html" if language == "zh" else "index.html")
        output.write_text(f"<html><body>{query} retry</body></html>", encoding="utf-8")
        return output

    handler = _build_dashboard_handler(ui_dir, analyze_theme)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_json_post(
            f"{base_url}/api/analyze-jobs",
            {"query": "HBM", "language": "zh"},
        )
        assert status == 202
        first_job = json.loads(body)["job"]
        first_job_id = first_job["job_id"]

        for _ in range(20):
            status, _, detail_body = _http_get(f"{base_url}/api/analyze-jobs?jobId={first_job_id}")
            assert status == 200
            detail = json.loads(detail_body)["job"]
            if detail["status"] == "failed":
                break
        assert detail["job_id"] == first_job_id
        assert detail["query"] == "HBM"
        assert detail["language"] == "zh"
        assert detail["status"] == "failed"
        assert detail["error"] == "first async attempt failed"
        assert detail["attempt"] == 1

        status, _, missing_body = _http_get(f"{base_url}/api/analyze-jobs?jobId=missing-job")
        assert status == 404
        assert "Job not found" in missing_body

        status, _, retry_body = _http_json_post(
            f"{base_url}/api/analyze-jobs",
            {"retry_job_id": first_job_id},
        )
        assert status == 202
        retry_job = json.loads(retry_body)["job"]
        assert retry_job["query"] == "HBM"
        assert retry_job["language"] == "zh"
        assert retry_job["retry_of_job_id"] == first_job_id
        assert retry_job["attempt"] == 2
        assert retry_job["job_id"] != first_job_id

        for _ in range(20):
            status, _, detail_body = _http_get(f"{base_url}/api/analyze-jobs?jobId={retry_job['job_id']}")
            assert status == 200
            detail = json.loads(detail_body)["job"]
            if detail["status"] == "completed":
                break
        assert detail["status"] == "completed"
        assert detail["retry_of_job_id"] == first_job_id
        assert detail["attempt"] == 2
        assert detail["href"].endswith("/analyses/retry-demo/index.zh.html")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_analyze_jobs_cancel_running_job(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")
    release_job = threading.Event()
    observed_runs: list[dict[str, object]] = []

    def analyze_theme(*, query: str, language: str = "en") -> Path:
        runs_path = ui_dir / "runs.json"
        observed_runs.append(json.loads(runs_path.read_text(encoding="utf-8"))["runs"][0])
        release_job.wait(timeout=5)
        analysis_dir = ui_dir / "analyses" / "cancel-demo"
        analysis_dir.mkdir(parents=True)
        output = analysis_dir / ("index.zh.html" if language == "zh" else "index.html")
        output.write_text(f"<html><body>{query} cancelled late</body></html>", encoding="utf-8")
        return output

    handler = _build_dashboard_handler(ui_dir, analyze_theme)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_json_post(
            f"{base_url}/api/analyze-jobs",
            {"query": "HBM", "language": "zh"},
        )
        assert status == 202
        job = json.loads(body)["job"]
        job_id = job["job_id"]

        for _ in range(20):
            status, _, detail_body = _http_get(f"{base_url}/api/analyze-jobs?jobId={job_id}")
            assert status == 200
            detail = json.loads(detail_body)["job"]
            if detail["status"] == "running":
                break
        assert detail["status"] == "running"

        status, _, cancel_body = _http_json_post(
            f"{base_url}/api/analyze-jobs",
            {"job_id": job_id, "cancel": True},
        )
        assert status == 200
        cancelled = json.loads(cancel_body)["job"]
        assert cancelled["job_id"] == job_id
        assert cancelled["status"] == "cancelled"
        assert cancelled["cancelled_at"]
        assert cancelled["completed_at"]
        assert "cancel" in cancelled["error"].lower()

        release_job.set()
        for _ in range(20):
            status, _, detail_body = _http_get(f"{base_url}/api/analyze-jobs?jobId={job_id}")
            assert status == 200
            detail = json.loads(detail_body)["job"]
            if detail["status"] == "cancelled":
                break
        assert observed_runs
        assert detail["status"] == "cancelled"
        assert not detail.get("href")
    finally:
        release_job.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_failed_analysis_page_has_retry_action(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    def analyze_theme(*, query: str, language: str = "en") -> Path:
        raise RuntimeError("simulated lifecycle failure")

    handler = _build_dashboard_handler(ui_dir, analyze_theme)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_get(f"{base_url}/analyze?query=HBM&language=zh")
        assert status == 500
        assert "分析生成失败" in body
        assert "simulated lifecycle failure" in body
        assert 'href="/analyze?query=HBM&amp;language=zh"' in body
        assert "重新生成" in body
        assert 'href="/index.zh.html"' in body
        assert "返回首页" in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_project_library_api_persists_projects(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    handler = _build_dashboard_handler(ui_dir, analyze_callback=None)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_get(f"{base_url}/api/projects")
        assert status == 200
        payload = json.loads(body)
        assert payload["projects"] == []

        status, _, saved_body = _http_json_post(
            f"{base_url}/api/projects",
            {
                "project": {
                    "id": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "query": "HBM",
                    "href": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "status": "pending-evidence",
                    "quality": {"status": "需补证据", "score": "48/100"},
                    "topTicker": "MU",
                    "gap": "missing_primary_source",
                    "owner": "evidence-owner",
                    "savedAt": "2026-07-06T00:00:00Z",
                }
            },
        )
        assert status == 200
        saved = json.loads(saved_body)
        assert saved["projects"][0]["query"] == "HBM"
        assert saved["projects"][0]["status"] == "pending-evidence"
        assert saved["projects"][0]["quality"]["score"] == "48/100"
        assert saved["projects"][0]["topTicker"] == "MU"
        assert saved["projects"][0]["owner"] == "evidence-owner"
        assert (ui_dir / "projects.json").exists()

        status, _, listed_body = _http_get(f"{base_url}/api/projects")
        assert status == 200
        listed = json.loads(listed_body)
        assert listed["projects"][0]["query"] == "HBM"
        assert listed["projects"][0]["owner"] == "evidence-owner"

        status, _, updated_body = _http_json_post(
            f"{base_url}/api/projects",
            {
                "project": {
                    "id": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "query": "HBM",
                    "href": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "status": "delivered",
                    "quality": {"status": "可发布", "score": "82/100"},
                    "topTicker": "MU",
                    "gap": "",
                    "owner": "report-reviewer",
                    "savedAt": "2026-07-06T01:00:00Z",
                }
            },
        )
        assert status == 200
        updated = json.loads(updated_body)
        assert len(updated["projects"]) == 1
        assert updated["projects"][0]["status"] == "delivered"
        assert updated["projects"][0]["owner"] == "report-reviewer"
        assert updated["projects"][0]["quality"]["score"] == "82/100"

        status, _, cleared_body = _http_json_post(f"{base_url}/api/projects", {"clear": True})
        assert status == 200
        cleared = json.loads(cleared_body)
        assert cleared["projects"] == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_project_review_event_api_persists_events(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    handler = _build_dashboard_handler(ui_dir, analyze_callback=None)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_get(f"{base_url}/api/project-events")
        assert status == 200
        payload = json.loads(body)
        assert payload["events"] == []

        status, _, saved_body = _http_json_post(
            f"{base_url}/api/project-events",
            {
                "event": {
                    "id": "event-1",
                    "projectId": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "projectQuery": "HBM",
                    "type": "detail-opened",
                    "label": "已打开详情",
                    "at": "2026-07-06T02:00:00Z",
                }
            },
        )
        assert status == 200
        saved = json.loads(saved_body)
        assert saved["events"][0]["projectId"] == "/analyses/hbm-6f259a8f14/index.zh.html"
        assert saved["events"][0]["projectQuery"] == "HBM"
        assert saved["events"][0]["type"] == "detail-opened"
        assert saved["events"][0]["label"] == "已打开详情"
        assert (ui_dir / "project_review_events.json").exists()

        status, _, queue_body = _http_json_post(
            f"{base_url}/api/project-events",
            {
                "event": {
                    "id": "event-queue",
                    "projectId": "queue-handoff",
                    "projectQuery": "项目队列交接",
                    "type": "queue-handoff-copied",
                    "label": "已复制队列交接",
                    "at": "2026-07-06T02:10:00Z",
                }
            },
        )
        assert status == 200
        queue_saved = json.loads(queue_body)
        assert queue_saved["events"][0]["projectId"] == "queue-handoff"
        assert queue_saved["events"][0]["projectQuery"] == "项目队列交接"
        assert queue_saved["events"][0]["type"] == "queue-handoff-copied"
        assert queue_saved["events"][0]["label"] == "已复制队列交接"

        status, _, owner_body = _http_json_post(
            f"{base_url}/api/project-events",
            {
                "event": {
                    "id": "event-owner",
                    "projectId": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "projectQuery": "HBM",
                    "type": "owner-changed",
                    "label": "负责人已更新",
                    "at": "2026-07-06T02:20:00Z",
                }
            },
        )
        assert status == 200
        owner_saved = json.loads(owner_body)
        assert owner_saved["events"][0]["projectId"] == "/analyses/hbm-6f259a8f14/index.zh.html"
        assert owner_saved["events"][0]["projectQuery"] == "HBM"
        assert owner_saved["events"][0]["type"] == "owner-changed"
        assert owner_saved["events"][0]["label"] == "负责人已更新"

        status, _, listed_body = _http_get(f"{base_url}/api/project-events")
        assert status == 200
        listed = json.loads(listed_body)
        assert listed["events"][0]["id"] == "event-owner"

        status, _, filtered_body = _http_get(
            f"{base_url}/api/project-events?projectId=/analyses/hbm-6f259a8f14/index.zh.html"
        )
        assert status == 200
        filtered = json.loads(filtered_body)
        assert len(filtered["events"]) == 2
        assert filtered["events"][0]["type"] == "owner-changed"
        assert filtered["events"][0]["projectQuery"] == "HBM"

        status, _, invalid_body = _http_json_post(f"{base_url}/api/project-events", {"event": "bad"})
        assert status == 400
        assert "Missing project review event payload" in invalid_body

        status, _, cleared_body = _http_json_post(f"{base_url}/api/project-events", {"clear": True})
        assert status == 200
        cleared = json.loads(cleared_body)
        assert cleared["events"] == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_project_evidence_audit_api_persists_entries(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    handler = _build_dashboard_handler(ui_dir, analyze_callback=None)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_get(f"{base_url}/api/project-evidence-audits")
        assert status == 200
        payload = json.loads(body)
        assert payload["audits"] == []

        status, _, saved_body = _http_json_post(
            f"{base_url}/api/project-evidence-audits",
            {
                "audit": {
                    "id": "audit-1",
                    "projectId": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "projectQuery": "HBM",
                    "taskId": "task-primary-source",
                    "ticker": "MU",
                    "type": "verified-task",
                    "label": "已验证任务审计轨迹",
                    "qualityBefore": "48/100",
                    "qualityAfter": "56/100",
                    "qualityDelta": "+8",
                    "at": "2026-07-06T02:00:00Z",
                }
            },
        )
        assert status == 200
        saved = json.loads(saved_body)
        assert saved["audits"][0]["projectId"] == "/analyses/hbm-6f259a8f14/index.zh.html"
        assert saved["audits"][0]["projectQuery"] == "HBM"
        assert saved["audits"][0]["taskId"] == "task-primary-source"
        assert saved["audits"][0]["ticker"] == "MU"
        assert saved["audits"][0]["qualityDelta"] == "+8"
        assert (ui_dir / "project_evidence_audits.json").exists()

        status, _, listed_body = _http_get(f"{base_url}/api/project-evidence-audits")
        assert status == 200
        listed = json.loads(listed_body)
        assert listed["audits"][0]["id"] == "audit-1"

        status, _, filtered_body = _http_get(
            f"{base_url}/api/project-evidence-audits?projectId=/analyses/hbm-6f259a8f14/index.zh.html"
        )
        assert status == 200
        filtered = json.loads(filtered_body)
        assert len(filtered["audits"]) == 1
        assert filtered["audits"][0]["projectQuery"] == "HBM"
        assert filtered["audits"][0]["qualityBefore"] == "48/100"
        assert filtered["audits"][0]["qualityAfter"] == "56/100"
        assert filtered["summary"]["projectId"] == "/analyses/hbm-6f259a8f14/index.zh.html"
        assert filtered["summary"]["ticker"] == "MU"
        assert filtered["summary"]["qualityBefore"] == "48/100"
        assert filtered["summary"]["qualityAfter"] == "56/100"
        assert filtered["summary"]["qualityDelta"] == "+8"

        status, _, invalid_body = _http_json_post(f"{base_url}/api/project-evidence-audits", {"audit": "bad"})
        assert status == 400
        assert "Missing project evidence audit payload" in invalid_body

        status, _, cleared_body = _http_json_post(f"{base_url}/api/project-evidence-audits", {"clear": True})
        assert status == 200
        cleared = json.loads(cleared_body)
        assert cleared["audits"] == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_project_library_api_includes_latest_quality_delta(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    handler = _build_dashboard_handler(ui_dir, analyze_callback=None)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        project_id = "/analyses/hbm-6f259a8f14/index.zh.html"
        status, _, project_body = _http_json_post(
            f"{base_url}/api/projects",
            {
                "project": {
                    "id": project_id,
                    "query": "HBM",
                    "href": project_id,
                    "status": "pending-evidence",
                    "quality": {"status": "需补证据", "score": "48/100"},
                    "topTicker": "MU",
                    "gap": "missing_primary_source",
                    "savedAt": "2026-07-06T00:00:00Z",
                }
            },
        )
        assert status == 200
        saved_project = json.loads(project_body)["projects"][0]
        assert saved_project.get("evidenceQualitySummary", {}) == {}

        status, _, _ = _http_json_post(
            f"{base_url}/api/project-evidence-audits",
            {
                "audit": {
                    "id": "audit-quality-delta",
                    "projectId": project_id,
                    "projectQuery": "HBM",
                    "taskId": "task-primary-source",
                    "ticker": "MU",
                    "type": "verified-task",
                    "label": "已验证任务审计轨迹",
                    "qualityBefore": "48/100",
                    "qualityAfter": "56/100",
                    "qualityDelta": "+8",
                    "at": "2026-07-06T02:00:00Z",
                }
            },
        )
        assert status == 200

        status, _, listed_body = _http_get(f"{base_url}/api/projects")
        assert status == 200
        listed_project = json.loads(listed_body)["projects"][0]
        assert listed_project["id"] == project_id
        assert listed_project["evidenceQualitySummary"]["ticker"] == "MU"
        assert listed_project["evidenceQualitySummary"]["taskId"] == "task-primary-source"
        assert listed_project["evidenceQualitySummary"]["qualityBefore"] == "48/100"
        assert listed_project["evidenceQualitySummary"]["qualityAfter"] == "56/100"
        assert listed_project["evidenceQualitySummary"]["qualityDelta"] == "+8"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_task_status_api_persists_statuses(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    handler = _build_dashboard_handler(ui_dir, analyze_callback=None)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _, body = _http_get(f"{base_url}/api/task-statuses")
        assert status == 200
        payload = json.loads(body)
        assert payload["statuses"] == []

        status, _, saved_body = _http_json_post(
            f"{base_url}/api/task-statuses",
            {
                "status": {
                    "id": "task-primary-source",
                    "projectId": "/analyses/hbm-6f259a8f14/index.zh.html",
                    "taskId": "task-primary-source",
                    "ticker": "MU",
                    "status": "verified",
                    "updatedAt": "2026-07-06T02:00:00Z",
                }
            },
        )
        assert status == 200
        saved = json.loads(saved_body)
        assert saved["statuses"][0]["projectId"] == "/analyses/hbm-6f259a8f14/index.zh.html"
        assert saved["statuses"][0]["taskId"] == "task-primary-source"
        assert saved["statuses"][0]["ticker"] == "MU"
        assert saved["statuses"][0]["status"] == "verified"
        assert (ui_dir / "task_statuses.json").exists()

        status, _, listed_body = _http_get(f"{base_url}/api/task-statuses")
        assert status == 200
        listed = json.loads(listed_body)
        assert listed["statuses"][0]["id"] == "task-primary-source"

        status, _, filtered_body = _http_get(
            f"{base_url}/api/task-statuses?projectId=/analyses/hbm-6f259a8f14/index.zh.html"
        )
        assert status == 200
        filtered = json.loads(filtered_body)
        assert len(filtered["statuses"]) == 1
        assert filtered["statuses"][0]["status"] == "verified"

        status, _, invalid_body = _http_json_post(f"{base_url}/api/task-statuses", {"status": "bad"})
        assert status == 400
        assert "Missing task status payload" in invalid_body

        status, _, invalid_status_body = _http_json_post(
            f"{base_url}/api/task-statuses",
            {"status": {"taskId": "task-primary-source", "status": "done"}},
        )
        assert status == 400
        assert "Invalid task status value" in invalid_status_body

        status, _, cleared_body = _http_json_post(f"{base_url}/api/task-statuses", {"clear": True})
        assert status == 200
        cleared = json.loads(cleared_body)
        assert cleared["statuses"] == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_project_library_api_includes_evidence_progress(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    handler = _build_dashboard_handler(ui_dir, analyze_callback=None)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        project_id = "/analyses/hbm-6f259a8f14/index.zh.html"
        status, _, project_body = _http_json_post(
            f"{base_url}/api/projects",
            {
                "project": {
                    "id": project_id,
                    "query": "HBM",
                    "href": project_id,
                    "status": "pending-evidence",
                    "quality": {"status": "需补证据", "score": "48/100"},
                    "topTicker": "MU",
                    "gap": "missing_primary_source",
                    "savedAt": "2026-07-06T00:00:00Z",
                }
            },
        )
        assert status == 200
        saved_project = json.loads(project_body)["projects"][0]
        assert saved_project.get("evidenceProgressSummary", {}) == {}

        for task_id, task_status in [
            ("task-primary-source", "verified"),
            ("task-risk", "collected"),
            ("task-customer-check", "to_collect"),
        ]:
            status, _, _ = _http_json_post(
                f"{base_url}/api/task-statuses",
                {
                    "status": {
                        "id": task_id,
                        "projectId": project_id,
                        "taskId": task_id,
                        "ticker": "MU",
                        "status": task_status,
                        "updatedAt": "2026-07-06T02:00:00Z",
                    }
                },
            )
            assert status == 200

        status, _, listed_body = _http_get(f"{base_url}/api/projects")
        assert status == 200
        listed_project = json.loads(listed_body)["projects"][0]
        assert listed_project["id"] == project_id
        progress = listed_project["evidenceProgressSummary"]
        assert progress["total"] == 3
        assert progress["verified"] == 1
        assert progress["collected"] == 1
        assert progress["toCollect"] == 1
        assert progress["label"] == "1/3 verified"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_e2e_project_library_api_includes_next_action_summary(tmp_path):
    readiness, pack_dir = _write_home_pack(tmp_path)
    ui_dir = tmp_path / "ui"
    out = ui_dir / "index.html"
    build_dashboard(readiness_path=readiness, pack_dir=pack_dir, output_path=out, language="both")

    handler = _build_dashboard_handler(ui_dir, analyze_callback=None)
    server = ReusableTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        project_id = "/analyses/hbm-6f259a8f14/index.zh.html"
        status, _, _ = _http_json_post(
            f"{base_url}/api/projects",
            {
                "project": {
                    "id": project_id,
                    "query": "HBM",
                    "href": project_id,
                    "status": "pending-evidence",
                    "quality": {"status": "需补证据", "score": "48/100"},
                    "topTicker": "MU",
                    "gap": "missing_primary_source",
                    "savedAt": "2026-07-06T00:00:00Z",
                }
            },
        )
        assert status == 200
        for task_id, task_status in [
            ("task-primary-source", "verified"),
            ("task-risk", "collected"),
            ("task-customer-check", "to_collect"),
        ]:
            status, _, _ = _http_json_post(
                f"{base_url}/api/task-statuses",
                {
                    "status": {
                        "id": task_id,
                        "projectId": project_id,
                        "taskId": task_id,
                        "ticker": "MU",
                        "status": task_status,
                        "updatedAt": "2026-07-06T02:00:00Z",
                    }
                },
            )
            assert status == 200

        status, _, listed_body = _http_get(f"{base_url}/api/projects")
        assert status == 200
        listed_project = json.loads(listed_body)["projects"][0]
        next_action = listed_project["nextActionSummary"]
        assert next_action["type"] == "collect-evidence"
        assert next_action["priority"] == "high"
        assert next_action["label"] == "Collect missing evidence"
        assert next_action["reason"] == "1 evidence task still needs collection"

        status, _, _ = _http_json_post(
            f"{base_url}/api/task-statuses",
            {
                "status": {
                    "id": "task-customer-check",
                    "projectId": project_id,
                    "taskId": "task-customer-check",
                    "ticker": "MU",
                    "status": "verified",
                    "updatedAt": "2026-07-06T03:00:00Z",
                }
            },
        )
        assert status == 200
        status, _, ready_body = _http_get(f"{base_url}/api/projects")
        assert status == 200
        ready_project = json.loads(ready_body)["projects"][0]
        ready_action = ready_project["nextActionSummary"]
        assert ready_action["type"] == "review-report"
        assert ready_action["priority"] == "medium"
        assert ready_action["label"] == "Review report"
        assert ready_action["reason"] == "Evidence tasks are complete; review thesis, risks, and invalidation conditions"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
