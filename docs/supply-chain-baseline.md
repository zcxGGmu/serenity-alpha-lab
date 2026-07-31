# DSA 供应链基线记录

> 任务：`SAL-P0-011` 建立供应链基线<br>
> 执行日期：2026-07-19<br>
> 上游基线：`upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> 当前状态：`DONE`

## 1. 执行结论

`SAL-P0-011` 已完成供应链基线。新增 `scripts/run-dsa-supply-chain-baseline.sh`，可复跑生成 Python 已安装依赖 SBOM、Python license inventory、Python vulnerability audit、Web npm audit、Web lockfile license inventory、Docker image package inventory、Syft image SBOM 和 Grype image vulnerability report。

本任务是 P0 基线与风险定责，不在本阶段直接执行 `npm audit fix`、升级上游 lockfile 或重构 Dockerfile。当前 baseline 暴露多项 High/Critical 风险，均已登记 owner、计划与截止时间；这些风险在后续安全门禁前必须解除或正式豁免。

## 2. 环境与工具

| 项目 | 值 |
|---|---|
| DSA baseline | `upstream/dsa-v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| DSA worktree | `.worktrees/dsa-v3.26.1` |
| Python target env | `.cache/dsa-p0/venv`, Python `3.11.15`, pip `26.1.2` |
| Tool env | `.cache/dsa-p0/supply-chain-tools-venv`, `pip-audit 2.9.0` |
| Docker image | `serenity-dsa-p0:sal-p0-007` / `sha256:7de0eca96fa8622e8b4b7292890f413e1a8fc52417f02c9c9a2829a364918076` |
| Docker | CLI `29.4.2`, server `29.4.0` |
| SBOM scanner | `syft 1.48.0` |
| Image vulnerability scanner | `grype 0.116.0` |
| Trivy | `0.72.0`, installed but DB download blocked by `mirror.gcr.io` timeout; Grype is the authoritative image scan for this baseline |
| Artifact dir | `.cache/dsa-p0/supply-chain-artifacts/` |

## 3. 结果摘要

| Area | Count / Status |
|---|---:|
| Python installed packages | 146 |
| Python audit packages checked | 145 |
| Python audit skipped packages | 1 |
| Python audit vulnerabilities | 1 |
| Web lockfile packages in license inventory | 529 |
| Web npm audit vulnerabilities | 16 |
| Web npm audit high | 10 |
| Web npm audit critical | 0 |
| Image Debian packages | 262 |
| Image Python packages | 142 |
| Image Syft CycloneDX components | 7865 |
| Image Grype matches | 933 |
| Image Grype critical | 39 |
| Image Grype high | 84 |
| Image Grype medium | 155 |

## 4. Python 供应链

### 4.1 SBOM 与 license

Python installed SBOM 由目标 venv 的 `pip inspect --local` 生成，不向目标 venv 安装额外 SBOM 工具，避免污染被审计环境。

| Artifact | 说明 |
|---|---|
| `.cache/dsa-p0/supply-chain-artifacts/python-pip-inspect.json` | pip inspect 原始输出 |
| `.cache/dsa-p0/supply-chain-artifacts/python-sbom-cyclonedx.json` | CycloneDX JSON，146 个 Python components |
| `.cache/dsa-p0/supply-chain-artifacts/python-license-inventory.csv` | Python 包 license inventory |
| `.cache/dsa-p0/supply-chain-artifacts/python-license-summary.md` | Python license 摘要，146 包中 53 个 UNKNOWN |
| `.cache/dsa-p0/supply-chain-artifacts/python-requirements-summary.md` | requirements 风险摘要 |

`requirements.txt` 仍不是锁文件：42 条 runtime dependency 声明中，1 条 AlphaSift 动态 Git 依赖、1 条 exact pin、40 条范围或未 pin 声明。AlphaSift Git 依赖为：`git+https://github.com/ZhuLinsen/alphasift.git@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf#egg=alphasift`。

### 4.2 Python vulnerabilities

`pip-audit` 在独立工具 venv 中运行，使用 `--path .cache/dsa-p0/venv/lib/python3.11/site-packages` 审计目标环境。

| 包 | 版本 | ID | Fix |
|---|---:|---|---|
| `setuptools` | `79.0.1` | `PYSEC-2026-3447` | `83.0.0` |
| `alphasift` | `0.2.0` | skipped | 不在 PyPI，无法由 `pip-audit` 审计 |

处理计划：BE/SEC 在 `SAL-P1-003` 引入正式 Python lock / build extras 时升级或隔离 build tooling；AlphaSift 在 `SAL-P0-012` 上游维护文档中明确 wheel hash、许可证和替代审计路径。

## 5. Web / Node 供应链

### 5.1 npm audit

| 严重级别 | 数量 |
|---|---:|
| critical | 0 |
| high | 10 |
| moderate | 5 |
| low | 1 |
| total | 16 |

