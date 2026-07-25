# Lessons

## 2026-07-25: SAL-P4-006 后状态复核必须把最终固化锚点写入恢复提示

- 纠正来源：`SAL-P4-006` 实现 checkpoint `1c5c6e81`、状态同步 checkpoint `76089299`、状态同步 hash-anchor `64c7998e` 和最终锚点固化提交 `ea244bdc` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并再次强调“每个阶段性任务完成后自动去做”。
- 模式：即使实现、状态同步和 hash-anchor 已提交，如果 `docs/development-status.md` 的“最新状态复核 checkpoint”仍停留在上一阶段任务，或最终交接没有给出可直接复用的启动提示词，下次恢复仍会误判当前任务是否已完整收尾。
- 规则：阶段性任务完成后，最终交接前必须再次复核并更新 `docs/development-status.md`、`docs/development-progress-checklist.md` 和 `tasks/todo.md`：明确最近实现 checkpoint、状态同步 checkpoint、hash-anchor/final anchor、完成/未完成范围、当前 READY 任务、严格禁区和完整可复制提示词；用户再次提醒该习惯时必须追加本文件并提交中文状态复核 checkpoint。
- 执行：后续从 `SAL-P4-007` 开始，不等待用户提醒；每个阶段性交付后自动执行实现提交、状态同步、必要 hash-anchor、状态复核、`tasks/lessons.md` 更新（若有纠正）和最终可复制启动提示词。

## 2026-07-25: SAL-P4-006 子代理派发失败时必须立即降级为本地复核并记录

- 纠正来源：`SAL-P4-006` 收尾期间多次尝试 code-review subagent，host wrapper 对空 optional fields、`message`/`items` 同时出现以及空 `items` 均拒绝，导致派发无法完成。
- 模式：如果反复调整 subagent payload 仍被平台包装层拒绝，继续重试会消耗上下文且不增加验证质量；但 AGENTS.md 仍要求使用子代理策略，因此必须把尝试、失败原因和本地复核范围写入 review。
- 规则：后续阶段任务需要 code review subagent 时，只做一次最小 payload 尝试；若仍因包装层 schema 被拒绝，立即停止重试，改为本地 senior review + 新鲜验证，并在 `tasks/todo.md` review 中记录 fallback。
- 执行：从 `SAL-P4-007` 开始，子代理失败不得阻断实现/验证/状态同步；最终完成声明仍以本轮实际测试、diff review 和 checkpoint 为准。

## 2026-07-25: SAL-P4-005 后状态复核必须记录 hash-anchor 与可复制提示词

- 纠正来源：`SAL-P4-005` 实现 checkpoint `82580fdb`、状态同步 checkpoint `800bef4e` 和状态同步 hash-anchor `ee5761ba` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并再次强调“每个阶段性任务完成后自动去做”。
- 模式：即使已经完成实现提交、状态同步提交和 hash-anchor 提交，如果 `docs/development-status.md` 的最新状态复核仍停留在更早的 P3 checkpoint，或下次启动提示词没有列出最新 hash-anchor，下次恢复时仍会误以为状态同步不完整。
- 规则：每个阶段性任务完成后，必须把最近实现 checkpoint、最新状态同步 checkpoint、最新 hash-anchor checkpoint、完成/未完成范围、当前 READY 任务、严格禁区和完整可复制启动提示词同时写入 `docs/development-status.md`、`docs/development-progress-checklist.md` 与 `tasks/todo.md`；用户再次提醒该习惯时，立即更新本文件并提交中文状态复核 checkpoint。
- 执行：后续从 `SAL-P4-006` 开始，完成阶段任务后自动完成实现/验证/证据/状态/lessons/恢复提示词收尾；最终回复必须直接给出最新实现 checkpoint、状态同步或状态复核 checkpoint、hash-anchor checkpoint 和完整下次启动提示词。

## 2026-07-25: SAL-P3-015 后状态复核必须保留最新已落地复核 checkpoint

