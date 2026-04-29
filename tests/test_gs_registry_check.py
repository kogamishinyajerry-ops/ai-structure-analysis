"""Tests for scripts/gs_registry_check.py (ENG-17 / HF3)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_registry():
    import gs_registry_check  # type: ignore[import-not-found]

    return gs_registry_check


@pytest.fixture(scope="module")
def registry():
    return _load_registry()


def _write_expected(sample_dir: Path, payload: dict) -> None:
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "expected_results.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def test_current_registry_passes_without_signed_claims(registry):
    report = registry.build_report(_REPO_ROOT / "golden_samples")
    assert report.ok is True
    assert report.violations == ()
    assert report.signed_count == 0


def test_gs100_radioss_smoke_scope_is_not_signed(registry):
    record = registry.classify_sample(_REPO_ROOT / "golden_samples" / "GS-100-radioss-smoke")
    assert record.sample_id == "GS-100-radioss-smoke"
    assert record.scope == registry.SCOPE_SMOKE
    assert record.signed is False
    assert "README.md" in record.evidence_files


def test_gs101_demo_unsigned_scope_is_not_signed(registry):
    record = registry.classify_sample(_REPO_ROOT / "golden_samples" / "GS-101-demo-unsigned")
    assert record.sample_id == "GS-101-demo-unsigned"
    assert record.scope == registry.SCOPE_DEMO_UNSIGNED
    assert record.signed is False
    assert "README.md" in record.evidence_files


@pytest.mark.parametrize("sample_id", ["GS-001", "GS-002", "GS-003"])
def test_legacy_samples_are_insufficient_evidence(registry, sample_id):
    record = registry.classify_sample(_REPO_ROOT / "golden_samples" / sample_id)
    assert record.scope == registry.SCOPE_INSUFFICIENT_EVIDENCE
    assert record.signed is False
    assert "expected_results.json" in record.evidence_files


def test_insufficient_evidence_requires_expected_results_status(registry, tmp_path):
    sample = tmp_path / "golden_samples" / "GS-900"
    _write_expected(
        sample,
        {
            "case_id": "GS-900",
            "status": "insufficient_evidence",
            "failure_pattern_ref": "FP-900",
            "status_reason": "synthetic mismatch",
        },
    )

    record = registry.classify_sample(sample)

    assert record.scope == registry.SCOPE_INSUFFICIENT_EVIDENCE
    assert record.signed is False
    assert "FP-900" in record.reason


def test_unknown_sample_fails_closed(registry, tmp_path):
    sample = tmp_path / "golden_samples" / "GS-999"
    sample.mkdir(parents=True)
    (sample / "README.md").write_text("# Unclassified sample\n", encoding="utf-8")

    report = registry.build_report(tmp_path / "golden_samples")

    assert report.ok is False
    assert len(report.violations) == 1
    assert "unknown registry scope" in report.violations[0]


def test_signed_sample_requires_validation_source(registry, tmp_path):
    sample = tmp_path / "golden_samples" / "GS-500"
    _write_expected(sample, {"case_id": "GS-500", "status": "signed"})
    (sample / "README.md").write_text("# GS-500\n", encoding="utf-8")

    report = registry.build_report(tmp_path / "golden_samples")

    assert report.ok is False
    assert any("validation_source.yaml" in violation for violation in report.violations)


def test_signed_sample_with_traceable_source_passes(registry, tmp_path):
    sample = tmp_path / "golden_samples" / "GS-501"
    _write_expected(sample, {"case_id": "GS-501", "status": "signed"})
    (sample / "README.md").write_text("# GS-501\n", encoding="utf-8")
    (sample / "validation_source.yaml").write_text("citation: synthetic\n", encoding="utf-8")

    report = registry.build_report(tmp_path / "golden_samples")

    assert report.ok is True
    assert report.signed_count == 1
    assert report.records[0].scope == registry.SCOPE_SIGNED


def test_cli_json_reports_current_scope_labels(registry, capsys):
    rc = registry.main(["--root", str(_REPO_ROOT / "golden_samples"), "--format", "json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    by_id = {record["sample_id"]: record for record in payload["records"]}

    assert rc == 0
    assert payload["ok"] is True
    assert by_id["GS-100-radioss-smoke"]["scope"] == "smoke"
    assert by_id["GS-101-demo-unsigned"]["scope"] == "demo-unsigned"
    assert by_id["GS-001"]["scope"] == "insufficient_evidence"
