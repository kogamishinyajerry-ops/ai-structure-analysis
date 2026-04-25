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


def test_zone_has_all_nine_categories(guard):
    """Per AR-2026-04-25-001 §3: HF1.1-HF1.7 (preserved) + HF1.8 (path-guard
    self-protection, NEW) + HF1.9 (.github/workflows/, NEW). docs/adr/ and
    docs/governance/ moved out of HF1 entirely (now PR-protected zone)."""
    rule_prefixes = {entry.rule.split(" — ", 1)[0] for entry in guard.ZONE}
    expected = {f"HF1.{i}" for i in range(1, 10)}
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
    entry = next(e for e in guard.ZONE if e.path == ".github/workflows/")
    assert guard.path_hits_zone("docs/quickstart.md", entry) is False
    assert guard.path_hits_zone(".github/dependabot.yml", entry) is False
    assert guard.path_hits_zone(".github/ISSUE_TEMPLATE/bug.md", entry) is False


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
        # Per AR-2026-04-25-001 §3: docs/adr/ and docs/governance/ moved
        # out of HF1 hard-stop into PR-protected zone (branch protection
        # + mandatory Codex enforce them; this script does not).
        "docs/adr/ADR-011-pivot-claude-code-takeover.md",
        "docs/adr/ADR-012-calibration-cap.md",
        "docs/governance/whatever.md",
        "docs/failure_patterns/FP-001.md",
    ]
    assert guard.find_violations(safe) == []


def test_violations_for_each_zone_entry(guard):
    """One representative path per HF1 category must be flagged.

    Per AR-2026-04-25-001 §3: HF1.8 is now `scripts/hf1_path_guard.py`
    (meta-protection, not docs/governance/); HF1.9 is `.github/workflows/`
    (CI enforcement). docs/adr/ + docs/governance/ are no longer HF1.
    """
    representatives = [
        "agents/solver.py",
        "tools/calculix_driver.py",
        "agents/router.py",
        "agents/geometry.py",
        "schemas/sim_state.py",
        "tests/test_toolchain_probes.py",
        "Dockerfile",
        "Makefile",
        "golden_samples/GS-001/gs001.inp",
        "scripts/hf1_path_guard.py",  # HF1.8 — self-protection
        ".github/workflows/ci.yml",  # HF1.9 — CI workflow
    ]
    hits = guard.find_violations(representatives)
    assert len(hits) == len(representatives)
    hit_paths = {p for p, _ in hits}
    assert hit_paths == set(representatives)


def test_self_protection_rejects_path_guard_modification(guard):
    """HF1.8 — modification of scripts/hf1_path_guard.py itself triggers."""
    hits = guard.find_violations(["scripts/hf1_path_guard.py"])
    assert len(hits) == 1
    assert "HF1.8" in hits[0][1].rule
    assert "self-modify" in hits[0][1].rule


def test_ci_workflow_modification_triggers(guard):
    """HF1.9 — any .github/workflows/ change is HF1."""
    hits = guard.find_violations([".github/workflows/ci.yml"])
    assert len(hits) == 1
    assert "HF1.9" in hits[0][1].rule


def test_pr_protected_zone_paths_are_NOT_hf1(guard):
    """Per AR-2026-04-25-001 §3: docs/adr/, docs/governance/,
    docs/failure_patterns/ are PR-protected (branch protection + Codex)
    but NOT HF1 hard-stop. This test enforces the boundary."""
    pr_protected = [
        "docs/adr/ADR-011-pivot-claude-code-takeover.md",
        "docs/adr/ADR-012-calibration-cap.md",
        "docs/governance/something.md",
        "docs/failure_patterns/FP-001-cantilever.md",
        "docs/failure_patterns/README.md",
    ]
    assert guard.find_violations(pr_protected) == []


def test_first_match_wins_no_double_count(guard):
    """A path that matches one entry should not be counted twice."""
    hits = guard.find_violations(["agents/router.py"])
    assert len(hits) == 1


def test_duplicate_paths_only_reported_once(guard):
    """If git surfaces the same path twice (e.g., parsed from rename), don't double-count."""
    hits = guard.find_violations(["agents/solver.py", "agents/solver.py"])
    assert len(hits) == 1