- 纠正来源：`SAL-P3-015` 实现 checkpoint `847e5263`、状态同步 checkpoint `fa0ba469` 与状态复核 checkpoint `3c19b937` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并再次强调“每个阶段性任务完成后自动去做”。
- 模式：即使已经有状态复核提交，如果恢复提示词仍只写“本次状态复核 checkpoint 提交后以最终回复为准”，下一次启动仍需要人工追溯最新已落地复核提交。
- 规则：每次状态同步或状态复核都必须保留上一已落地实现 checkpoint、状态同步 checkpoint、状态复核 checkpoint、完成/未完成范围、当前 READY 任务和严格禁区；新的复核提交可以用提交后确认语句，但不得覆盖或省略上一已落地复核 hash。
- 执行：后续从 `SAL-P3-016` 开始，阶段性任务完成后自动完成状态快照、进度清单、证据、风险/决策、`tasks/todo.md` review、必要 lessons、可复制启动提示词和中文 checkpoint commit；最终回复必须直接给出最新提交 hash 与完整下次启动提示词。

## 2026-07-25: SAL-P3-014 后状态复核必须写清最新已落地状态同步 checkpoint

- 纠正来源：`SAL-P3-014` 实现 checkpoint `dd4e9465` 与状态同步 checkpoint `cd0d6c6f` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求直接给出下次启动提示词，同时再次强调“每个阶段性任务完成后自动去做”。
- 模式：即使上一轮已经提交状态同步，如果恢复文档仍写“本次状态同步提交生成后以 git log 为准”，下次启动仍需要人工判断哪个 hash 是最新已落地状态同步，降低恢复确定性。
- 规则：每个阶段性任务完成后，最终交接前必须把最近实现 checkpoint、最新已落地状态同步 checkpoint、完成/未完成范围、当前 READY 任务、严格禁区和完整可复制启动提示词写入 `docs/development-status.md`、`docs/development-progress-checklist.md` 与 `tasks/todo.md`；如果随后又做状态复核提交，文档可写明“本次状态复核 checkpoint 以提交后 `git log -1 --oneline` 和最终回复为准”，但不得丢失上一已落地状态同步实际 hash。
- 执行：后续从 `SAL-P3-015` 开始，不等待用户提醒；阶段性任务完成后自动做状态/清单/证据/风险/决策/`tasks/todo.md` review/必要 lessons/可复制提示词收尾，并在最终回复直接给出最新实现 checkpoint、最新状态同步或状态复核 checkpoint 和完整下次启动提示词。

## 2026-07-24: SAL-P3-013 后状态复核必须把 docs sync 实际 hash 写入提示词

- 纠正来源：`SAL-P3-013` 实现 checkpoint `10d97975` 与状态同步 checkpoint `e0ca42d9` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求直接给出下次启动提示词，同时强调“每个阶段性任务完成后自动去做”。
- 模式：即使完成了实现提交和状态同步提交，如果恢复文档仍写“本次状态同步提交，标题为 ...”而没有实际 hash，下次启动仍需要人工用 `git log` 对齐状态同步锚点。
- 规则：每个阶段性任务完成后，最终交接前必须把最近实现 checkpoint、最新状态同步 checkpoint 的实际 hash、完成/未完成范围、当前 READY 任务、严格禁区和完整可复制启动提示词写入 `docs/development-status.md`、`docs/development-progress-checklist.md` 与 `tasks/todo.md`；用户再次提醒该习惯时，立即更新本文件并提交中文状态复核 checkpoint。
- 执行：后续从 `SAL-P3-014` 开始，不等待用户提醒；完成实现后自动进行状态/清单/证据/`tasks/todo.md` review/必要 lessons/可复制提示词收尾，且最终回复必须直接给出最新状态同步 checkpoint 和下次启动提示词。

## 2026-07-24: SAL-P3-007 后状态复核必须在最终交接给出实际 docs checkpoint

- 纠正来源：`SAL-P3-007` 实现 checkpoint `27b87c2e` 与状态同步 checkpoint `e3ce4840` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求“给我一个提示词，直接发给我”和“每个阶段性任务完成后自动去做”。
- 模式：即使状态文档已经包含完成范围和下一步，如果最终交接没有再次复核并给出最新 docs checkpoint 实际 hash，用户仍需要额外确认下次启动是否能直接恢复。
- 规则：每次阶段性任务后或用户提醒状态同步时，必须把最近实现 checkpoint、上一状态同步 checkpoint、已完成/未完成范围、当前 READY 任务、严格禁区和完整可复制启动提示词同步到 `docs/development-status.md`、`docs/development-progress-checklist.md` 与 `tasks/todo.md`；最终回复必须写出最新状态同步 checkpoint 的实际 hash。
- 执行：后续从 `SAL-P3-008` 开始，不等待用户提醒；实现完成后自动做状态/清单/证据/`tasks/todo.md` review/必要 lessons/可复制提示词收尾，并提交中文 checkpoint。

