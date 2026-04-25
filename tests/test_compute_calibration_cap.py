"""Tests for scripts/compute_calibration_cap.py (ADR-012)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_calc():
    import compute_calibration_cap  # type: ignore[import-not-found]

    return compute_calibration_cap


@pytest.fixture(scope="module")
def calc():
    return _load_calc()


# ---------------------------------------------------------------------------
# step_up
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "input_ceiling,expected",
    [(30, 50), (50, 80), (80, 95), (95, 95)],
)
def test_step_up_each_rung(calc, input_ceiling, expected):
    assert calc.step_up(input_ceiling) == expected


def test_step_up_rejects_unknown_ceiling(calc):
    with pytest.raises(ValueError, match="unknown ceiling rung"):
        calc.step_up(42)


# ---------------------------------------------------------------------------
# base_ceiling_from_cr_count
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cr_count,expected",
    [
        (0, 95),
        (1, 80),
        (2, 80),
        (3, 50),
        (4, 50),
        (5, 30),
    ],
)
def test_base_ceiling_each_count(calc, cr_count, expected):
    assert calc.base_ceiling_from_cr_count(cr_count) == expected


def test_base_ceiling_rejects_negative(calc):
    with pytest.raises(ValueError, match="cr_count must be >= 0"):
        calc.base_ceiling_from_cr_count(-1)


# ---------------------------------------------------------------------------
# trailing_approve_count
# ---------------------------------------------------------------------------


def test_trailing_approve_empty(calc):
    assert calc.trailing_approve_count([]) == 0


def test_trailing_approve_no_trailing(calc):
    assert calc.trailing_approve_count(["APPROVE", "CHANGES_REQUIRED"]) == 0


def test_trailing_approve_single(calc):
    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE"]) == 1


def test_trailing_approve_two(calc):
    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE"]) == 2


def test_trailing_approve_three(calc):
    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]) == 3


def test_trailing_approve_all_approve(calc):
    assert calc.trailing_approve_count(["APPROVE"] * 5) == 5


def test_trailing_approve_nits_counts_as_approve(calc):
    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE_WITH_NITS", "APPROVE"]) == 2


def test_trailing_approve_blocker_breaks(calc):
    assert calc.trailing_approve_count(["APPROVE", "BLOCKER", "APPROVE"]) == 1


# ---------------------------------------------------------------------------
# compute_calibration — bootstrap and steady-state scenarios
# ---------------------------------------------------------------------------


def test_compute_bootstrap_5_cr_yields_30_blocking(calc):
    """Session 2026-04-25 bootstrap: 5/5 CHANGES_REQUIRED → ceiling 30, blocking."""
    r = calc.compute_calibration(["CHANGES_REQUIRED"] * 5)
    assert r.ceiling == 30
    assert r.mandatory_codex is True
    assert r.blocking is True
    assert "5 of last 5" in r.basis


def test_compute_ideal_5_approve_yields_95_optional(calc):
    r = calc.compute_calibration(["APPROVE"] * 5)
    assert r.ceiling == 95
    assert r.mandatory_codex is False
    assert r.blocking is False


def test_compute_two_cr_three_approve_recovery_step_up(calc):
    """3-trailing-APPROVE recovery overrides base ceiling to 95."""
    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]
    r = calc.compute_calibration(outcomes)
    # base would be 80 (2 of 5 = CR), but 3 trailing approve → recovery = 95
    assert r.ceiling == 95
    assert "recovery" in r.basis


def test_compute_three_cr_two_approve_step_up_one_rung(calc):
    """2-trailing-APPROVE recovery moves base 50 → 80."""
    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE"]
    r = calc.compute_calibration(outcomes)
    # base = 50 (3 of 5 = CR), 2 trailing → step up to 80
    assert r.ceiling == 80
    assert r.mandatory_codex is False


def test_compute_four_cr_one_approve_no_recovery(calc):
    """1-trailing-APPROVE is below 2 threshold; ceiling stays at base."""
    outcomes = ["CHANGES_REQUIRED"] * 4 + ["APPROVE"]
    r = calc.compute_calibration(outcomes)
    # base = 50 (4 of 5 = CR), 1 trailing → no recovery
    assert r.ceiling == 50
    assert r.mandatory_codex is True
    assert r.blocking is False


def test_compute_more_than_5_uses_only_last_5(calc):
    """Window is last 5 entries; older entries do not affect base count."""
    # 7 entries: first 2 are APPROVE, last 5 are all CR
    outcomes = ["APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
    r = calc.compute_calibration(outcomes)
    assert r.ceiling == 30  # last 5 are all CR


def test_compute_trailing_approve_uses_full_history(calc):
    """Trailing-APPROVE count uses the entire history, not just last 5."""
    # Last 5 = all CR, but trailing 0 APPROVE; ceiling 30
    outcomes = ["APPROVE", "APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
    r = calc.compute_calibration(outcomes)
    assert r.ceiling == 30


def test_compute_empty_history_yields_95(calc):
    """No PRs yet → 0 of last 5 = CR → ceiling 95 (honor system)."""
    r = calc.compute_calibration([])
    assert r.ceiling == 95
    assert r.mandatory_codex is False
    assert r.blocking is False


def test_compute_blocker_counts_as_changes_required(calc):
    """BLOCKER outcome must count as CHANGES_REQUIRED for the formula."""
    r = calc.compute_calibration(["BLOCKER"] * 5)
    assert r.ceiling == 30
    assert r.blocking is True


def test_compute_nits_counts_as_approve(calc):
    """APPROVE_WITH_NITS must count as APPROVE for the formula."""
    r = calc.compute_calibration(["APPROVE_WITH_NITS"] * 5)
    assert r.ceiling == 95


# ---------------------------------------------------------------------------
# load_state
# ---------------------------------------------------------------------------


def test_load_state_missing_file_returns_empty(calc, tmp_path):
    assert calc.load_state(tmp_path / "nonexistent.json") == []


def test_load_state_reads_chronologically(calc, tmp_path):
    """Entries must be sorted by PR number regardless of file order."""
    state = {
        "schema_version": 1,
        "entries": [
            {"pr": 22, "r1_outcome": "BLOCKER"},
            {"pr": 18, "r1_outcome": "APPROVE"},
            {"pr": 20, "r1_outcome": "CHANGES_REQUIRED"},
        ],
    }
    state_path = tmp_path / "calibration_state.json"
    state_path.write_text(json.dumps(state))
    outcomes = calc.load_state(state_path)
    assert outcomes == ["APPROVE", "CHANGES_REQUIRED", "BLOCKER"]  # sorted by pr


def test_load_state_real_file_yields_30_while_last_5_are_cr(calc):
    """The real reports/calibration_state.json must yield 30/BLOCKING
    as long as the last 5 R1 outcomes are CHANGES_REQUIRED.

    Entry count grows monotonically as PRs land — locking it would mean
    every PR breaks this test. The invariant is the ceiling, not the row count.
    """
    state_path = _REPO_ROOT / "reports" / "calibration_state.json"
    outcomes = calc.load_state(state_path)
    assert len(outcomes) >= 5, "state file must have at least 5 bootstrap entries"
    last_5 = outcomes[-5:]
    if all(o in ("CHANGES_REQUIRED", "BLOCKER") for o in last_5):
        r = calc.compute_calibration(outcomes)
        assert r.ceiling == 30
        assert r.blocking is True


# ---------------------------------------------------------------------------
# gate_label
# ---------------------------------------------------------------------------


def test_gate_label_blocking(calc):
    r = calc.CalibrationResult(
        ceiling=30, mandatory_codex=True, blocking=True, basis="b", entry_count=5
    )
    assert calc.gate_label(r) == "BLOCKING"


def test_gate_label_mandatory(calc):
    r = calc.CalibrationResult(
        ceiling=50, mandatory_codex=True, blocking=False, basis="b", entry_count=5
    )
    assert calc.gate_label(r) == "MANDATORY"


def test_gate_label_recommended(calc):
    r = calc.CalibrationResult(
        ceiling=80, mandatory_codex=False, blocking=False, basis="b", entry_count=5
    )
    assert calc.gate_label(r) == "RECOMMENDED"


def test_gate_label_optional(calc):
    r = calc.CalibrationResult(
        ceiling=95, mandatory_codex=False, blocking=False, basis="b", entry_count=5
    )
    assert calc.gate_label(r) == "OPTIONAL"


# ---------------------------------------------------------------------------
# main() — JSON / human / --check
# ---------------------------------------------------------------------------


def test_main_json_output(calc, tmp_path, capsys):
    state = {
        "schema_version": 1,
        "entries": [{"pr": i, "r1_outcome": "CHANGES_REQUIRED"} for i in range(1, 6)],
    }
    state_path = tmp_path / "s.json"
    state_path.write_text(json.dumps(state))
    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ceiling"] == 30
    assert out["mandatory_codex"] is True
    assert out["blocking"] is True
    assert out["entry_count"] == 5
    assert out["gate_label"] == "BLOCKING"


def test_main_human_output(calc, tmp_path, capsys):
    state = {"schema_version": 1, "entries": []}
    state_path = tmp_path / "s.json"
    state_path.write_text(json.dumps(state))
    rc = calc.main(["compute_calibration_cap.py", "--human", "--state", str(state_path)])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "T1 calibration ceiling : 95%" in captured
    assert "OPTIONAL" in captured


def test_main_check_passes_when_claim_below_ceiling(calc, tmp_path):
    state = {"schema_version": 1, "entries": []}  # ceiling 95
    state_path = tmp_path / "s.json"
    state_path.write_text(json.dumps(state))
    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
    assert rc == 0


def test_main_check_fails_when_claim_above_ceiling(calc, tmp_path, capsys):
    state = {
        "schema_version": 1,
        "entries": [{"pr": i, "r1_outcome": "CHANGES_REQUIRED"} for i in range(1, 6)],
    }  # ceiling 30
    state_path = tmp_path / "s.json"
    state_path.write_text(json.dumps(state))
    rc = calc.main(["compute_calibration_cap.py", "--check", "95", "--state", str(state_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "calibration check FAILED" in err
    assert "claimed 95%" in err
    assert "computed ceiling 30%" in err


def test_main_check_at_exact_ceiling_passes(calc, tmp_path):
    """Claim == ceiling must pass (not strictly greater)."""
    state = {
        "schema_version": 1,
        "entries": [{"pr": i, "r1_outcome": "CHANGES_REQUIRED"} for i in range(1, 6)],
    }
    state_path = tmp_path / "s.json"
    state_path.write_text(json.dumps(state))
    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
    assert rc == 0
