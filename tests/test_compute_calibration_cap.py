"""Tests for scripts/compute_calibration_cap.py (ADR-012).

R2 update (2026-04-26, post Codex R1 CHANGES_REQUIRED):
  * load_state now sorts by merged_at, not PR number — see
    `test_load_state_sorts_by_merged_at_not_pr_counterexample` for the
    Codex-cited regression case.
  * Missing/malformed state is now a hard CalibrationStateError; see
    the "adversarial state validation" block below.
"""

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


def _entry(pr: int, merged_at: str, outcome: str = "CHANGES_REQUIRED") -> dict:
    """Build a valid entry dict for tests."""
    return {"pr": pr, "merged_at": merged_at, "r1_outcome": outcome}


def _write_state(tmp_path: Path, entries: list[dict], schema_version: int = 1) -> Path:
    state_path = tmp_path / "calibration_state.json"
    state_path.write_text(json.dumps({"schema_version": schema_version, "entries": entries}))
    return state_path


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
    assert r.ceiling == 95
    assert "recovery" in r.basis


def test_compute_three_cr_two_approve_step_up_one_rung(calc):
    """2-trailing-APPROVE recovery moves base 50 → 80."""
    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE"]
    r = calc.compute_calibration(outcomes)
    assert r.ceiling == 80
    assert r.mandatory_codex is False


def test_compute_four_cr_one_approve_no_recovery(calc):
    """1-trailing-APPROVE is below 2 threshold; ceiling stays at base."""
    outcomes = ["CHANGES_REQUIRED"] * 4 + ["APPROVE"]
    r = calc.compute_calibration(outcomes)
    assert r.ceiling == 50
    assert r.mandatory_codex is True
    assert r.blocking is False