High 漏洞包仍为：`axios`、`flatted`、`form-data`、`minimatch`、`picomatch`、`react-router`、`react-router-dom`、`rollup`、`undici`、`vite`。P0 不运行 `npm audit fix`，避免改写上游 lockfile；FE/SEC 在解除 `SAL-P0-005` 与后续 `SAL-P6-005` 发布门禁前处理或正式豁免。

### 5.2 Node license inventory

当前 web license inventory 从 `apps/dsa-web/package-lock.json` 生成，共 529 个 lockfile packages，0 个 UNKNOWN license。

| License | Count |
|---|---:|
| MIT | 447 |
| ISC | 28 |
| Apache-2.0 | 20 |
| MPL-2.0 | 12 |
| BSD-2-Clause | 8 |
| BSD-3-Clause | 4 |
| 其他单项 license | 10 |

需 SEC 复核的非主流或内容类许可证仍包括 Remix Icon License 1.0、Python-2.0、CC-BY-4.0、BlueOak-1.0.0、MPL-2.0 等。

## 6. Docker / 镜像供应链

### 6.1 SBOM

| Artifact | 说明 |
|---|---|
| `.cache/dsa-p0/supply-chain-artifacts/image-syft-cyclonedx.json` | Syft CycloneDX image SBOM，7865 components |
| `.cache/dsa-p0/supply-chain-artifacts/image-sbom-lite-cyclonedx.json` | 由 dpkg + pip inventory 生成的轻量 CycloneDX，404 components |
| `.cache/dsa-p0/supply-chain-artifacts/image-dpkg.tsv` | Debian package inventory，262 packages |
| `.cache/dsa-p0/supply-chain-artifacts/image-python-pip-list.json` | Image Python package inventory，142 packages |
| `.cache/dsa-p0/supply-chain-artifacts/image-inspect.json` | Docker image inspect |

### 6.2 Image vulnerabilities

Grype 扫描 `serenity-dsa-p0:sal-p0-007`，输出 933 matches：

| Severity | Count |
|---|---:|
| Critical | 39 |
| High | 84 |
| Medium | 155 |
| Low | 13 |
| Negligible | 626 |
| Unknown | 16 |

代表性高风险项包括 `curl 7.88.1-10+deb12u15` 的 Critical、Debian runtime 包漏洞和 Go stdlib 相关 finding。BE/SEC 处理计划：在 `SAL-P1-003`/`SAL-P6-005` 前重建 runtime base、执行 `apt-get upgrade` 或切换已修复 base image，并建立镜像漏洞门禁；未能修复的 Critical/High 必须有到期豁免。

Trivy 已安装但本机无法从 `mirror.gcr.io/aquasec/trivy-db:2` 下载 DB，失败原因记录在 `.cache/dsa-p0/supply-chain-artifacts/image-trivy.stderr`。本次以 Grype 作为镜像漏洞基线来源。

## 7. Critical / High 处理计划

| 风险 | 当前证据 | Owner | 截止 |
|---|---|---|---|
| Web npm High 10 | `node-web-npm-audit.json` | FE/SEC | `SAL-P0-005` 契约解除后制定升级补丁；最迟 `SAL-P6-005` 发布门禁前关闭或豁免 |
| Python `setuptools` vulnerability 1 | `python-pip-audit.json` | BE/SEC | `SAL-P1-003` Python lock/build extras 引入时升级到 `83.0.0+` 或隔离 build tool |
| AlphaSift 无法由 PyPI 审计 | `python-pip-audit.json` skip reason；wheel hash 已在 Docker baseline 记录 | BE/SEC | `SAL-P0-012` 上游维护文档记录 wheel hash、许可证和替代审计方式 |
| Image Critical 39 / High 84 | `image-grype-vulnerabilities.json` | BE/SEC | `SAL-P6-005` 安全门禁前基于修复 base image 重建，或逐项豁免 |
| Python license UNKNOWN 53 | `python-license-summary.md` | SEC | `SAL-P1-003` lockfile 生成后复核并补全高风险包许可证 |
| Node 非主流许可证 | `node-web-license-summary.md` | SEC/FE | `SAL-P6-005` 发布审查前确认可分发边界 |
| OpenBB / AGPL | 当前 DSA runtime 与 Web lockfile 未发现 OpenBB；作为后续可选 Provider 风险保留 | SEC/BE | 引入 OpenBB 前必须 ADR 评审 license 与部署边界 |
| 数据服务条款 | DSA 使用 AkShare、Tushare、Yahoo/Longbridge 等多 Provider；本次只做依赖基线，不代表数据条款可商用 | SEC/RE | `SAL-P6-005` 发布审查前完成 Provider ToS 登记与使用边界 |

## 8. 不做事项与限制

- 不运行 `npm audit fix`、`npm update` 或重写 DSA Web lockfile。
- 不把 scanner DB、`.cache`、`.worktrees`、镜像导出文件或生成 SBOM artifact 提交到本项目。
- 不把当前存在 Critical/High 漏洞解释为发布可接受；本任务只完成基线、定责和处理计划。
- 不把 Gate G0 标记为完成；`SAL-P0-005`、`SAL-P0-008` 至 `SAL-P0-010`、`SAL-P0-012` 仍未完成。