## 2026-07-24: SAL-P3-006 后状态复核必须写入最新状态同步 hash

- 纠正来源：`SAL-P3-006` 实现 checkpoint `a63822d0` 与状态同步 checkpoint `6ee91eed` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求直接给出下次启动提示词，同时再次强调“每个阶段性任务完成后自动去做”。
- 模式：即使已经做过实现提交和 checkpoint hash 同步，如果恢复提示词仍把“最新状态同步 checkpoint”写成“本文件所在提交”但没有记录上一状态同步实际 hash，下一次恢复仍需要额外比对 `git log` 才能确认文档是否已落地。
- 规则：每个阶段性任务完成后，最终交接前必须把最近实现 checkpoint、上一状态同步 checkpoint、完成/未完成范围、当前 READY 任务、严格禁区和完整可复制启动提示词同步到 `docs/development-status.md`、`docs/development-progress-checklist.md` 与 `tasks/todo.md`；用户再次提醒该习惯时，立即追加本文件并提交中文状态复核 checkpoint。
- 执行：后续从 `SAL-P3-007` 开始，不等待用户提醒；任务完成后自动完成实现/验证/证据/状态/lessons/启动提示词收尾，并在最终回复中直接给出可复制提示词。

## 2026-07-24: SAL-P3-005 后状态同步必须消除实现 checkpoint 占位

- 纠正来源：`SAL-P3-005` 实现 checkpoint `d405e6ab` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求“给我一个提示词，直接发给我”和“每个阶段性任务完成后自动去做”。
- 模式：阶段性实现提交虽然已经包含状态更新，但如果恢复文档仍保留“本次实现提交”“将由本次提交生成”等占位表达，下次启动仍需要人工查询实际 hash，无法直接从文档判断当前进度。
- 规则：每个阶段性任务完成后，最终交接前必须把实际实现 checkpoint 写入 `docs/development-status.md`、`docs/development-progress-checklist.md` 和下次启动提示词；若用户再次提醒该习惯，立即追加本文件，并提交中文状态复核 checkpoint。
- 执行：后续从 `SAL-P3-006` 开始，不等待用户提醒；任务完成后自动同步状态、清单、证据、`tasks/todo.md` review、必要 lessons、实际 checkpoint 和可复制启动提示词，再运行状态锚点扫描与 `git diff --check`。

## 2026-07-23: SAL-P3-002 后状态复核必须补齐最新状态同步锚点

- 纠正来源：`SAL-P3-002` 实现 checkpoint `50012b44` 与状态同步 `c53daa65` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求“给我一个提示词，直接发给我”和“每个阶段性任务完成后自动去做”。
- 模式：即使状态文档已更新到正确 Phase/Gate/下一任务，如果下次启动提示词没有纳入本阶段新增证据文档，或没有在最终交接中再次明确最新状态同步 checkpoint，恢复时仍可能漏读关键 evidence 或重复询问当前进度。
- 规则：每个阶段性任务完成后，最终交接前必须再次复核 `docs/development-status.md` 的下次启动提示词，确保包含本阶段新增 evidence 文档、最近实现 checkpoint、最新状态同步 checkpoint、完成/未完成范围、当前 READY 任务和严格禁区；用户再次提醒该习惯时，必须追加本文件并提交中文状态复核 checkpoint。
- 执行：后续从 `SAL-P3-003` 开始，不等待用户提醒；完成任务后自动同步状态、清单、证据、`tasks/todo.md` review、必要 lessons 和可复制启动提示词，并在最终回复直接给出完整 prompt。

## 2026-07-23: SAL-P3-001 后状态同步必须写入实际交付 hash

