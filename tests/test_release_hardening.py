from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_exposes_console_script_entrypoint():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[build-system]" in pyproject
    assert 'requires = ["setuptools>=64"]' in pyproject
    assert 'build-backend = "setuptools.build_meta"' in pyproject
    assert "[project.scripts]" in pyproject
    assert 'serenity-alpha-lab = "serenity_alpha_lab.cli:main"' in pyproject
    assert "[tool.setuptools.packages.find]" in pyproject
    assert 'where = ["src"]' in pyproject


def test_setup_py_supports_legacy_editable_install():
    setup_py = (ROOT / "setup.py").read_text(encoding="utf-8")

    assert "from setuptools import find_packages, setup" in setup_py
    assert 'package_dir={"": "src"}' in setup_py
    assert 'packages=find_packages("src")' in setup_py
    assert "serenity-alpha-lab=serenity_alpha_lab.cli:main" in setup_py


def test_release_makefile_exposes_standard_targets():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "test:" in makefile
    assert "e2e:" in makefile
    assert "doctor:" in makefile
    assert "smoke:" in makefile
    assert "run-cpo-pack:" in makefile
    assert "coverage-matrix:" in makefile
    assert "ui:" in makefile
    assert "serve-ui:" in makefile
    assert "verify:" in makefile
    assert "frontend-test:" in makefile
    assert "frontend-build:" in makefile
    assert "frontend-smoke:" in makefile
    assert "release-check:" in makefile
    assert "clean-pack:" in makefile
    assert ".PHONY: test e2e doctor smoke run-cpo-pack coverage-matrix ui serve-ui verify clean-pack" in makefile
    assert "verify: test doctor run-cpo-pack coverage-matrix" in makefile
    assert "python3 -m pytest tests -q" in makefile
    assert "python3 -m pytest tests/test_ui_http_e2e.py -q" in makefile
    assert "serenity_alpha_lab.cli doctor" in makefile
    assert "serenity_alpha_lab.cli run-cpo-pack" in makefile
    assert "serenity_alpha_lab.cli build-coverage-matrix" in makefile
    assert "serenity_alpha_lab.cli build-ui" in makefile
    assert "serenity_alpha_lab.cli serve-ui" in makefile
    assert "SERENITY_ALPHA_LAB ?=" in makefile
    assert 'shutil.which("serenity-alpha-lab")' in makefile
    assert 'sysconfig.get_path("scripts")' in makefile
    assert "$(SERENITY_ALPHA_LAB) doctor" in makefile
    assert "$(SERENITY_ALPHA_LAB) run-cpo-pack" in makefile
    assert "scripts/verify_offline_release.py" in makefile


def test_operations_doc_describes_stable_product_run():
    operations = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")

    assert "run-cpo-pack" in operations
    assert "python3 -m pytest tests -q" in operations
    assert "output/packs/cpo-guarded" in operations
    assert "output/reports/cpo-readiness-guarded.md" in operations
    assert "build-ui" in operations
    assert "build-coverage-matrix" in operations
    assert "output/reports/universe-coverage-matrix.md" in operations
    assert "evidence-acquisition-queue.md" in operations
    assert "serve-ui" in operations
    assert "output/ui/index.html" in operations


def test_changelog_documents_productized_release():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "# Changelog" in changelog
    assert "## 0.1.0" in changelog
    assert "run-cpo-pack" in changelog
    assert "doctor" in changelog
    assert "make verify" in changelog


def test_release_checklist_covers_artifact_verification():
    checklist = (ROOT / "docs" / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    assert "# Release Checklist" in checklist
    assert "make verify" in checklist
    assert "build-coverage-matrix" in checklist
    assert "output/reports/universe-coverage-matrix.md" in checklist
    assert "Open Acquisition Queue" in checklist
    assert "evidence-acquisition-queue.md" in checklist
    assert "output/packs/cpo-guarded/index.md" in checklist
    assert "output/packs/cpo-guarded/sources.md" in checklist
    assert "research only" in checklist


def test_ci_workflow_runs_release_gate():
    workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")

    assert "name: Verify" in workflow
    assert "pull_request:" in workflow
    assert "branches:" in workflow
    assert "tags:" in workflow
    assert 'python-version: "3.11"' in workflow
    assert 'node-version: "20"' in workflow
    assert "npm ci" in workflow
    assert "playwright install --with-deps chromium" in workflow
    assert 'SERENITY_RESEARCH_AGENTS_ENABLED: "false"' in workflow
    assert 'SERENITY_RESEARCH_BOT_ENABLED: "false"' in workflow
    assert "scripts/verify_offline_release.py" in workflow


def test_install_doc_describes_installed_smoke_path():
    install_doc = (ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert "# Install" in install_doc
    assert "python3 -m pip install -e ." in install_doc
    assert "serenity-alpha-lab doctor" in install_doc
    assert "serenity-alpha-lab run-cpo-pack" in install_doc
    assert "make smoke" in install_doc
