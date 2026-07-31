# DSA 基线运行环境记录

> 任务：`SAL-P0-003` 固化基线运行环境<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 证据来源：`requirements.txt`、`.github/requirements-ci.txt`、`apps/dsa-web/package*.json`、`apps/dsa-desktop/package*.json`、`docker/Dockerfile`、`docker/docker-compose.yml`、`.github/workflows/ci.yml`

## 1. 执行结论

`SAL-P0-003` 固定 DSA 基线的最小可复现环境为：

- 后端/CI：Python `3.11`，本地虚拟环境安装 `requirements.txt` 和 `.github/requirements-ci.txt`。
- 桌面打包：Python `3.12`，Node `20`，Electron `31.4.0`，以 `apps/dsa-desktop/package-lock.json` 为依赖快照。
- Web：Node `>=20.19.0 <27`，npm `>=10`，以 `apps/dsa-web/package-lock.json` 为依赖快照。
- Docker：`node:20-slim` 构建 Web，`python:3.11-slim-bookworm` 运行后端，并安装 `gcc/curl/git/gosu/wkhtmltopdf/fontconfig/libjpeg62-turbo/libxrender1/libxext6`。
- 本项目提供 `scripts/bootstrap-dsa-baseline.ps1` 和 `scripts/bootstrap-dsa-baseline.sh`，从本地不可变 tag 创建隔离 worktree，并使用本地 `.cache/dsa-p0` 缓存安装依赖；不把 DSA 源码合入当前工作树。

## 2. 环境矩阵

| Profile | OS/Runtime | 版本约束 | 系统依赖 | 用途 |
|---|---|---|---|---|
| Windows local | Windows 11 / Server 2022；PowerShell 5.1+；Git 2.40+ | Python 3.11；Node `>=20.19.0 <27`；npm `>=10` | Git、可选 wkhtmltopdf、可选 Docker Desktop | 本地后端依赖、Web 构建、Smoke 预检 |
| Linux local/CI | Ubuntu latest 或 Ubuntu 22.04/24.04；Git 2.40+ | Python 3.11；Node 20；npm 10+ | `gcc`、`curl`、`git`、`wkhtmltopdf`、`fontconfig`、`libjpeg`、`libxrender`、`libxext` | 后端门禁、Web 门禁、离线测试 |
| Docker baseline | Docker Engine/BuildKit；Compose v2 | `node:20-slim` + `python:3.11-slim-bookworm` | Dockerfile 内固定 apt 依赖；内存建议 1G+ | analyzer/server 镜像基线 |
| Desktop release | Windows/macOS release runner | Python 3.12；Node 20；npm 10+ | Electron Builder 所需平台工具 | 桌面端打包与升级演练 |

## 3. 依赖来源

### 3.1 Python

- 运行时依赖来自上游 `requirements.txt`，当前未提供锁文件。
- CI 额外依赖来自 `.github/requirements-ci.txt`，内容为 `-r ../requirements.txt`、`flake8`、`pytest`。
- `requirements.txt` 含动态 Git 依赖 `git+https://github.com/ZhuLinsen/alphasift.git@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf#egg=alphasift`；供应链审计在 `SAL-P0-011` 继续处理。
- `longbridge` 对 Linux/Python 版本有条件依赖：Linux 且 Python `<3.12` 使用 `longbridge==0.2.74`，其他环境使用 `longbridge>=4.0.5,<5`。

### 3.2 Node

- Web 依赖由 `apps/dsa-web/package-lock.json` 冻结，`package.json` engines 要求 Node `>=20.19.0 <27` 与 npm `>=10`。
- Desktop 依赖由 `apps/dsa-desktop/package-lock.json` 冻结，主要运行时依赖为 `electron-updater`，构建依赖为 `electron` 和 `electron-builder`。
- 上游 CI `ci.yml` 只在 `apps/dsa-web/**` 变化时运行 Web gate；P0 后续应在本项目基线 CI 中强制跑 Web 基线。

### 3.3 Docker

- Dockerfile 使用 BuildKit cache mount：`/root/.npm` 和 `/root/.cache/pip`。
- 运行镜像以非 root 用户 `dsa` 执行，持久化 `/app/data`、`/app/logs`、`/app/reports`。
- Compose 提供 `analyzer` 和 `server` 两个服务，`server` 命令为 `python main.py --serve-only --host 0.0.0.0 --port ${API_PORT:-8000}`。

## 4. Bootstrap 命令

### 4.1 Windows

```powershell
.\scripts\bootstrap-dsa-baseline.ps1 -ValidateOnly
.\scripts\bootstrap-dsa-baseline.ps1
.\scripts\bootstrap-dsa-baseline.ps1 -InstallPython -InstallCiTools -InstallWeb
```

可选桌面依赖：

