SERENITY_ALPHA_LAB ?= $(shell python3 -c 'import shutil, sysconfig; print(shutil.which("serenity-alpha-lab") or sysconfig.get_path("scripts") + "/serenity-alpha-lab")')

.PHONY: test e2e doctor smoke run-cpo-pack coverage-matrix ui serve-ui verify clean-pack frontend-test frontend-build frontend-smoke release-check

test:
	python3 -m pytest tests -q

e2e:
	python3 -m pytest tests/test_ui_http_e2e.py -q

doctor:
	PYTHONPATH=src python3 -m serenity_alpha_lab.cli doctor

smoke:
	$(SERENITY_ALPHA_LAB) doctor
	$(SERENITY_ALPHA_LAB) run-cpo-pack

run-cpo-pack:
	PYTHONPATH=src python3 -m serenity_alpha_lab.cli run-cpo-pack

coverage-matrix:
	PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-coverage-matrix \
		--data data/enriched/github_plus_primary.jsonl data/enriched/manual_intake_guarded.jsonl \
		--stock-universe config/stock_universe.json \
		--query "存储芯片" \
		--out output/reports/universe-coverage-matrix.md

ui:
	PYTHONPATH=src python3 -m serenity_alpha_lab.cli build-ui

serve-ui:
	PYTHONPATH=src python3 -m serenity_alpha_lab.cli serve-ui

verify: test doctor run-cpo-pack coverage-matrix

frontend-test:
	cd apps/serenity-web && npm test -- --run

frontend-build:
	cd apps/serenity-web && npm run build

frontend-smoke:
	cd apps/serenity-web && npm run test:smoke -- --reporter=line

release-check:
	PYTHONPATH=src python3 scripts/verify_offline_release.py

clean-pack:
	rm -rf output/packs/cpo-guarded
	rm -f output/reports/cpo-readiness-guarded.md
