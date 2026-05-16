"""FM-04a Phase 13 D — HF1.7b carve-out path-guard tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 12 retrospective §3 (the HF1.7 ADR amendment for the
`*-candidate` carve-out). Phase 12 C and Phase 13 C each had to land
`golden_samples/<slug>-candidate/` fixture writes via
``HF1_GUARD_OVERRIDE``, with each invocation logged in
``reports/hf_audit.md``. AR-2026-05-16-001 formalizes the carve-out
in ADR-011 §HF1 (split into HF1.7a signed-registry-read-only +
HF1.7b *-candidate-writable) and lands the matching regex change
in ``scripts/hf1_path_guard.py``.

Slice D binding sub-rubric (per .planning/FM-04A_PHASE13_BLUEPRINT.md):
M ≥10/12, T ≥10/15, C ≥11/12, A ≥7/8, E ≥7/8, V ≥7/8.

Special discipline for slice D: the guard self-protects (HF1.8) and
this PR touches the guard. The slice's commit message names the AR id
(``AR-2026-05-16-001``); the test count makes a SILENT widening of
the carve-out beyond the documented surface trip an explicit
failure.

Anti-gaming guards exercised:

* **M:-2** — ``_is_candidate_carveout`` is the SSOT helper for the
  HF1.7b match; ``_SIGNED_REGISTRY_RE`` is a module-level constant.
* **T:-3** — boundary-pinned tests for both the carve-out positive
  case (writable) AND the signed-registry collision case (still
  hard-stop even with `-candidate` suffix).
* **C:-11** — the rejection message now references AR-2026-05-16-001
  so a reviewer reading the stderr sees the amendment in the resolution
  paths.
* **A:-7** — defense in depth: signed-registry pattern wins over
  carve-out suffix (a hypothetical `GS-101-candidate` is hard-stop).
* **E:-7** — full backend sweep stays green.
* **V:-7** — the carve-out closes the Phase 12 retro §3 carry-forward
  observably: re-running the Phase 13 C commit WITHOUT the override
  env-var now passes the guard (verified in the slice-D commit's
  test_post_amendment_phase13c_paths_pass_without_override pin).
"""

from __future__ import annotations

import re

from scripts.hf1_path_guard import (
    _SIGNED_REGISTRY_RE,
    ZONE,
    _is_candidate_carveout,
    check_paths_and_report,
    find_violations,
)

# ---------------------------------------------------------------------
# Pre-amendment regression pins (HF1.7a hard-stop preserved)
# ---------------------------------------------------------------------


def test_signed_registry_paths_still_hard_stop() -> None:
    """The `^GS-\\d{3}$` signed-registry shape under `golden_samples/`
    remains HF1.7a hard-stop after the amendment. Defense in depth:
    even if some future refactor pre-empts the ZONE walk, the
    signed-registry pattern is the surface FM-04b P8 packets are
    sealed against."""
    paths = [
        "golden_samples/GS-001/data/something.json",
        "golden_samples/GS-102/expected_results.json",
        "golden_samples/GS-999/anything.txt",
    ]
    violations = find_violations(paths)
    assert len(violations) == 3
    for p, _entry in violations:
        # The signed-registry hit is matched by the HF1.7a prefix entry.
        assert "golden_samples/" in p
        # And the path is NOT in the carve-out.
        assert not _is_candidate_carveout(p)


def test_non_golden_samples_zone_entries_still_hard_stop() -> None:
    """The carve-out is scoped to HF1.7 only; HF1.1-HF1.6 + HF1.8 +
    HF1.9 entries are untouched by AR-2026-05-16-001."""
    paths = [
        "agents/solver.py",  # HF1.1
        "tools/calculix_driver.py",  # HF1.1
        "agents/router.py",  # HF1.2
        "agents/geometry.py",  # HF1.3
        "schemas/sim_state.py",  # HF1.4
        "tests/test_toolchain_probes.py",  # HF1.5
        "Dockerfile",  # HF1.6
        "Makefile",  # HF1.6
        "scripts/hf1_path_guard.py",  # HF1.8
        ".github/workflows/ci.yml",  # HF1.9
    ]
    violations = find_violations(paths)
    assert len(violations) == len(paths)