- 纠正来源：`SAL-P3-001` checkpoint `4e6d5ee4` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求直接给出下次启动提示词，同时再次强调“每个阶段性任务完成后自动去做”。
- 模式：即使实现 checkpoint 已经包含状态同步，如果恢复文档仍把最近交付写成“本文件所在提交”，下次启动仍要先人工确认实际 hash，降低可恢复性。
- 规则：每个阶段性任务完成后，最终交接前必须把最近可评审交付的实际 hash、完成范围、未完成起点、当前 READY 任务、严格禁区和可复制下次启动提示词写入 `docs/development-status.md` 与 `docs/development-progress-checklist.md`；若用户再次提醒该习惯，立即更新本文件并提交中文状态复核 checkpoint。
- 执行：后续从 `SAL-P3-002` 开始，不等待用户提醒；阶段性任务完成后先完成实现 checkpoint，再同步状态文档和 `tasks/todo.md` review，运行状态锚点扫描与 `git diff --check`，最终回复必须附完整下一次启动提示词。

## 2026-07-23: SAL-P2-016 后再次复核必须直接给出可复制启动提示词

- 纠正来源：`SAL-P2-016` 实现 checkpoint `cfadc415` 与状态同步 `70f82cee` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求“给我一个提示词，直接发给我”和“每个阶段性任务完成后自动去做”。
- 模式：即使状态文档已经更新，如果最终交接没有再次明确最新完成范围、未完成起点、当前 READY 任务、最近实现 checkpoint、最新状态同步 checkpoint 和可复制提示词，用户仍需要重复提醒才能放心恢复开发。
- 规则：每个阶段性任务完成后，最终回复前必须完成仓库内状态复核并直接给出可复制启动提示词；若用户再次提醒该习惯，立即更新本文件，运行状态锚点扫描和 `git diff --check`，提交中文状态复核 checkpoint。
- 执行：后续完成 `SAL-P2-017` 或任一 `SAL-*` 后，不等待用户提醒；先写清已完成/未完成/下一步/禁区/实际实现 checkpoint/状态同步锚点，再提交状态同步，最终回复必须附完整下一次启动提示词。

## 2026-07-23: SAL-P2-015 后状态同步必须写入实际实现 checkpoint

- 纠正来源：`SAL-P2-015` 实现 checkpoint `378ba734` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求把“每个阶段性任务完成后自动去做”固化为习惯。
- 模式：即使实现 commit 已经包含大部分状态同步，如果恢复文档里仍写“本文件所在提交”或“最近实现 checkpoint 将在本次提交生成”，下次启动时仍需要人工查询实际实现 hash，进度恢复不够直接。
- 规则：阶段性任务完成后的状态同步必须把最近可评审交付的实际 hash 写入 `docs/development-status.md`、`docs/development-progress-checklist.md` 和下次启动提示词；最新状态同步 commit 自身可以写标题并要求启动后用 `git log -1 --oneline` 确认实际 hash。
- 执行：后续完成 `SAL-P2-016` 或任一 `SAL-*` 后，不等待用户提醒；先写清已完成/未完成/下一步/禁区/实际实现 checkpoint，再更新 `tasks/todo.md` review 和本文件（若用户再次纠正习惯），最后运行状态扫描与 `git diff --check` 并提交中文 checkpoint/status-sync commit。

## 2026-07-23: SAL-P2-014 后状态复核必须再次固化恢复提示

- 纠正来源：`SAL-P2-014` 实现 checkpoint `5016ced6` 与状态同步 `8c70cde5` 后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并强调“每个阶段性任务完成后自动去做”。
- 模式：即使已经做过状态同步，只要用户再次要求恢复提示，就必须把实际完成范围、未完成起点、当前 READY 任务、最近实现 checkpoint、状态同步锚点和禁止提前进入的范围重新写入仓库文档，而不能只在聊天里回答。
- 规则：每个阶段性任务完成后，最终回复前必须执行一次状态复核：`git status --short --branch`、`git log -3 --oneline`、状态锚点扫描、`git diff --check`；若文档仍只写提交标题而没有足够恢复锚点，补写上一状态同步 hash 和恢复确认命令。
- 执行：后续完成 `SAL-P2-015` 或任一 `SAL-*` 后，自动同步 `docs/development-status.md`、`docs/development-progress-checklist.md`、相关证据文档和 `tasks/todo.md`，并在最终回复直接给出可复制的下次启动提示词；用户再次提醒该习惯时继续追加本文件。