def test_compute_more_than_5_uses_only_last_5(calc):
    """Window is last 5 entries; older entries do not affect base count."""
    outcomes = ["APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
    r = calc.compute_calibration(outcomes)
    assert r.ceiling == 30


def test_compute_trailing_approve_uses_full_history(calc):
    """Trailing-APPROVE count uses the entire history, not just last 5."""
    outcomes = ["APPROVE", "APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
    r = calc.compute_calibration(outcomes)
    assert r.ceiling == 30


def test_compute_empty_history_yields_95(calc):
    """No PRs yet → 0 of last 5 = CR → ceiling 95.

    Note: this only tests the pure-function compute_calibration; the load_state
    side now hard-errors on a MISSING file, so the empty-history branch is
    only reachable via an explicitly-empty entries list, which the establishing
    PR must seed deliberately.
    """
    r = calc.compute_calibration([])
    assert r.ceiling == 95
    assert r.mandatory_codex is False
    assert r.blocking is False


def test_compute_blocker_counts_as_changes_required(calc):
    r = calc.compute_calibration(["BLOCKER"] * 5)
    assert r.ceiling == 30
    assert r.blocking is True


def test_compute_nits_counts_as_approve(calc):
    r = calc.compute_calibration(["APPROVE_WITH_NITS"] * 5)
    assert r.ceiling == 95


# ---------------------------------------------------------------------------
# load_state — happy path + chronological sort by merged_at (R2 fix HIGH 1)
# ---------------------------------------------------------------------------


def test_load_state_sorts_by_merged_at(calc, tmp_path):
    """Entries must be ordered by merged_at, not file order."""
    state_path = _write_state(
        tmp_path,
        [
            _entry(22, "2026-04-25T10:43:55Z", "BLOCKER"),
            _entry(18, "2026-04-25T08:53:09Z", "APPROVE"),
            _entry(20, "2026-04-25T08:33:51Z", "CHANGES_REQUIRED"),
        ],
    )
    outcomes = calc.load_state(state_path)
    # merged_at order: 20 (08:33), 18 (08:53), 22 (10:43)
    assert outcomes == ["CHANGES_REQUIRED", "APPROVE", "BLOCKER"]


def test_load_state_sorts_by_merged_at_not_pr_counterexample(calc, tmp_path):
    """Codex R1 HIGH #1 regression: PR #20 merged BEFORE PR #18 and #19.

    With the old PR-number sort, the recovery calculation diverges. Verify
    that sorting by merged_at gives the truly chronological sequence.
    """
    state_path = _write_state(
        tmp_path,
        [
            _entry(18, "2026-04-25T08:53:09Z", "CHANGES_REQUIRED"),
            _entry(19, "2026-04-25T08:56:46Z", "APPROVE"),
            _entry(20, "2026-04-25T08:33:51Z", "APPROVE"),
        ],
    )
    outcomes = calc.load_state(state_path)
    # merged_at order: 20, 18, 19 — so sequence is APPROVE, CR, APPROVE
    # Trailing approve = 1 (from #19), no recovery
    assert outcomes == ["APPROVE", "CHANGES_REQUIRED", "APPROVE"]
    r = calc.compute_calibration(outcomes)
    # Compare with the WRONG (PR-sorted) order: would be CR, APPROVE, APPROVE
    # which has 2 trailing APPROVE → recovery step up. The chronologically
    # correct answer has only 1 trailing APPROVE → no recovery.
    assert "trailing APPROVE" not in r.basis
    assert r.ceiling == 80  # 1 of last 5 = CR → base 80, no recovery


def test_load_state_real_file_yields_30_while_last_5_are_cr(calc):
    """The real reports/calibration_state.json must yield 30/BLOCKING
    as long as the last 5 R1 outcomes are CHANGES_REQUIRED."""
    state_path = _REPO_ROOT / "reports" / "calibration_state.json"
    outcomes = calc.load_state(state_path)
    assert len(outcomes) >= 5
    last_5 = outcomes[-5:]
    if all(o in ("CHANGES_REQUIRED", "BLOCKER") for o in last_5):
        r = calc.compute_calibration(outcomes)
        assert r.ceiling == 30
        assert r.blocking is True


# ---------------------------------------------------------------------------
# load_state — adversarial state validation (R2 fix HIGH 2)
# ---------------------------------------------------------------------------


def test_load_state_missing_file_is_hard_error(calc, tmp_path):
    """R2 fix: missing state file used to fail-open at 95%/OPTIONAL."""
    with pytest.raises(calc.CalibrationStateError, match="not found"):
        calc.load_state(tmp_path / "definitely-missing.json")


def test_load_state_invalid_json_is_hard_error(calc, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not-valid-json")
    with pytest.raises(calc.CalibrationStateError, match="not valid JSON"):
        calc.load_state(bad)


def test_load_state_non_dict_root_is_hard_error(calc, tmp_path):
    bad = tmp_path / "list_root.json"
    bad.write_text("[1, 2, 3]")
    with pytest.raises(calc.CalibrationStateError, match="JSON object"):
        calc.load_state(bad)


def test_load_state_wrong_schema_version_is_hard_error(calc, tmp_path):
    state_path = _write_state(tmp_path, [], schema_version=999)
    with pytest.raises(calc.CalibrationStateError, match="schema_version"):
        calc.load_state(state_path)


def test_load_state_missing_schema_version_is_hard_error(calc, tmp_path):
    bad = tmp_path / "no_schema.json"
    bad.write_text(json.dumps({"entries": []}))
    with pytest.raises(calc.CalibrationStateError, match="schema_version"):
        calc.load_state(bad)


def test_load_state_entries_not_list_is_hard_error(calc, tmp_path):
    bad = tmp_path / "bad_entries.json"
    bad.write_text(json.dumps({"schema_version": 1, "entries": "not-a-list"}))
    with pytest.raises(calc.CalibrationStateError, match="entries"):
        calc.load_state(bad)


def test_load_state_duplicate_pr_is_hard_error(calc, tmp_path):
    state_path = _write_state(
        tmp_path,
        [
            _entry(18, "2026-04-25T08:53:09Z"),
            _entry(18, "2026-04-25T09:00:00Z"),  # same PR number twice
        ],
    )
    with pytest.raises(calc.CalibrationStateError, match="duplicate"):
        calc.load_state(state_path)


def test_load_state_missing_merged_at_is_hard_error(calc, tmp_path):
    bad = tmp_path / "no_merged_at.json"
    bad.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [{"pr": 18, "r1_outcome": "APPROVE"}],
            }
        )
    )
    with pytest.raises(calc.CalibrationStateError, match="merged_at"):
        calc.load_state(bad)


def test_load_state_unknown_outcome_is_hard_error(calc, tmp_path):
    state_path = _write_state(
        tmp_path,
        [{"pr": 18, "merged_at": "2026-04-25T08:53:09Z", "r1_outcome": "MAYBE"}],
    )
    with pytest.raises(calc.CalibrationStateError, match="r1_outcome"):
        calc.load_state(state_path)


