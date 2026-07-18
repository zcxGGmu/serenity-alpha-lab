# DSA 供应链基线尝试记录

> 任务：`SAL-P0-011` 建立供应链基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`BLOCKED`

## 1. 执行结论

本次已完成可离线读取的 DSA 供应链初筛：确认 DSA 根许可证为 MIT，完成 Web npm audit 摘要、Node 依赖许可证枚举、Python requirements 动态依赖识别、Dockerfile/Compose 依赖路径复核，以及 Docker CLI/SBOM 插件可用性检查。

`SAL-P0-011` 仍不能标记完成：Python 依赖安装仍受 AlphaSift 动态 Git 克隆阻塞，无法生成已安装 Python SBOM；Docker daemon 未运行，无法构建/检查镜像，也无法生成镜像 SBOM 或镜像漏洞报告。当前记录是供应链基线尝试与阻塞证据，不是完整 SBOM 交付。

## 2. 已执行验证

| 验证 | 结果 |
|---|---|
| `LICENSE` | DSA 根许可证为 MIT |
| `npm audit --json` | 16 个漏洞：1 low、5 moderate、10 high、0 critical |
| Node `node_modules` 许可证枚举 | 446 个包、14 类许可证、0 个 UNKNOWN |
| `requirements.txt` 解析 | 42 条依赖声明；1 条动态 Git 依赖；1 条 `==` pin；39 条范围版本 |
| `.github/requirements-ci.txt` | 通过 `-r ../requirements.txt` 继承运行时依赖，并额外安装 `flake8`、`pytest` |
| `docker --version` | Docker CLI `29.4.1` 可用 |
| `docker sbom --version` | SBOM 插件 `sbom-cli-plugin 0.6.0` 可用 |
| `docker info` | 失败，无法连接 `dockerDesktopLinuxEngine`，daemon 未运行 |

## 3. Web / Node 风险

### 3.1 npm audit

| 严重级别 | 数量 |
|---|---:|
| critical | 0 |
| high | 10 |
| moderate | 5 |
| low | 1 |
| total | 16 |

High 漏洞包：

| 包 | 直接依赖 | 受影响范围 | `npm audit` 修复可用 |
|---|---|---|---|
| `axios` | 是 | `1.0.0 - 1.15.2` | 是 |
| `flatted` | 否 | `<=3.4.1` | 是 |
| `form-data` | 否 | `4.0.0 - 4.0.5` | 是 |
| `minimatch` | 否 | `<=3.1.3 \|\| 9.0.0 - 9.0.6` | 是 |
| `picomatch` | 否 | `4.0.0 - 4.0.3` | 是 |
| `react-router` | 否 | `7.0.0 - 7.15.0` | 是 |
| `react-router-dom` | 是 | `7.0.0-pre.0 - 7.14.1` | 是 |
| `rollup` | 否 | `4.0.0 - 4.58.0` | 是 |
| `undici` | 否 | `7.0.0 - 7.27.2` | 是 |
| `vite` | 是 | `7.0.0 - 7.3.3` | 是 |

P0 基线阶段不运行 `npm audit fix`，避免改写上游 lockfile。后续需在受控补丁或上游同步分支中评估升级影响，并将未豁免 High 纳入发布门禁。

### 3.2 Node 许可证

| 许可证 | 包数量 |
|---|---:|
| MIT | 378 |
| ISC | 26 |
| Apache-2.0 | 19 |
| BSD-2-Clause | 8 |
| BSD-3-Clause | 4 |
| MIT-0 | 2 |
| MPL-2.0 | 2 |
| Remix Icon License 1.0 | 1 |
| Python-2.0 | 1 |
| CC-BY-4.0 | 1 |
| CC0-1.0 | 1 |
| 0BSD | 1 |
| `MIT OR CC0-1.0` | 1 |
| `MIT AND ISC` | 1 |

需 SEC 复核的非主流或内容类许可证包：

| 包 | 版本 | 许可证 |
|---|---|---|
| `@remixicon/react` | `4.9.0` | Remix Icon License 1.0 |
| `argparse` | `2.0.1` | Python-2.0 |
| `caniuse-lite` | `1.0.30001767` | CC-BY-4.0 |
| `lightningcss` | `1.30.2` | MPL-2.0 |
| `lightningcss-win32-x64-msvc` | `1.30.2` | MPL-2.0 |

### 3.3 Registry 可复现性

`apps/dsa-web/package-lock.json` 的 resolved URL 同时指向：

| Registry host | resolved 数量 |
|---|---:|
| `registry.npmmirror.com` | 140 |
| `registry.npmjs.org` | 391 |

这会影响离线缓存、国际网络环境和供应链镜像策略；后续应决定是否保留上游 lockfile 原样、统一 registry，或通过内部缓存代理保证可复现。

## 4. Python 风险

`requirements.txt` 目前不是锁文件，主要风险如下：

- 42 条依赖声明中，39 条为范围版本，只有 `longbridge==0.2.74` 是条件 pin。
- AlphaSift 通过动态 Git URL 安装：`git+https://github.com/ZhuLinsen/alphasift.git@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf#egg=alphasift`。
- `.github/requirements-ci.txt` 直接继承运行时 requirements，因此后端 CI 也受 AlphaSift Git 可达性和范围版本漂移影响。
- AlphaSift 仓库当前无法从 GitHub 443 克隆；其许可证、依赖树和 wheel hash 尚不能由本地证据复核。
- OpenBB 当前未出现在 DSA `requirements.txt` 或 Web package 中；架构方案中的 AGPL 风险仍作为后续可选 Provider/服务接入风险保留。

## 5. Docker / 镜像风险

Dockerfile 采用多阶段构建：

- Web builder：`node:20-slim`，执行 `npm ci` 与 `npm run build`。
- Runtime：`python:3.11-slim-bookworm`。
- apt 依赖：`gcc`、`curl`、`git`、`gosu`、`wkhtmltopdf`、`fontconfig`、`libjpeg62-turbo`、`libxrender1`、`libxext6`。
- 运行阶段执行 `pip install -r requirements.txt` 并校验 `import alphasift.dsa_adapter`。

阻塞：

- Docker daemon 未运行，`docker info` 无法连接 `dockerDesktopLinuxEngine`。
- 不能构建 `dsa-baseline:v3.26.1`。
- 不能生成镜像 digest、镜像 SBOM 或镜像漏洞报告。
- 即使 daemon 恢复，镜像构建仍会受 AlphaSift Git 依赖可达性影响。

## 6. 解除条件

- 提供 AlphaSift 可访问 GitHub、内部镜像或离线 wheel，并记录 hash、许可证与依赖树。
- 生成 Python 已安装依赖 SBOM 或等价锁定清单，覆盖运行时与 CI 依赖。
- 启动 Docker daemon，构建 DSA baseline image，记录镜像 digest、`docker sbom` 输出和镜像漏洞摘要。
- 对 npm audit high、Node 非主流许可证、混合 registry、Python 动态 Git 安装分别指定处理人、截止时间和补偿控制。

## 7. 不做事项

- 不运行 `npm audit fix` 或手动升级 Web lockfile。
- 不跳过 AlphaSift 依赖生成虚假的 Python SBOM。
- 不在 Docker daemon 未运行时伪造镜像 digest 或镜像 SBOM。
- 不将本记录视为 Gate G0 的完整供应链通过证据。
