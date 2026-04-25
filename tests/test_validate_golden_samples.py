"""Tests for scripts/validate_golden_samples.py (FF-08 / HF3)."""

from __future__ import annotations

import json
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


def _make_sample(
    base: Path,
    sample_id: str,
    *,
    case_id: str | None = None,
    case_name: str = "test sample",
    analysis_type: str = "static_analysis",
    status: str | None = None,
    add_inp: bool = True,
    add_theory: bool = True,
    add_readme: bool = True,
    readme_content: str = "# header\n\nbody",
    expected_extra: dict | None = None,
) -> Path:
    sample_dir = base / sample_id
    sample_dir.mkdir(parents=True)

    if add_readme:
        (sample_dir / "README.md").write_text(readme_content)

    data = {
        "case_id": case_id if case_id is not None else sample_id,
        "case_name": case_name,
        "analysis_type": analysis_type,
    }
    if status is not None:
        data["status"] = status
    if expected_extra:
        data.update(expected_extra)
    (sample_dir / "expected_results.json").write_text(json.dumps(data))

    if add_inp:
        (sample_dir / f"{sample_id.lower()}.inp").write_text("*HEADING\nplaceholder")
    if add_theory:
        (sample_dir / f"{sample_id.lower()}_theory.py").write_text("# theory\n")

    return sample_dir


# ---------------------------------------------------------------------------
# validate_sample — happy paths
# ---------------------------------------------------------------------------