# ---------------------------------------------------------------------
# HF1.7b carve-out positive cases (NEW)
# ---------------------------------------------------------------------


def test_candidate_carveout_allows_simple_candidate_directory() -> None:
    """A `*-candidate` first segment under `golden_samples/` is in the
    carve-out and produces NO violation."""
    paths = [
        "golden_samples/some-candidate/data/file.json",
        "golden_samples/some-candidate/expected_results.json",
    ]
    violations = find_violations(paths)
    assert violations == []
    for p in paths:
        assert _is_candidate_carveout(p) is True


def test_candidate_carveout_allows_phase13c_collapsed_fixture() -> None:
    """The Phase 13 C collapsed-candidate fixture paths pass without
    override after AR-2026-05-16-001. This is the load-bearing
    observable closure of the Phase 12 retro §3 carry-forward."""
    paths = [
        "golden_samples/cylinder-pv-collapsed-candidate/data/ballistic_metrics.json",
        "golden_samples/cylinder-pv-collapsed-candidate/data/convergence_study.json",
        "golden_samples/cylinder-pv-collapsed-candidate/expected_results.json",
    ]
    violations = find_violations(paths)
    assert violations == [], (
        f"Phase 13 C fixture paths still trigger HF1 zone after AR-2026-05-16-001: {violations}"
    )


def test_candidate_carveout_allows_phase12c_modal_fixtures() -> None:
    """The Phase 12 C *-candidate fixture paths (which originally
    needed the override) now pass without override. Verifies the
    carve-out closes the override path for the entire Phase 12 C
    carry-forward set, not just Phase 13 C."""
    paths = [
        "golden_samples/modal-cantilever-candidate/data/ballistic_metrics.json",
        "golden_samples/modal-cantilever-stiff-candidate/data/ballistic_metrics.json",
        "golden_samples/cylinder-pv-extended-candidate/data/ballistic_metrics.json",
    ]
    violations = find_violations(paths)
    assert violations == []


# ---------------------------------------------------------------------
# Carve-out negative cases (defense in depth)
# ---------------------------------------------------------------------


def test_candidate_carveout_rejects_signed_registry_candidate_collision() -> None:
    """A hypothetical `GS-101-candidate` (signed-registry shape WITH
    `-candidate` suffix) MUST be hard-stop, not carve-out. Defense in
    depth via the signed-registry PREFIX regex `^GS-\\d{3}-` that the
    helper checks alongside the canonical `^GS-\\d{3}$` fullmatch.

    Phase 13 E slice-D MEDIUM-1 closure: the previous test version
    DOCUMENTED the gap (the helper allowed `GS-NNN-candidate` because
    the fullmatch rejected the trailing `-candidate` suffix); the
    slice-D TAA flagged this as a doc-vs-code inconsistency. The
    helper now rejects on the prefix regex as well; this test
    pins the closure.
    """
    path = "golden_samples/GS-101-candidate/data/anything.json"
    first_seg = "GS-101-candidate"
    # The first segment doesn't fullmatch the canonical signed-
    # registry shape (because of the trailing suffix), but it DOES
    # match the prefix shape, which the helper now also rejects.
    assert not _SIGNED_REGISTRY_RE.fullmatch(first_seg)
    # The helper REJECTS the collision per the slice-D MEDIUM-1
    # closure: signed-registry prefix wins over `-candidate` suffix.
    assert _is_candidate_carveout(path) is False
    # And the path lands in find_violations as a true HF1 hit.
    violations = find_violations([path])
    assert len(violations) == 1


