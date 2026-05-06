"""Tests for scripts/validate_golden_samples.py (FF-08 / HF3)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture(scope="module")
def mod():
    import validate_golden_samples  # type: ignore[import-not-found]

    return validate_golden_samples


def _write_sample(
    root: Path,
    sample_id: str = "GS-900",
    *,
    metadata: dict[str, object] | None = None,
    readme_text: str | None = None,
    add_input: bool = True,
) -> Path:
    sample_dir = root / "golden_samples" / sample_id
    sample_dir.mkdir(parents=True)
    if readme_text is None:
        readme_text = "# Synthetic validation case\n"
    (sample_dir / "README.md").write_text(readme_text, encoding="utf-8")
    data: dict[str, object] = {
        "case_id": sample_id,
        "case_name": "Synthetic validation case",
        "analysis_type": "static_analysis",
        "status": "active",
    }
    if metadata:
        data.update(metadata)
    (sample_dir / "expected_results.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )
    if add_input:
        (sample_dir / f"{sample_id.lower().replace('-', '')}.inp").write_text(
            "*HEADING\n",
            encoding="utf-8",
        )
    return sample_dir


def test_current_signed_samples_validate_and_exclude_unsigned_fixtures(mod) -> None:
    result = mod.validate_registry(_REPO_ROOT)

    assert result.ok, result.errors
    assert result.sample_ids == ["GS-001", "GS-002", "GS-003"]
    assert result.sample_count == 3


def test_discovery_includes_only_signed_gs_id_directories(mod, tmp_path: Path) -> None:
    _write_sample(tmp_path, "GS-900")
    (tmp_path / "golden_samples" / "GS-100-radioss-smoke").mkdir(parents=True)
    (tmp_path / "golden_samples" / "GS-101-demo-unsigned").mkdir()
    (tmp_path / "golden_samples" / "notes").mkdir()

    result = mod.validate_registry(tmp_path)

    assert result.ok, result.errors
    assert result.sample_ids == ["GS-900"]


def test_symlinked_signed_sample_directory_is_rejected(mod, tmp_path: Path) -> None:
    external_root = tmp_path / "external"
    target = _write_sample(external_root, "GS-900")
    golden_root = tmp_path / "golden_samples"
    golden_root.mkdir()
    os.symlink(target, golden_root / "GS-900", target_is_directory=True)

    result = mod.validate_registry(tmp_path)

    assert not result.ok
    assert any("signed sample directory must not be a symlink" in error for error in result.errors)


def test_insufficient_evidence_requires_failure_pattern_ref_and_reason(mod, tmp_path: Path) -> None:
    _write_sample(
        tmp_path,
        metadata={
            "status": "insufficient_evidence",
        },
        readme_text="See FP-900.\n",
    )

    result = mod.validate_registry(tmp_path)

    assert not result.ok
    assert any("failure_pattern_ref" in error for error in result.errors)
    assert any("status_reason" in error for error in result.errors)


def test_failure_pattern_ref_must_match_fp_id(mod, tmp_path: Path) -> None:
    _write_sample(
        tmp_path,
        metadata={
            "status": "insufficient_evidence",
            "failure_pattern_ref": "failure-pattern-900",
            "status_reason": "Reference is not defensible.",
        },
        readme_text="See failure-pattern-900.\n",
    )

    result = mod.validate_registry(tmp_path)

    assert not result.ok
    assert any("failure_pattern_ref must match FP-<id>" in error for error in result.errors)


def test_case_id_must_match_sample_directory(mod, tmp_path: Path) -> None:
    _write_sample(tmp_path, "GS-900", metadata={"case_id": "GS-901"})

    result = mod.validate_registry(tmp_path)

    assert not result.ok
    assert any("case_id must match directory name" in error for error in result.errors)


def test_missing_required_files_and_evidence_are_reported(mod, tmp_path: Path) -> None:
    sample_dir = tmp_path / "golden_samples" / "GS-900"
    sample_dir.mkdir(parents=True)

    result = mod.validate_registry(tmp_path)

    assert not result.ok
    assert any("missing README.md" in error for error in result.errors)
    assert any("missing expected_results.json" in error for error in result.errors)
    assert any(
        "must include at least one .inp or theory .py artifact" in error for error in result.errors
    )


def test_cli_reports_success(mod, tmp_path: Path, capsys) -> None:
    _write_sample(tmp_path, "GS-900")

    rc = mod.main(["--root", str(tmp_path)])

    assert rc == 0
    out = capsys.readouterr().out
    assert "HF3 golden-sample registry validation passed" in out
    assert "GS-900" in out


def test_cli_reports_failure(mod, tmp_path: Path, capsys) -> None:
    _write_sample(tmp_path, "GS-900", metadata={"case_id": "WRONG"})

    rc = mod.main(["--root", str(tmp_path)])

    assert rc == 1
    err = capsys.readouterr().err
    assert "HF3 golden-sample registry validation failed" in err
    assert "GS-900" in err