# ---------------------------------------------------------------------------
# parse_name_status_z — git rename/delete coverage
# ---------------------------------------------------------------------------


def test_parse_empty_returns_empty(guard):
    assert guard.parse_name_status_z("") == []


def test_parse_single_modify(guard):
    blob = "M\0agents/router.py\0"
    assert guard.parse_name_status_z(blob) == ["agents/router.py"]


def test_parse_single_add(guard):
    blob = "A\0backend/new.py\0"
    assert guard.parse_name_status_z(blob) == ["backend/new.py"]


def test_parse_single_delete(guard):
    """Delete must surface the deleted path so HF1 catches `rm agents/solver.py`."""
    blob = "D\0agents/solver.py\0"
    assert guard.parse_name_status_z(blob) == ["agents/solver.py"]


def test_parse_rename_returns_both_sides(guard):
    """Rename A->B must surface BOTH A and B so renaming a zone path away triggers."""
    blob = "R100\0agents/router.py\0agents/router_old.py\0"
    paths = guard.parse_name_status_z(blob)
    assert paths == ["agents/router.py", "agents/router_old.py"]


def test_parse_copy_returns_both_sides(guard):
    blob = "C75\0Makefile\0Makefile.copy\0"
    paths = guard.parse_name_status_z(blob)
    assert paths == ["Makefile", "Makefile.copy"]


def test_parse_mixed_records(guard):
    blob = (
        "M\0backend/main.py\0"
        "D\0agents/solver.py\0"
        "R100\0agents/router.py\0agents/router_v2.py\0"
        "A\0docs/quickstart.md\0"
    )
    paths = guard.parse_name_status_z(blob)
    assert paths == [
        "backend/main.py",
        "agents/solver.py",
        "agents/router.py",
        "agents/router_v2.py",
        "docs/quickstart.md",
    ]


def test_rename_of_zone_file_caught(guard):
    """Integration: rename old-path is in zone → must flag."""
    blob = "R100\0agents/router.py\0agents/router_old.py\0"
    paths = guard.parse_name_status_z(blob)
    hits = guard.find_violations(paths)
    hit_paths = {p for p, _ in hits}
    assert "agents/router.py" in hit_paths


def test_delete_of_zone_file_caught(guard):
    blob = "D\0schemas/sim_state.py\0"
    paths = guard.parse_name_status_z(blob)
    hits = guard.find_violations(paths)
    assert len(hits) == 1
    assert hits[0][0] == "schemas/sim_state.py"


# ---------------------------------------------------------------------------
# check_paths_and_report — pure decision + reporting (no git IO)
# ---------------------------------------------------------------------------