```powershell
.\scripts\bootstrap-dsa-baseline.ps1 -InstallDesktop
```

### 4.2 Linux

```bash
bash scripts/bootstrap-dsa-baseline.sh --validate-only
bash scripts/bootstrap-dsa-baseline.sh
bash scripts/bootstrap-dsa-baseline.sh --install-python --install-ci-tools --install-web
```

可选桌面依赖：

```bash
bash scripts/bootstrap-dsa-baseline.sh --install-desktop
```

### 4.3 Docker

在物化出的 DSA worktree 中执行：

```bash
cd .worktrees/dsa-v3.26.1
DOCKER_BUILDKIT=1 docker build -f docker/Dockerfile -t dsa-baseline:v3.26.1 .
docker compose -f docker/docker-compose.yml config
docker compose -f docker/docker-compose.yml up -d server
```

## 5. 缓存与隔离策略

- DSA 源码物化到 `.worktrees/dsa-v3.26.1`，保持与本项目工作树隔离。
- Python venv 与 pip cache 位于 `.cache/dsa-p0/venv` 和 `.cache/dsa-p0/pip`，不写入全局 site-packages。
- Web 与 Desktop npm cache 位于 `.cache/dsa-p0/npm-web` 与 `.cache/dsa-p0/npm-desktop`。
- Docker 构建依赖 Dockerfile 的 BuildKit cache mount；不得依赖宿主机已安装 Python 包、Node 包或系统库。
- `.env` 由 `.env.example` 复制生成，但不提交；真实密钥必须由本地或 CI secret 注入。

## 6. 验收记录

| 验证 | 结果 |
|---|---|
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `git show upstream/dsa-v3.26.1:requirements.txt` | 已确认 Python 运行时依赖、AlphaSift Git pin、Longbridge 条件依赖 |
| `git show upstream/dsa-v3.26.1:.github/requirements-ci.txt` | 已确认 CI 依赖入口 |
| `git show upstream/dsa-v3.26.1:apps/dsa-web/package.json` | 已确认 Node/npm engine 与 Web scripts |
| `git show upstream/dsa-v3.26.1:docker/Dockerfile` | 已确认 Python/Node 镜像、apt 依赖与 BuildKit cache |
| `git show upstream/dsa-v3.26.1:.github/workflows/ci.yml` | 已确认上游 CI 使用 Python 3.11、Node 20、Docker build |
| `python --version` / `py -0p` | 当前 Windows PATH 为 Python 3.10.11，`py` 未发现 Python 3.11；`SAL-P0-004` 前需安装 Python 3.11 或改用容器/CI |
| `node --version` / `npm --version` | 当前 Windows PATH 为 Node v24.12.0、npm 11.6.2，满足 Web engines `>=20.19.0 <27` 和 npm `>=10` |
| `docker --version` / `docker image inspect python:3.11-slim-bookworm` | Docker CLI 为 29.4.1，但 Docker Desktop Linux daemon 当前未运行；`SAL-P0-007` 前需启动或配置 Docker daemon |
| `powershell -NoProfile -Command "$null = [scriptblock]::Create((Get-Content -Raw scripts/bootstrap-dsa-baseline.ps1))"` | PowerShell 脚本解析通过 |
| `C:\Program Files\Git\bin\bash.exe -n scripts/bootstrap-dsa-baseline.sh` | Bash 脚本解析通过 |
| `scripts/bootstrap-dsa-baseline.ps1 -ValidateOnly` | 基线 tag 校验通过 |
| `scripts/bootstrap-dsa-baseline.ps1` | 已物化 `.worktrees/dsa-v3.26.1`，HEAD 为锁定 SHA，并从 `.env.example` 生成本地 `.env` |
| `C:\Program Files\Git\bin\bash.exe scripts/bootstrap-dsa-baseline.sh --validate-only` | Git Bash 下基线 tag 与 worktree HEAD 校验通过；系统 WSL bash 当前不可用，不作为本任务 Linux 证据 |

## 7. 已知风险

- 上游 Python 依赖未锁定，`requirements.txt` 仍使用范围版本和动态 Git 依赖；`SAL-P0-011` 必须生成 SBOM、许可证和漏洞报告，`SAL-P1-003` 必须引入锁文件。
- Web lockfile 中 resolved registry 指向 `npmmirror.com`；离线/国际网络环境需要缓存策略或 registry 镜像策略复核。
- 当前 Windows 主机未安装 Python 3.11，Docker daemon 未启动；后端测试和 Docker 运行基线前需要先完成环境补齐或切换到 CI/容器环境。
- 本任务只固化安装入口和环境矩阵，不替代 `SAL-P0-004` 后端测试、`SAL-P0-005` Web 构建、`SAL-P0-007` Docker 运行基线。
