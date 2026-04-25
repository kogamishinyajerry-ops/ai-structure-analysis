"""Tests for scripts/hf1_path_guard.py (FF-06)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_guard():
    # Import via sys.path so cls.__module__ resolves correctly under
    # the dataclass + `from __future__ import annotations` combo
    # (importlib.util.spec_from_file_location triggers a Python 3.9
    # dataclasses bug otherwise; CI is 3.11 but local dev may be 3.9).
    import hf1_path_guard  # type: ignore[import-not-found]

    return hf1_path_guard


@pytest.fixture(scope="module")
def guard():
    return _load_guard()


# ---------------------------------------------------------------------------
# Pure-function checks (no env, no stderr, no exit)
# ---------------------------------------------------------------------------


def test_zone_has_all_eight_categories(guard):
    rule_prefixes = {entry.rule.split(" — ", 1)[0] for entry in guard.ZONE}
    expected = {f"HF1.{i}" for i in range(1, 9)}
    assert rule_prefixes == expected, (
        f"missing or extra HF1 zone categories: "
        f"got {sorted(rule_prefixes)}, expected {sorted(expected)}"
    )


def test_exact_match_hits_zone(guard):
    entry = next(e for e in guard.ZONE if e.path == "agents/router.py")
    assert guard.path_hits_zone("agents/router.py", entry) is True


def test_exact_match_does_not_partial_match(guard):
    """`agents/router.py` exact-match must not match `agents/router_old.py`."""
    entry = next(e for e in guard.ZONE if e.path == "agents/router.py")
    assert guard.path_hits_zone("agents/router_old.py", entry) is False
    assert guard.path_hits_zone("agents/router.py.bak", entry) is False


def test_prefix_match_hits_subdir(guard):
    entry = next(e for e in guard.ZONE if e.path == "golden_samples/")
    assert guard.path_hits_zone("golden_samples/GS-001/expected_results.json", entry) is True
    assert guard.path_hits_zone("golden_samples/", entry) is True


def test_prefix_match_does_not_match_unrelated_file(guard):
    entry = next(e for e in guard.ZONE if e.path == "docs/adr/")
    assert guard.path_hits_zone("docs/quickstart.md", entry) is False
    assert guard.path_hits_zone("docs/governance/foo.md", entry) is False


def test_unknown_match_mode_raises(guard):
    bad = guard.ZoneEntry(path="x", match="regex", rule="r", adr_ref="r")
    with pytest.raises(ValueError, match="unknown match mode"):
        guard.path_hits_zone("x", bad)


# ---------------------------------------------------------------------------
# find_violations
# ---------------------------------------------------------------------------


def test_no_violations_for_safe_paths(guard):
    safe = [
        "backend/app/main.py",
        "frontend/src/App.tsx",
        "docs/quickstart.md",
        "scripts/install_dependencies.sh",
        ".planning/STATE.md",
    ]
    assert guard.find_violations(safe) == []


def test_violations_for_each_zone_entry(guard):
    """One representative path per HF1 category must be flagged."""
    representatives = [
        "agents/solver.py",
        "agents/router.py",
        "agents/geometry.py",
        "schemas/sim_state.py",
        "tests/test_toolchain_probes.py",
        "Dockerfile",
        "Makefile",
        "golden_samples/GS-001/gs001.inp",
        "docs/adr/ADR-011-pivot-claude-code-takeover.md",
        "docs/governance/anything.md",
        "tools/calculix_driver.py",
    ]
    hits = guard.find_violations(representatives)
    assert len(hits) == len(representatives)
    hit_paths = {p for p, _ in hits}
    assert hit_paths == set(representatives)


def test_first_match_wins_no_double_count(guard):
    """A path that matches one entry should not be counted twice."""
    hits = guard.find_violations(["agents/router.py"])
    assert len(hits) == 1


# ---------------------------------------------------------------------------
# main() — exit codes and override
# ---------------------------------------------------------------------------


def test_main_exit_zero_on_no_args(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    assert guard.main(["hf1_path_guard.py"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""


def test_main_exit_zero_on_safe_files(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.main(["hf1_path_guard.py", "backend/app/main.py", "docs/quickstart.md"])
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_main_exit_one_on_zone_violation(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.main(["hf1_path_guard.py", "agents/solver.py"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "HF1 forbidden-zone violation" in err
    assert "agents/solver.py" in err
    assert "HF1.1" in err
    assert "ADR-011 §HF1 #1" in err
    assert "Resolution paths" in err


def test_main_override_with_reason_allows_pass(guard, capsys, monkeypatch):
    monkeypatch.setenv("HF1_GUARD_OVERRIDE", "hot-fix CVE-2026-0001 per security incident")
    rc = guard.main(["hf1_path_guard.py", "agents/solver.py"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "HF1 OVERRIDE active" in err
    assert "hot-fix CVE-2026-0001" in err
    assert "Reviewer note" in err


def test_main_override_with_empty_reason_still_blocks(guard, capsys, monkeypatch):
    """Empty HF1_GUARD_OVERRIDE must not bypass the guard."""
    monkeypatch.setenv("HF1_GUARD_OVERRIDE", "")
    rc = guard.main(["hf1_path_guard.py", "agents/solver.py"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "HF1 forbidden-zone violation" in err
    assert "OVERRIDE" not in err.split("violation")[0]  # no override banner before violation


def test_main_override_with_whitespace_reason_blocks(guard, capsys, monkeypatch):
    """Whitespace-only reason is rejected the same as empty."""
    monkeypatch.setenv("HF1_GUARD_OVERRIDE", "   \t  ")
    rc = guard.main(["hf1_path_guard.py", "Dockerfile"])
    assert rc == 1


def test_main_lists_all_violations_not_just_first(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.main(
        [
            "hf1_path_guard.py",
            "agents/solver.py",
            "schemas/sim_state.py",
            "Dockerfile",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "agents/solver.py" in err
    assert "schemas/sim_state.py" in err
    assert "Dockerfile" in err


def test_script_invocable_via_subprocess(monkeypatch, tmp_path):
    """Smoke-test that the script can be invoked end-to-end as pre-commit would."""
    import subprocess

    here = Path(__file__).resolve()
    repo_root = here.parent.parent
    guard_path = repo_root / "scripts" / "hf1_path_guard.py"

    env = {k: v for k, v in __import__("os").environ.items() if k != "HF1_GUARD_OVERRIDE"}

    # Safe file → exit 0
    rc = subprocess.run(
        [sys.executable, str(guard_path), "backend/app/main.py"],
        capture_output=True,
        env=env,
    ).returncode
    assert rc == 0

    # Zone file → exit 1
    rc = subprocess.run(
        [sys.executable, str(guard_path), "agents/router.py"],
        capture_output=True,
        env=env,
    ).returncode
    assert rc == 1