def test_minimal_valid_sample(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-100")
    r = mod.validate_sample(d)
    assert r.violations == []
    assert r.has_inp is True
    assert r.has_theory_script is True
    assert r.status == "active"


def test_with_explicit_active_status(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-101", status="active")
    r = mod.validate_sample(d)
    assert r.violations == []


def test_insufficient_evidence_with_fp_reference(mod, tmp_path):
    d = _make_sample(
        tmp_path,
        "GS-102",
        status="insufficient_evidence",
        readme_content="# GS-102\n\nFlagged by FP-003 per ADR-011.",
    )
    r = mod.validate_sample(d)
    assert r.violations == []
    assert r.warnings == []


def test_only_theory_script_passes_without_inp(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-103", add_inp=False)
    r = mod.validate_sample(d)
    assert r.violations == []
    assert r.has_inp is False


def test_only_inp_passes_without_theory(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-104", add_theory=False)
    r = mod.validate_sample(d)
    assert r.violations == []


# ---------------------------------------------------------------------------
# validate_sample — violations
# ---------------------------------------------------------------------------


def test_missing_readme_is_violation(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-200", add_readme=False)
    r = mod.validate_sample(d)
    assert any("missing README.md" in v for v in r.violations)


def test_empty_readme_is_violation(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-201", readme_content="")
    r = mod.validate_sample(d)
    assert any("README.md is empty" in v for v in r.violations)


def test_missing_expected_results_aborts(mod, tmp_path):
    d = tmp_path / "GS-202"
    d.mkdir()
    (d / "README.md").write_text("ok")
    r = mod.validate_sample(d)
    assert any("missing expected_results.json" in v for v in r.violations)


def test_invalid_json_in_expected_results(mod, tmp_path):
    d = tmp_path / "GS-203"
    d.mkdir()
    (d / "README.md").write_text("ok")
    (d / "expected_results.json").write_text("{not valid json")
    r = mod.validate_sample(d)
    assert any("not valid JSON" in v for v in r.violations)


def test_case_id_mismatch(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-204", case_id="GS-999")
    r = mod.validate_sample(d)
    assert any("does not match directory name" in v for v in r.violations)


def test_missing_case_name(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-205", case_name="")
    r = mod.validate_sample(d)
    assert any("missing or empty `case_name`" in v for v in r.violations)


def test_unknown_analysis_type(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-206", analysis_type="bogus_type")
    r = mod.validate_sample(d)
    assert any("not in known set" in v and "analysis_type" in v for v in r.violations)


def test_unknown_status(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-207", status="weirdo")
    r = mod.validate_sample(d)
    assert any("not in known set" in v and "status" in v for v in r.violations)


def test_no_inp_and_no_theory_is_violation(mod, tmp_path):
    d = _make_sample(tmp_path, "GS-208", add_inp=False, add_theory=False)
    r = mod.validate_sample(d)
    assert any("missing both .inp file and theory script" in v for v in r.violations)


# ---------------------------------------------------------------------------
# validate_sample — warnings (non-blocking)
# ---------------------------------------------------------------------------


def test_insufficient_evidence_without_fp_reference_warns(mod, tmp_path):
    d = _make_sample(
        tmp_path,
        "GS-300",
        status="insufficient_evidence",
        readme_content="# GS-300\n\nNo FP reference here.",
    )
    r = mod.validate_sample(d)
    assert r.violations == []  # not a violation
    assert any("FP-NNN" in w or "FailurePattern" in w for w in r.warnings)


# ---------------------------------------------------------------------------
# discover_samples + main()
# ---------------------------------------------------------------------------


def test_discover_samples_finds_gs_dirs(mod, tmp_path):
    gs_root = tmp_path / "golden_samples"
    gs_root.mkdir()
    _make_sample(gs_root, "GS-401")
    _make_sample(gs_root, "GS-402")
    (gs_root / "not_a_gs_dir").mkdir()  # wrong prefix
    (gs_root / "GS-decoy.txt").write_text("file not dir")

    samples = mod.discover_samples(tmp_path)
    names = sorted(p.name for p in samples)
    assert names == ["GS-401", "GS-402"]


def test_main_human_output_passes(mod, tmp_path, capsys, monkeypatch):
    gs_root = tmp_path / "golden_samples"
    gs_root.mkdir()
    _make_sample(gs_root, "GS-501")
    rc = mod.main(["validate_golden_samples.py", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "[OK] GS-501" in out
    assert "Summary: 1/1 OK" in out
    assert rc == 0


def test_main_human_output_fails_with_violation(mod, tmp_path, capsys):
    gs_root = tmp_path / "golden_samples"
    gs_root.mkdir()
    _make_sample(gs_root, "GS-502", case_name="")  # violation
    rc = mod.main(["validate_golden_samples.py", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "[FAIL]" in out
    assert "VIOLATION" in out
    assert rc == 1


def test_main_json_output(mod, tmp_path, capsys):
    gs_root = tmp_path / "golden_samples"
    gs_root.mkdir()
    _make_sample(gs_root, "GS-503")
    rc = mod.main(["validate_golden_samples.py", "--json", "--root", str(tmp_path)])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert parsed[0]["sample_id"] == "GS-503"
    assert parsed[0]["violations"] == []
    assert rc == 0


def test_main_explicit_dirs(mod, tmp_path, capsys):
    """Pass specific dirs as positional args."""
    gs_root = tmp_path / "g"
    gs_root.mkdir()
    d1 = _make_sample(gs_root, "GS-601")
    rc = mod.main(["validate_golden_samples.py", str(d1)])
    out = capsys.readouterr().out
    assert "GS-601" in out
    assert rc == 0


def test_main_no_samples_returns_2(mod, tmp_path, capsys):
    """Empty root should return 2 (usage error)."""
    rc = mod.main(["validate_golden_samples.py", "--root", str(tmp_path)])
    err = capsys.readouterr().err
    assert "no golden samples" in err
    assert rc == 2


# ---------------------------------------------------------------------------
# Integration with the actual repo
# ---------------------------------------------------------------------------


def test_real_golden_samples_pass(mod):
    """The actual GS-001/002/003 in the repo must pass current schema."""
    repo_samples = mod.discover_samples(_REPO_ROOT)
    assert len(repo_samples) >= 3, f"expected ≥3 GS-* dirs, found {len(repo_samples)}"
    for d in repo_samples:
        r = mod.validate_sample(d)
        assert r.violations == [], f"{d.name} has violations: {r.violations}"
