# AlphaSift 离线 Wheel Intake 记录

> 任务：`SAL-P3-002` 构建离线 AlphaSift Wheel<br>
> 日期：2026-07-23<br>
> 上游基线：DSA `v3.26.1 @ e8a9ca7742e8cb2498c8f491dd76d239b3064e1a`<br>
> Gate 入口：G2 已通过；G3 未通过<br>
> 结论：`APPROVED FOR INTERNAL WHEELHOUSE`

## 1. Intake 结论

`SAL-P3-002` 已把 AlphaSift 从动态 Git 安装风险推进到可审计的内部 Wheel intake。仓库不提交 Wheel 二进制，只提交可复跑脚本和证据文件；内部制品系统应按本记录中的 URI 和 SHA-256 镜像该 Wheel。

```yaml
source_repository: https://github.com/ZhuLinsen/alphasift
locked_source_commit: 9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf
source_archive_url: https://codeload.github.com/ZhuLinsen/alphasift/tar.gz/9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf
source_archive_sha256: 4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a
source_archive_size_bytes: 300697
package_name: alphasift
package_version: 0.2.0
wheel_filename: alphasift-0.2.0-py3-none-any.whl
wheel_sha256: b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2
source_date_epoch: 1783081838
internal_artifact_uri: internal://serenity-alpha-lab/python-wheels/alphasift/9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf/alphasift-0.2.0-py3-none-any.whl#sha256=b71fe6f4b11c9655b2190f91217fee66361f9852ae344c53fe501455a4823ed2
license_spdx: Apache-2.0
```

## 2. 可复跑脚本

新增脚本：

```text
scripts/build-alphasift-wheel-intake.sh
```

脚本执行步骤：

1. 从 codeload 下载或读取 `--source-archive` 指定的锁定源码 archive。
2. 校验 source archive SHA-256 必须等于 `4ab7a4124d9b95a1fdad6a1f9a3f0fc12913e903ed0d532d4b2848a9bb77de7a`。
3. 使用 `SOURCE_DATE_EPOCH=1783081838` 固定 Wheel zip 时间戳，执行 `uv build --wheel --python 3.11 --out-dir .cache/alphasift-wheel-intake/wheelhouse --clear <source-archive>`。
4. 计算 Wheel SHA-256，生成 manifest、SBOM、许可证清单和 checksum 文件。
5. 运行离线安装形状检查：

```bash
uv pip install --no-index --find-links .cache/alphasift-wheel-intake/wheelhouse --no-deps --target .cache/alphasift-wheel-intake/offline-install-check alphasift==0.2.0
```

本机验证时首次 `github.com` Git endpoint 超时，但 `codeload.github.com` archive 下载成功；后续重跑可使用 `--source-archive .cache/alphasift-wheel-intake/source/alphasift-9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf.tar.gz` 避免外部网络依赖。

## 3. 证据文件

| 文件 | 说明 |
|---|---|
| [intake-manifest.json](./baselines/alphasift-wheel-intake/intake-manifest.json) | 锁定 source、build、wheel、internal artifact、offline install 和禁止范围 |
| [sbom-cyclonedx.json](./baselines/alphasift-wheel-intake/sbom-cyclonedx.json) | CycloneDX 1.5 SBOM，主组件为 `alphasift@0.2.0`，并登记声明运行时依赖 |
| [license-inventory.csv](./baselines/alphasift-wheel-intake/license-inventory.csv) | AlphaSift Wheel 与声明运行时依赖的当前 license metadata |
| [license-summary.md](./baselines/alphasift-wheel-intake/license-summary.md) | 许可证摘要，`unknown_license_count=0` |
| [alphasift-wheel.sha256](./baselines/alphasift-wheel-intake/alphasift-wheel.sha256) | 内部制品 URI 对应的 Wheel SHA-256 |

AlphaSift Wheel 内含两份 Apache-2.0 LICENSE 路径：

- `alphasift-0.2.0.data/data/LICENSE`
- `alphasift-0.2.0.dist-info/licenses/LICENSE`

直接运行时依赖未 vendored 进 AlphaSift Wheel；许可证 inventory 只记录当前 root uv 环境 metadata，生产解析仍由 root `uv.lock` 或后续内部 wheelhouse mirror 控制。

## 4. 安装面处理

- 根 `pyproject.toml` 未加入 AlphaSift。
- `uv.lock` 未因本任务加入 AlphaSift。
- 生产/桌面 `requirements.txt` 未加入 AlphaSift，也仍不包含 `git+https`。
- 生产安装策略为从内部 wheelhouse 使用 `uv pip install --no-index --find-links <internal-wheelhouse> --no-deps alphasift==0.2.0` 安装 AlphaSift Wheel；运行时依赖继续由既有 root lock 或后续制品镜像统一提供。

## 5. 明确未做事项

- 未实现 ScreeningProvider 或 AlphaSift Adapter；该范围属于 `SAL-P3-003`。
- 未实现 CandidateBatch、FactorDefinition、Factor Engine、Screen Lab 或 Quant Screening API。
- 未启动 Quant Core。
- 未启动正式回测。
- 未启动 Evidence Agent。
- 未调用真实 Provider。
- 未调用真实 LLM。
- 未迁移 DSA runtime source，未移动 `upstream/dsa-v3.26.1` tag。
- 未提交 `.cache`、source archive 或 Wheel 二进制。

## 6. 本地验证

| 验证 | 结果 |
|---|---|
| `uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_wheel_intake.py -q` | Red：`4 failed`，缺少 intake 脚本和证据；Green：`4 passed` |
| `uv run --extra core --extra dev python -m pytest tests/architecture/test_alphasift_wheel_intake.py tests/architecture/test_alphasift_source_review.py tests/architecture/test_dependency_locking.py -q` | PASS：`10 passed` |
| `uv run --extra core --extra dev python -m pytest -q` | PASS：`242 passed, 3 skipped` |
| `uv run --extra core --extra dev python -m compileall src tests` | PASS |
| `scripts/verify-python-dependency-lock.sh` | PASS：`Resolved 298 packages` |
| `git diff --check` | PASS |
| `git rev-parse upstream/dsa-v3.26.1` | `e8a9ca7742e8cb2498c8f491dd76d239b3064e1a` |
| `scripts/build-alphasift-wheel-intake.sh --source-archive .cache/alphasift-wheel-intake/source/alphasift-9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf.tar.gz` | PASS：source SHA-256、reproducible wheel build、offline no-deps install、manifest/SBOM/license evidence |
| `uv pip install --no-index --find-links .cache/alphasift-wheel-intake/wheelhouse --no-deps --target .cache/alphasift-wheel-intake/offline-install-check alphasift==0.2.0` | PASS |

最终测试结果同步记录在 `AEV-051`。