def test_load_state_non_int_pr_is_hard_error(calc, tmp_path):
    state_path = _write_state(
        tmp_path,
        [{"pr": "eighteen", "merged_at": "2026-04-25T08:53:09Z", "r1_outcome": "APPROVE"}],
    )
    with pytest.raises(calc.CalibrationStateError, match="pr"):
        calc.load_state(state_path)


def test_load_state_zero_pr_is_hard_error(calc, tmp_path):
    state_path = _write_state(tmp_path, [_entry(0, "2026-04-25T08:53:09Z")])
    with pytest.raises(calc.CalibrationStateError, match="positive int"):
        calc.load_state(state_path)


def test_load_state_negative_pr_is_hard_error(calc, tmp_path):
    state_path = _write_state(tmp_path, [_entry(-1, "2026-04-25T08:53:09Z")])
    with pytest.raises(calc.CalibrationStateError, match="positive int"):
        calc.load_state(state_path)


def test_load_state_non_dict_entry_is_hard_error(calc, tmp_path):
    bad = tmp_path / "bad_entry.json"
    bad.write_text(json.dumps({"schema_version": 1, "entries": ["not-a-dict"]}))
    with pytest.raises(calc.CalibrationStateError, match="JSON object"):
        calc.load_state(bad)


def test_load_state_empty_entries_list_is_valid(calc, tmp_path):
    """An empty list of entries is valid (only the establishing PR uses this)."""
    state_path = _write_state(tmp_path, [])
    assert calc.load_state(state_path) == []


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
# main() — JSON / human / --check + R2 fail-closed paths
# ---------------------------------------------------------------------------


def test_main_json_output(calc, tmp_path, capsys):
    state_path = _write_state(
        tmp_path,
        [_entry(i, f"2026-04-25T08:0{i}:00Z") for i in range(1, 6)],
    )
    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ceiling"] == 30
    assert out["mandatory_codex"] is True
    assert out["blocking"] is True
    assert out["entry_count"] == 5
    assert out["gate_label"] == "BLOCKING"


def test_main_human_output(calc, tmp_path, capsys):
    state_path = _write_state(tmp_path, [])
    rc = calc.main(["compute_calibration_cap.py", "--human", "--state", str(state_path)])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "T1 calibration ceiling : 95%" in captured
    assert "OPTIONAL" in captured


def test_main_check_passes_when_claim_below_ceiling(calc, tmp_path):
    state_path = _write_state(tmp_path, [])  # ceiling 95
    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
    assert rc == 0


def test_main_check_fails_when_claim_above_ceiling(calc, tmp_path, capsys):
    state_path = _write_state(
        tmp_path,
        [_entry(i, f"2026-04-25T08:0{i}:00Z") for i in range(1, 6)],
    )  # ceiling 30
    rc = calc.main(["compute_calibration_cap.py", "--check", "95", "--state", str(state_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "calibration check FAILED" in err
    assert "claimed 95%" in err
    assert "computed ceiling 30%" in err


def test_main_check_at_exact_ceiling_passes(calc, tmp_path):
    """Claim == ceiling must pass (not strictly greater)."""
    state_path = _write_state(
        tmp_path,
        [_entry(i, f"2026-04-25T08:0{i}:00Z") for i in range(1, 6)],
    )
    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
    assert rc == 0


# ---------------------------------------------------------------------------
# main() — R2 fail-closed enforcement
# ---------------------------------------------------------------------------


def test_main_missing_state_file_returns_1(calc, tmp_path, capsys):
    """R2 fix: --check used to silently pass when state file was missing.

    Codex R1 reproduction: `--check 95 --state /tmp/does-not-exist.json` → 0.
    Now: hard error, exit 1, no fail-open.
    """
    rc = calc.main(
        [
            "compute_calibration_cap.py",
            "--check",
            "95",
            "--state",
            str(tmp_path / "missing.json"),
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "calibration state error" in err
    assert "not found" in err


def test_main_invalid_json_returns_1(calc, tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("not-valid-json")
    rc = calc.main(["compute_calibration_cap.py", "--state", str(bad)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "calibration state error" in err


def test_main_wrong_schema_version_returns_1(calc, tmp_path, capsys):
    state_path = _write_state(tmp_path, [], schema_version=999)
    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "schema_version" in err


def test_main_duplicate_pr_returns_1(calc, tmp_path, capsys):
    state_path = _write_state(
        tmp_path,
        [
            _entry(18, "2026-04-25T08:53:09Z"),
            _entry(18, "2026-04-25T09:00:00Z"),
        ],
    )
    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "duplicate" in err