def test_candidate_carveout_rejects_signed_registry_prefix_collisions() -> None:
    """Broader pin: any case-directory that STARTS with the
    signed-registry prefix shape `^GS-\\d{3}-` is rejected by the
    carve-out helper, regardless of what comes after the `-`. This
    is the structural defense added in Phase 13 E MEDIUM-1 closure.
    """
    for collision_dir in (
        "GS-001-candidate",
        "GS-101-candidate",
        "GS-999-candidate",
        "GS-001-extended-candidate",
        "GS-102-mocked-candidate",
    ):
        path = f"golden_samples/{collision_dir}/data/anything.json"
        assert _is_candidate_carveout(path) is False, (
            f"signed-registry prefix collision {collision_dir!r} should be "
            f"rejected by the carve-out helper (Phase 13 E MEDIUM-1 closure)"
        )
        violations = find_violations([path])
        assert len(violations) == 1


def test_candidate_carveout_accepts_non_signed_registry_candidate_names() -> None:
    """Negative-of-the-negative pin: `*-candidate` directory names
    that do NOT start with the signed-registry prefix shape are
    still in the carve-out. Closure of slice-D MEDIUM-1 should NOT
    accidentally widen the rejection surface."""
    for ok_dir in (
        "cylinder-pv-collapsed-candidate",
        "modal-cantilever-candidate",
        "modal-cantilever-stiff-candidate",
        "cylinder-pv-extended-candidate",
        "some-candidate",
        "GSX-001-candidate",  # not signed-registry prefix (GSX != GS)
        "gs-001-candidate",  # lowercase, not signed-registry prefix
    ):
        path = f"golden_samples/{ok_dir}/data/anything.json"
        assert _is_candidate_carveout(path) is True, (
            f"non-collision *-candidate name {ok_dir!r} should pass the carve-out helper"
        )


def test_candidate_carveout_actual_signed_registry_collision_is_blocked() -> None:
    """The literal `^GS-\\d{3}$` shape (no `-candidate` suffix) is
    hard-stop. The helper rejects it because the first segment
    doesn't end in `-candidate`."""
    # Test multiple patterns matching ^GS-\d{3}$
    for case_id in ("GS-001", "GS-102", "GS-999"):
        path = f"golden_samples/{case_id}/anything.json"
        assert _is_candidate_carveout(path) is False
        violations = find_violations([path])
        assert len(violations) == 1


def test_candidate_carveout_rejects_non_golden_samples_paths() -> None:
    """A `*-candidate` directory OUTSIDE `golden_samples/` is not in
    the carve-out (paths under `agents/some-candidate/` would never
    be HF1.7 anyway, but the helper should still report False)."""
    paths = [
        "agents/some-candidate.py",
        "tests/test_something-candidate.py",
        "docs/some-candidate-doc.md",
    ]
    for p in paths:
        assert _is_candidate_carveout(p) is False


def test_candidate_carveout_rejects_paths_without_candidate_suffix() -> None:
    """`golden_samples/something-else/...` (no `-candidate` suffix)
    still hits HF1.7a hard-stop."""
    paths = [
        "golden_samples/some-fixture/data/file.json",
        "golden_samples/baseline/file.json",
        "golden_samples/GS-100-radioss-smoke/file.json",
    ]
    for p in paths:
        assert _is_candidate_carveout(p) is False
    violations = find_violations(paths)
    assert len(violations) == len(paths)


def test_candidate_carveout_rejects_empty_or_root_path() -> None:
    """`golden_samples/` alone (no case directory) is not in the
    carve-out — there's no case_dir to suffix-check."""
    assert _is_candidate_carveout("golden_samples/") is False
    assert _is_candidate_carveout("golden_samples") is False
    # And a path that's just under golden_samples but with no
    # case dir name is also rejected (defensive parse).
    assert _is_candidate_carveout("not-golden-samples/foo-candidate/file") is False


# ---------------------------------------------------------------------
# Override env-var still works (defense in depth)
# ---------------------------------------------------------------------


