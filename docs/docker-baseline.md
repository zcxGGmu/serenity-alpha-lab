# DSA Docker 基线记录

> 任务：`SAL-P0-007` 建立 Docker 基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`DONE`

## 1. 执行结论

本次已完成锁定 DSA 基线的 Docker build、server profile health smoke 和 analyzer import smoke。`SAL-P0-007` 可标记为 `DONE`。

直接使用上游 Dockerfile 构建时，容器内 `pip install -r requirements.txt` 会从 GitHub 克隆 AlphaSift，首轮失败于 `GnuTLS recv error (-110)`。为避免继续依赖动态 Git clone，本项目新增 `scripts/run-dsa-docker-baseline.sh`：脚本只生成 `.cache/dsa-p0/docker-build-context` 临时上下文，把已缓存的 AlphaSift wheel 显式注入 Docker build，不修改 DSA 上游 worktree。

## 2. 环境

| 项目 | 结果 |
|---|---|
| Docker context | `orbstack` |
| Docker server | `29.4.0` |
| Docker OS / Arch | `OrbStack` / `aarch64` |
| Docker Compose | `5.1.3` |
| Image tag | `serenity-dsa-p0:sal-p0-007` |
| Image digest | `serenity-dsa-p0@sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076` |
| AlphaSift wheel | `alphasift-0.2.0-py3-none-any.whl` |
| AlphaSift wheel SHA256 | `c9890b127ad062253200bf4b7fe5816bff42a2e95e69ee04b985542cd9e39cf2` |

## 3. 命令与结果

| 命令 | 结果 |
|---|---|
| `docker build --progress=plain -t serenity-dsa-p0:sal-p0-007 -f docker/Dockerfile .` | 失败：AlphaSift Git clone 在容器内 TLS 中断 |
| `bash -n scripts/run-dsa-docker-baseline.sh` | 通过 |
| `scripts/run-dsa-docker-baseline.sh` | 通过：镜像构建、server health、analyzer import smoke 均完成 |

Server profile smoke：

```json
{"status":"ok","timestamp":"2026-07-19T11:41:35.701758"}
```

Server container 状态：

```text
dsa-p0-server	Up 16 seconds (healthy)	0.0.0.0:18000->8000/tcp, [::]:18000->8000/tcp
```

Analyzer import smoke：

```text
ok-analyzer
```

## 4. 产物

脚本将可复查产物写入 `.cache/dsa-p0/docker-baseline-artifacts/`，包括：

- `docker-build.log`
- `image-inspect.json`
- `image-summary.txt`
- `server-health.json`
- `server-ps.txt`
- `server.log`
- `analyzer-smoke.log`
- `alphasift-wheel.sha256`

`.cache/` 不提交，提交物只包含可复跑脚本和本证据记录。

## 5. 限制与后续

- 本任务证明 Docker build、server health 和 analyzer import smoke 可运行；不证明真实 Provider、真实 LLM、真实计划任务或真实分析全流程。
- 本任务不生成 Python SBOM、镜像 SBOM 或漏洞报告；这些仍属于 `SAL-P0-011`。
- Web npm audit high 风险仍未处理；P0 不运行 `npm audit fix` 改写上游 lockfile。
- Compose 配置解析时提示 `version` 字段 obsolete；本次未改上游 compose 文件，只记录为后续兼容性观察项。
