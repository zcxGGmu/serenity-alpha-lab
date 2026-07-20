# ResearchOrchestrator 协议与 DSA 兼容 Facade 记录

> 任务：`SAL-P1-009` 抽取 ResearchOrchestrator<br>
> 日期：2026-07-20<br>
> Phase：P1 工程加固<br>
> Gate：G1 未通过<br>
> 范围：应用层 ResearchOrchestrator 协议、请求/结果 DTO、DSA `AgentOrchestrator.run/chat` 注入式兼容 facade；不迁移 API route、不启动 Provider/LLM 调用、不实现 Agent checkpoint 或 Evidence Agent。

## 目标

`ResearchOrchestrator` 把 API、Worker、Bot 和后续 Agent 持久化工作与 DSA 具体 `AgentOrchestrator` / `AgentExecutor` 类隔离开。P1 先冻结 dashboard 与 chat 两类调用的稳定协议，并保留 DSA 当前结果语义。

## 应用层契约

`src/serenity_alpha_lab/application/research_orchestrator.py` 定义：

| 类型 | 作用 |
|---|---|
| `ResearchRequest` | Dashboard 研究请求，包含 `run_id`、`query`、`context`、`mode` 和可选幂等 key。 |
| `ResearchChatRequest` | Chat 研究请求，包含 `run_id`、`message`、`session_id`、`context`、显式 `skills` 和可选幂等 key。 |
| `ResearchResult` | 与 DSA `AgentResult` 兼容的稳定输出，保留 `success/content/dashboard/tool_calls_log/total_steps/total_tokens/provider/model/error`。 |
| `ResearchOrchestrator` | Protocol：`run()` 与 `chat()`。 |
| `ProgressCallback` | Chat/streaming 进度事件回调类型。 |

请求对象会浅层规范字段并深拷贝 context，避免 facade 写入污染调用方输入。

## DSA Facade

`src/serenity_alpha_lab/integrations/dsa/research_orchestrator.py` 提供 `DsaResearchOrchestratorFacade`：

- 通过构造函数注入 DSA-like orchestrator，不在模块顶层导入 `src.agent.orchestrator`。
- `run()` 调用注入对象的 `run(task, context=...)`，并映射 legacy `AgentResult` 字段。
- `chat()` 调用注入对象的 `chat(message=..., session_id=..., progress_callback=..., context=...)`。
- 显式 `skills` 会覆盖 chat context 中旧的 `skills/strategies`，与 DSA Agent API 当前语义一致。
- legacy 异常会包装为 `ResearchOrchestratorError`，但 legacy 失败结果本身不被重新解释。

## 范围限制

- 不复制、不迁移 DSA `src/agent/orchestrator.py`、`src/agent/executor.py` 或 API route。
- 不修改 `/api/v1/agent/chat`、`/chat/stream`、`/research` 行为。
- 不实现 Agent checkpoint、阶段持久化、Evidence Agent、Citation Validator、Provider 调用、模型调用、Quant Core、PIT Dataset 或正式回测。
- Deep Research `ResearchAgent` 仍保留在 DSA legacy 路径；本任务仅为主 Agent Orchestrator 建立兼容外壳。

## 验证

| 验证 | 结果 |
|---|---|
| Red 测试 | `tests/application/test_research_orchestrator_contract.py` 和 `tests/integrations/test_dsa_research_orchestrator_facade.py` 初始因缺少 `serenity_alpha_lab.application.research_orchestrator` 失败 |
| 目标测试 | `.cache/dsa-p0/venv/bin/python -m pytest tests/application/test_research_orchestrator_contract.py tests/integrations/test_dsa_research_orchestrator_facade.py tests/architecture/test_architecture_boundaries.py -q`：`16 passed` |
| 相关套件 | `.cache/dsa-p0/venv/bin/python -m pytest tests/application tests/integrations tests/architecture -q`：`43 passed` |
| 全量 pytest | `.cache/dsa-p0/venv/bin/python -m pytest -q`：`90 passed` |
| 依赖与状态保护 | `scripts/verify-python-dependency-lock.sh`、`git diff --check`、`git rev-parse upstream/dsa-v3.26.1` 通过 |
| 语法检查 | `py_compile` 覆盖新 application/facade/test/export 文件，通过 |

## 后续衔接

- `SAL-P5-001` Evidence Schema 可在 `ResearchResult.metadata` 或后续扩展 DTO 中接入证据引用，但不得让 LLM 自行伪造引用。
- `SAL-P5-011` Agent checkpoint persistence 必须经该 Protocol 绑定 `run_id/stage_id`，不得绕过 facade 直接调用 DSA 类。
- `SAL-P1-010` API 错误协议可把 `ResearchOrchestratorError` 映射为统一 problem detail。