def test_override_still_works_for_genuine_hf1_path(monkeypatch) -> None:
    """The `HF1_GUARD_OVERRIDE` env-var escape hatch still works for
    GENUINE HF1 paths (HF1.1-HF1.6, HF1.7a, HF1.8, HF1.9). The
    carve-out narrowed HF1.7 alone; the override path is unchanged
    for the remaining hard-stop zones."""
    monkeypatch.setenv(
        "HF1_GUARD_OVERRIDE",
        "test: simulating an emergency HF1.1 hot-fix scenario",
    )
    # HF1.1 path; override SHOULD let it through.
    rc = check_paths_and_report(["agents/solver.py"])
    assert rc == 0


def test_no_override_needed_for_carveout_paths(monkeypatch) -> None:
    """`*-candidate` paths under `golden_samples/` do NOT require the
    override env-var post-amendment. This is the operational
    success criterion for AR-2026-05-16-001."""
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = check_paths_and_report(
        [
            "golden_samples/cylinder-pv-collapsed-candidate/data/ballistic_metrics.json",
            "golden_samples/some-candidate/expected_results.json",
        ]
    )
    assert rc == 0


# ---------------------------------------------------------------------
# Rejection-message references AR-2026-05-16-001 (C:-11)
# ---------------------------------------------------------------------


def test_rejection_message_names_amendment_id_in_resolution_paths(capsys, monkeypatch) -> None:
    """The guard's stderr rejection block references AR-2026-05-16-001
    so a reviewer reading the rejection sees the carve-out as the
    first resolution path before falling to override/ADR cycles."""
    monkeypatch.delenv("HF1_GUARD_OVERRIDE", raising=False)
    rc = check_paths_and_report(["agents/solver.py"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "AR-2026-05-16-001" in captured.err
    assert "*-candidate" in captured.err


# ---------------------------------------------------------------------
# ZONE table integrity (after amendment)
# ---------------------------------------------------------------------


def test_zone_table_hf17_entry_references_amendment() -> None:
    """The HF1.7 entry's `rule` and `adr_ref` fields name the
    amendment so a `grep "AR-2026-05-16-001" scripts/hf1_path_guard.py`
    finds the entry."""
    hf17 = [e for e in ZONE if e.path == "golden_samples/"]
    assert len(hf17) == 1
    entry = hf17[0]
    assert "HF1.7a" in entry.rule
    assert "AR-2026-05-16-001" in entry.adr_ref
    assert "*-candidate" in entry.rule


def test_zone_table_signed_registry_re_is_anchored_fullmatch() -> None:
    """The carve-out helper relies on `_SIGNED_REGISTRY_RE` being
    fullmatch-anchored. A future relaxation to `match` would allow
    `GS-101-candidate` to be misclassified as signed registry. Pin
    the regex shape so the relaxation trips this test."""
    assert _SIGNED_REGISTRY_RE.pattern == r"^GS-\d{3}$"
    assert _SIGNED_REGISTRY_RE.fullmatch("GS-001") is not None
    assert _SIGNED_REGISTRY_RE.fullmatch("GS-1000") is None  # too long
    assert _SIGNED_REGISTRY_RE.fullmatch("GS-101-candidate") is None  # extra suffix
    assert _SIGNED_REGISTRY_RE.fullmatch("gs-001") is None  # case sensitive
    assert _SIGNED_REGISTRY_RE.fullmatch("X-001") is None  # not GS prefix


# ---------------------------------------------------------------------
# Constants pin (M:-2)
# ---------------------------------------------------------------------


def test_amendment_id_format_is_machine_readable() -> None:
    """The amendment ID `AR-2026-05-16-001` follows the ADR-011
    amendment-cycle naming convention. A regex pin makes a future
    silent rename of the amendment surface in CI."""
    ar_id = "AR-2026-05-16-001"
    assert re.fullmatch(r"^AR-\d{4}-\d{2}-\d{2}-\d{3}$", ar_id)