## 2026-07-22: SAL-P2-010 后状态同步要避免模糊 checkpoint

- 纠正来源：`SAL-P2-010` checkpoint `3e2056fe` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求“我希望你能记住这个习惯，在每个阶段性任务完成后自动去做”。
- 模式：实现 checkpoint 已经包含状态同步时，如果恢复文档仍写“本文件所在提交”或 `tasks/todo.md` 里提交步骤未勾选，下次启动仍要人工判断哪些内容真实完成、哪个 commit 是实现交付、哪个任务可以继续。
- 规则：每个阶段性任务完成后，状态文档必须优先记录最近可评审交付的明确 hash、完成/未完成范围、当前 READY 任务和严格禁区；若另有状态同步提交，最终回复必须给出实际 docs checkpoint hash，文档中至少写清提交标题和恢复确认命令。
- 执行：后续完成 `SAL-P2-011` 或任一 `SAL-*` 后，除实现/验证/证据外，还必须复核 `tasks/todo.md` checklist 是否全勾选，更新 `docs/development-status.md` 的下次启动提示词，并在最终回复直接提供可复制提示词；不得再等待用户提醒。

## 2026-07-22: SAL-P2-008 后必须继续自动做状态同步

- 纠正来源：`SAL-P2-008` checkpoint `81e65230` 完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求“我希望你能记住这个习惯，在每个阶段性任务完成后自动去做”。
- 模式：阶段性交付完成后，即使已经同步过状态，如果最终文档和最终回复没有明确列出“已完成/未完成/下一步/可复制提示词/最近 checkpoint”，用户仍需要再次追问才能放心恢复开发。
- 规则：每个阶段性任务完成后，必须自动完成固定收尾：更新 `docs/development-status.md`、`docs/development-progress-checklist.md`、任务证据文档、决策/证据登记、`tasks/todo.md` review、`tasks/lessons.md`（若用户提醒习惯或指出偏差）和下次启动提示词；同时明确最近可评审交付 commit、当前完成度、当前 READY 任务和禁止提前进入的范围。
- 执行：后续完成 `SAL-P2-009` 或任一 `SAL-*` 后，不等待用户提醒；先做状态锚点扫描和 `git diff --check`，再提交中文 checkpoint/status-sync commit，最终回复必须附一段可直接复制给 Codex 的下次启动提示词。

## 2026-07-19: 阶段性任务收尾要自动同步恢复状态

- 纠正来源：用户要求“请更新文档的最新开发状态”和“我希望你能记住这个习惯，在每个阶段性任务完成后自动去做”；在 `SAL-P0-008` 完成后用户再次要求同步最新开发状态和下次启动提示词。
- 模式：阶段性任务完成后，如果只提交实现而没有同步状态快照、进度清单、证据和恢复提示，下次会话容易丢失真实进度，重复询问或误进入后续 Phase。
- 规则：每完成、阻塞或形成可评审交付的阶段性任务，必须在结束前同步 `docs/development-status.md`、`docs/development-progress-checklist.md`、受影响的验收证据/风险/决策登记、`tasks/todo.md` review 和下次启动提示词；可评审交付必须创建中文 checkpoint commit。
- 执行：后续完成 `SAL-P0-009`、`SAL-P0-010`、`SAL-P0-012` 或 Gate `SAL-P0-013` 时，不等待用户提醒，自动完成上述收尾动作；完成后最终回复必须直接给出可复制的下次启动提示词。

## 2026-07-20: 用户再次强调状态同步必须成为固定习惯

- 纠正来源：Gate G0 checkpoint 完成后，用户再次要求“请更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求下次启动提示词可直接继续开发。
- 模式：即使刚完成 checkpoint，也不能只在最终回复口头说明状态；必须确保仓库内状态文档本身已经能独立恢复上下文。
- 规则：每个阶段性任务结束后，最终回复前必须复核并必要时更新 `docs/development-status.md` 的已完成/未完成/下一步/下次启动提示词，复核 `docs/development-progress-checklist.md` 的完成度和当前任务，并把本次 review 写入 `tasks/todo.md`。
- 执行：若用户再次提醒“更新状态”或“记住这个习惯”，立即更新 `tasks/lessons.md`，并运行 `git status`、状态锚点扫描和 `git diff --check` 后再声称状态同步完成。

