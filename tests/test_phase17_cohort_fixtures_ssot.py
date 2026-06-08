"""FM-04a Phase 17 D — meta-test: cohort-fixture SSOT enforcement.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

The Phase 17 D SSOT consolidation hoists the 5-case cohort-fixture
seeding helpers (``make_stub_path`` / ``make_explicit_dynamics_healthy_input``
/ ``make_pv_case_input`` / ``make_clean_leak_case_input`` /
``make_regressed_leak_case_input``) to ``tests/_test_utils/cohort_fixtures.py``.

This meta-test enforces that no Phase 15+ journey test file re-inlines
those helper bodies — a future maintainer who copy-pastes an old
helper back into a journey file trips this audit.

Detection method: scan every ``tests/test_phase{N}_journey*.py`` and
``tests/test_phase{N}_*cohort_arc.py`` etc., parse its AST, and refuse
any module-level ``def`` whose name matches the canonical helper
pattern (``_stub_path`` / ``_healthy_case_input`` /
``_explicit_dynamics_healthy_input`` / ``_pv_case_input`` /
``_clean_leak_case_input`` / ``_regressed_leak_case_input``). The
SSOT module itself is explicitly excluded.

Anti-gaming pin (rubric §3.D · meta-audit):
* **M:-2 lexical detection**: any ``def`` matching the canonical
  helper-name set inside a Phase 15+ journey file is a re-inlining
  violation, regardless of the body's content.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"

# The 6 canonical helper names that MUST NOT be re-defined inside a
# Phase 15+ journey file. Each name maps to its SSOT counterpart in
# ``tests/_test_utils/cohort_fixtures.py``.
FORBIDDEN_HELPER_NAMES: frozenset[str] = frozenset(
    {
        "_stub_path",
        "_healthy_case_input",
        "_explicit_dynamics_healthy_input",
        "_pv_case_input",
        "_clean_leak_case_input",
        "_regressed_leak_case_input",
    }
)

# Files explicitly allowed to define helpers matching the forbidden
# pattern (currently empty — every journey file MUST delegate to the
# SSOT). Reserved for future explicit-opt-out cases.
EXEMPT_FILES: frozenset[str] = frozenset()

# The SSOT module itself defines helpers in the ``make_<name>`` form —
# the meta-test explicitly excludes the SSOT path.
SSOT_PATH = TESTS_DIR / "_test_utils" / "cohort_fixtures.py"


def _journey_test_files() -> list[Path]:
    """Return every Phase 15+ journey/cohort test file (cohort-fixture
    consumer set). Includes both `journey` and `cohort_arc` shapes
    (the latter pre-dates the journey naming convention)."""
    files: list[Path] = []
    for path in sorted(TESTS_DIR.glob("test_phase*.py")):
        if path == SSOT_PATH:
            continue
        name = path.name
        if name in EXEMPT_FILES:
            continue
        # Heuristic match: cohort fixture consumers are journey-shaped
        # tests OR cohort_arc-shaped tests (Phase 15 B).
        if "journey" in name or "cohort_arc" in name:
            files.append(path)
    return files


def test_cohort_fixture_consumer_files_exist() -> None:
    """Sanity: the consumer set is non-empty (post-Phase-17-D we have
    at least 7 consumer files across Phase 15-17)."""
    files = _journey_test_files()
    # 5 pre-existing (Phase 15 B/D × 2 + Phase 16 D × 2) + 2 new Phase 17 D
    assert len(files) >= 5, [p.name for p in files]


def _module_level_def_names(path: Path) -> set[str]:
    """Return the set of names of module-level ``def`` definitions in
    ``path``. AST-based — robust against comments and string-literal
    occurrences of the names."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_no_journey_file_redefines_canonical_cohort_helpers() -> None:
    """Per Phase 17 D SSOT consolidation: no Phase 15+ journey or
    cohort_arc test file may re-inline any of the 6 canonical
    cohort-fixture helper names. The SSOT lives in
    ``tests/_test_utils/cohort_fixtures.py``.

    Future maintainers: if you need a divergent variant of one of
    these helpers, add a kwarg to the SSOT helper (see
    ``make_regressed_leak_case_input.drop_optional_artifacts`` for an
    example) and update this test's expectation. Do NOT redefine the
    helper locally.
    """
    offenders: list[tuple[str, list[str]]] = []
    for path in _journey_test_files():
        local_defs = _module_level_def_names(path)
        hits = sorted(local_defs & FORBIDDEN_HELPER_NAMES)
        if hits:
            offenders.append((path.name, hits))
    assert not offenders, (
        "Phase 17 D SSOT violation — the following journey files "
        "re-inline canonical cohort-fixture helpers (must import from "
        "tests/_test_utils/cohort_fixtures.py instead):\n"
        + "\n".join(f"  * {name}: {hits}" for name, hits in offenders)
    )


def test_ssot_module_exists_and_exports_canonical_helpers() -> None:
    """The SSOT module must exist and export every canonical
    ``make_<helper>`` variant the consumers depend on."""
    assert SSOT_PATH.is_file(), SSOT_PATH
    src = SSOT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    defs = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    expected = {
        "make_stub_path",
        "make_explicit_dynamics_healthy_input",
        "make_pv_case_input",
        "make_clean_leak_case_input",
        "make_regressed_leak_case_input",
    }
    missing = expected - defs
    assert not missing, f"SSOT module missing helpers: {sorted(missing)}"


def test_phase17_d_journey_files_import_from_ssot() -> None:
    """The 2 Phase 17 D journey files MUST import from
    ``tests._test_utils.cohort_fixtures`` (positive-presence sanity
    check; complements the negative-absence test above)."""
    phase17_journey_files = sorted(TESTS_DIR.glob("test_phase17_journey_*.py"))
    # At minimum: five-drift-views + cumulative-coherence
    assert len(phase17_journey_files) >= 2, [p.name for p in phase17_journey_files]
    for path in phase17_journey_files:
        src = path.read_text(encoding="utf-8")
        assert "tests._test_utils.cohort_fixtures" in src, (
            f"Phase 17 D journey file {path.name} does not import from the "
            f"cohort-fixture SSOT module"
        )