def test_check_no_paths_returns_zero(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    assert guard.check_paths_and_report([]) == 0
    assert capsys.readouterr().err == ""


def test_check_safe_paths_returns_zero(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.check_paths_and_report(["backend/app/main.py", "docs/quickstart.md"])
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_check_zone_violation_returns_one(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.check_paths_and_report(["agents/solver.py"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "HF1 forbidden-zone violation" in err
    assert "agents/solver.py" in err
    assert "HF1.1" in err
    assert "ADR-011 §HF1 #1" in err
    assert "Resolution paths" in err


def test_check_override_with_reason_passes(guard, capsys, monkeypatch):
    monkeypatch.setenv("HF1_GUARD_OVERRIDE", "hot-fix CVE-2026-0001 per security incident")
    rc = guard.check_paths_and_report(["agents/solver.py"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "HF1 OVERRIDE active" in err
    assert "hot-fix CVE-2026-0001" in err
    assert "Local-only escape hatch" in err
    assert "FF-07" in err


def test_check_override_empty_reason_blocks(guard, capsys, monkeypatch):
    monkeypatch.setenv("HF1_GUARD_OVERRIDE", "")
    rc = guard.check_paths_and_report(["agents/solver.py"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "HF1 forbidden-zone violation" in err
    assert "OVERRIDE active" not in err


def test_check_override_whitespace_reason_blocks(guard, capsys, monkeypatch):
    monkeypatch.setenv("HF1_GUARD_OVERRIDE", "   \t  ")
    rc = guard.check_paths_and_report(["Dockerfile"])
    assert rc == 1


def test_check_lists_all_violations(guard, capsys, monkeypatch):
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.check_paths_and_report(["agents/solver.py", "schemas/sim_state.py", "Dockerfile"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "agents/solver.py" in err
    assert "schemas/sim_state.py" in err
    assert "Dockerfile" in err


# ---------------------------------------------------------------------------
# main() — git invocation contract (mocked)
# ---------------------------------------------------------------------------


def test_main_ignores_argv_paths_uses_git(guard, capsys, monkeypatch):
    """main() must NOT use argv for paths (pre-commit's filter would
    miss deletes/renames). It always reads from git."""
    captured = {}

    def fake_git_paths():
        captured["called"] = True
        return ["agents/solver.py"]

    monkeypatch.setattr(guard, "get_staged_paths", fake_git_paths)
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    # Pass argv that, if used, would NOT trigger a violation. But
    # main() must ignore argv and use git-supplied paths.
    rc = guard.main(["hf1_path_guard.py", "backend/app/main.py"])
    assert captured["called"] is True
    assert rc == 1  # because git supplied a zone path
    err = capsys.readouterr().err
    assert "agents/solver.py" in err


def test_main_no_staged_paths_returns_zero(guard, capsys, monkeypatch):
    monkeypatch.setattr(guard, "get_staged_paths", lambda: [])
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.main(["hf1_path_guard.py"])
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_main_git_returns_rename_caught(guard, capsys, monkeypatch):
    """Integration: git surfaces a rename of a zone path; main() must
    block (this is the BLOCKER scenario from R1)."""
    monkeypatch.setattr(
        guard,
        "get_staged_paths",
        lambda: ["agents/router.py", "agents/router_old.py"],
    )
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.main(["hf1_path_guard.py"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "agents/router.py" in err  # old path (in zone) flagged


def test_main_git_returns_delete_caught(guard, capsys, monkeypatch):
    """Integration: git surfaces a delete of a zone path; main() must block."""
    monkeypatch.setattr(guard, "get_staged_paths", lambda: ["agents/solver.py"])
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.main(["hf1_path_guard.py"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "agents/solver.py" in err


# ---------------------------------------------------------------------------
# --from-diff mode (CI invocation per AR-2026-04-25-001 §HF1 enforcement)
# ---------------------------------------------------------------------------


def test_main_from_diff_calls_get_paths_from_diff(guard, capsys, monkeypatch):
    """--from-diff <ref> mode must call get_paths_from_diff(ref), not
    get_staged_paths()."""
    captured: dict = {}

    def fake_from_diff(ref):
        captured["ref"] = ref
        return ["agents/router.py"]

    def fake_staged():
        captured["staged_called"] = True
        return []

    monkeypatch.setattr(guard, "get_paths_from_diff", fake_from_diff)
    monkeypatch.setattr(guard, "get_staged_paths", fake_staged)
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)

    rc = guard.main(["hf1_path_guard.py", "--from-diff", "origin/main"])
    assert captured.get("ref") == "origin/main"
    assert "staged_called" not in captured  # must NOT fall back to staged
    assert rc == 1  # zone path → block
    err = capsys.readouterr().err
    assert "agents/router.py" in err


def test_main_default_mode_uses_staged_not_diff(guard, capsys, monkeypatch):
    """Without --from-diff, must use get_staged_paths()."""
    captured: dict = {}

    monkeypatch.setattr(
        guard, "get_staged_paths", lambda: (captured.setdefault("staged", True), [])[1]
    )
    monkeypatch.setattr(
        guard,
        "get_paths_from_diff",
        lambda ref: (captured.setdefault("diff", True), [])[1],
    )
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)

    rc = guard.main(["hf1_path_guard.py"])
    assert captured.get("staged") is True
    assert "diff" not in captured  # CI mode must not fire
    assert rc == 0


def test_main_from_diff_clean_paths_pass(guard, capsys, monkeypatch):
    monkeypatch.setattr(
        guard,
        "get_paths_from_diff",
        lambda ref: ["backend/app/main.py", "docs/quickstart.md"],
    )
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = guard.main(["hf1_path_guard.py", "--from-diff", "origin/main"])
    assert rc == 0
    assert capsys.readouterr().err == ""