## 2026-07-20: 到达用户指定提示节点后仍要提交状态同步

- 纠正来源：用户在 Gate G1 已通过、项目进入 P2 后再次要求“请更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并强调“每个阶段性任务完成后自动去做”。
- 模式：即使阶段 Gate checkpoint 已经提交，也可能只在最终回复中提示用户，而没有追加一次明确的状态复核记录；这会让下次会话难以判断“已到 P2”是口头状态还是仓库内权威状态。
- 规则：每次到达用户要求的停顿/提示节点（例如“等到 P2 再提示我”）时，必须在最终回复前确认并必要时更新 `docs/development-status.md`、`docs/development-progress-checklist.md`、`tasks/todo.md` 和下次启动提示词；如果用户再次提醒这个习惯，必须把提醒写入 `tasks/lessons.md`。
- 执行：后续完成任一 `SAL-*` 阶段任务或 Gate 后，不等待用户提醒，先做状态锚点扫描（Phase/Gate/完成度/当前可执行任务/恢复提示词），再提交中文 checkpoint 或状态同步 commit，最后把可复制启动提示词发给用户。

## 2026-07-21: 阶段性交付后状态同步要写清 checkpoint 锚点

- 纠正来源：`SAL-P2-001` checkpoint 已完成后，用户再次要求“更新文档的最新开发状态，标注清楚哪些完成了哪些未完成”，并要求“记住这个习惯，在每个阶段性任务完成后自动去做”。
- 模式：状态文档即使已经列出 Phase/Gate/下一步，如果 checkpoint 仍写成“本文件所在提交”，下次会话仍需要额外判断最近可评审交付和状态同步是否同一个 commit。
- 规则：阶段性任务完成后，状态同步必须明确记录最近可评审交付 commit、当前完成度、当前 READY/DOING/BLOCKED 任务、仍未完成范围和下次启动提示词；用户再次提醒该习惯时必须追加到本文件。
- 执行：以后完成任一 `SAL-*` 后，先提交可评审交付，再根据需要追加状态同步 commit；最终回复必须提供可复制的下一次启动提示词，并说明最近交付 commit 与最新状态同步 commit。

## 2026-07-21: 状态同步提示词必须可直接复用

- 纠正来源：`SAL-P2-002` checkpoint `68e8fea9` 完成后，用户再次要求“标注清楚哪些完成了哪些未完成”并“给我一个提示词，直接发给我”，同时要求把该习惯固化。
- 模式：如果状态文档只描述抽象的“本文件所在提交”，或最终回复没有给出完整可复制 prompt，下次启动仍需要人工拼接当前 Phase、Gate、完成范围、下一步和禁区。
- 规则：每个阶段性任务完成后，必须把最近可评审交付 commit、最新状态同步 commit、完成/未完成范围、当前 READY 任务和严格禁区同时写入 `docs/development-status.md` 的正文与下次启动提示词；最终回复必须直接附上可复制提示词。
- 执行：后续任一 `SAL-*` 或 Gate 收尾时，先更新 `tasks/lessons.md`（若用户再次提醒习惯）、`docs/development-status.md`、`docs/development-progress-checklist.md`、`tasks/todo.md` review，再运行状态锚点扫描和 `git diff --check`，最后提交中文 status-sync 或 checkpoint commit。

## 2026-07-19: “下一阶段开发”不能长期停留在文档收尾

- 纠正来源：用户指出“为什么还不开始写代码，一直在写这些文档？”
- 模式：在 P0 Gate 未通过时，容易把“下一阶段开发”解释成继续补证据/状态文档，而没有尽快进入可运行脚本、测试、Docker profile 或代码修复。
- 规则：完成必要的计划和状态同步后，下一步必须选择一个会产生可运行产物的任务；文档只能作为证据收尾，不应成为主要交付。
- 执行：后续推进 P0 时，优先执行 `SAL-P0-007` Docker baseline 或 `SAL-P0-004` backend gate/offline-tests；若发现脚本、配置、compose、healthcheck 或测试入口缺口，直接最小范围修改代码/脚本。
