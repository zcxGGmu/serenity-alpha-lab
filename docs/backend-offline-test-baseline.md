# DSA 后端离线测试基线尝试记录

> 任务：`SAL-P0-004` 建立后端离线测试基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`BLOCKED`

## 1. 执行结论

本次尚未进入 DSA backend-gate 或离线测试执行阶段。阻塞发生在后端/CI 依赖安装阶段：`requirements-ci.txt` 引用上游 `requirements.txt`，其中 AlphaSift 动态 Git 依赖需要从 GitHub 克隆 `ZhuLinsen/alphasift`，当前环境两次重试均无法连接 GitHub 443。

因此 `SAL-P0-004` 不得标记完成；测试数量、耗时、失败清单、Junit/coverage Artifact 仍为空，待解除依赖安装阻塞后补齐。

## 2. 已完成的前置动作

| 验证 | 结果 |
|---|---|
| `uv python install 3.11` | 已准备 uv 管理的 Python `3.11.15` |
| `uv python find 3.11` | `E:\hermes\uv-python\cpython-3.11.15-windows-x86_64-none\python.exe` |
| `scripts/bootstrap-dsa-baseline.ps1 -PythonExecutable <python-3.11> -InstallCiTools -InstallRetries 2` | 创建/复用 `.cache/dsa-p0/venv`，升级 pip 到 `26.1.2`，依赖安装在 AlphaSift Git clone 阶段失败 |
| bootstrap 失败处理 | 已修复 PowerShell 脚本的 native command 退出码检查；依赖失败现在正确返回非零 |

## 3. 阻塞详情

失败命令摘要：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap-dsa-baseline.ps1 `
  -PythonExecutable 'E:\hermes\uv-python\cpython-3.11.15-windows-x86_64-none\python.exe' `
  -InstallCiTools `
  -InstallRetries 2
```

失败点：

```text
git clone --filter=blob:none --quiet https://github.com/ZhuLinsen/alphasift.git ...
fatal: unable to access 'https://github.com/ZhuLinsen/alphasift.git/':
Failed to connect to github.com port 443 after 21069 ms: Couldn't connect to server
```

第二次重试同样失败。该阻塞属于外部网络/供应链可达性问题，不是 DSA 测试失败。

## 4. 解除条件

- 当前环境可访问 `https://github.com/ZhuLinsen/alphasift.git`，或提供内部镜像/离线 wheel。
- `scripts/bootstrap-dsa-baseline.ps1 -PythonExecutable <python-3.11> -InstallCiTools` 能完成依赖安装并返回 0。
- 之后再运行上游 `scripts/ci_gate.sh syntax`、`flake8`、`deterministic`、`offline-tests`，并记录测试数量、耗时、失败分类和 Artifact。

## 5. 不做事项

- 不跳过 AlphaSift 依赖来伪造 backend-gate 通过。
- 不把 `SAL-P0-004` 标记为 `DONE`。
- 不开始依赖 `SAL-P0-004` 的 API、DB、报告金标和上游维护文档任务。
