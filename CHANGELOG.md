# Changelog

## 0.1.0

Initial productized local release of Serenity Alpha Lab.

- Added the default CPO memo-pack pipeline via `run-cpo-pack`.
- Added `doctor` as a read-only health check for required local inputs.
- Added `make verify` as the release gate for tests, health checks, and product output generation.
- Added guarded primary-source provenance with source excerpts in generated memo packs.
- Added memo evidence partitioning so focus-ticker primary evidence is separated from sector context.
- Added a skipped-memo quality gate so product runs fail when requested candidates are not generated unless `--allow-skipped` is explicit.
- Added release operations docs and checklist for stable handoff.
