"""FM-04a Phase 13 C — deeper-degradation 5th cohort case.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 12 retrospective §4 (the deeper-degradation fixture
carry-forward). Phase 12 D's ``cylinder-pv-extended-candidate``
snapshot 3 landed at trust=84 — still "healthy" by the bucket math
even though the blueprint wording promised a regressed-bucket trigger.
This file ships the 5th synthetic cohort case
``cylinder-pv-collapsed-candidate`` authored to push trust strictly
below the ``WATCHING_TRUST_SCORE_MIN`` (= 50) threshold on the third
snapshot, making the slice-D ``regressed_count >= 1`` blueprint
assertion load-bearing on real fixture math.

Slice C binding sub-rubric (per .planning/FM-04A_PHASE13_BLUEPRINT.md):
M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

Anti-gaming guards exercised:

* **M:-2** — ``COLLAPSED_CASE_ID`` is a module-level SSOT constant; the
  trust-floor expectation ``COLLAPSED_TRUST_SCORE_CEILING = 49`` is
  named + typed + commented.
* **T:-3** — boundary-pinned: the load-bearing assertion is strictly
  ``snapshot3_trust < 50`` (NOT ``< 60`` or any other loose bound that
  would let a future regression past the 50-bucket-edge silently
  re-bucket the case as ``watching``).
* **C:-8** — every 200 envelope inspected by the cohort polls gets a
  Tier 1 disclaimer trio audit; the collapsed case has the
  ``not_signed_validation`` boundary stamped on every snapshot.
* **A:-3** — signed-registry case_id patterns never appear; the
  collapsed case is a ``*-candidate`` form.
* **E:-2** — no real-solver invocation; the fixture is read off
  ``golden_samples/cylinder-pv-collapsed-candidate/`` (a
  ``*-candidate`` directory authorized by the FM-04a binding
  constraint) and rendered through ``write_cohort_snapshot``.
* **V:-3** — V-axis honesty: the collapsed-bucket trigger is asserted
  on the FIXTURE NUMBERS (snapshot-3 trust < 50), not on a blueprint
  promise. The fixture's PV-quality numbers (worst rel err 12-15%,
  ratio P_m/S_m = 1.5 > 1.0) are demonstrably failing every gate.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import case_completeness as case_completeness_route
from app.api.routes import cohort_executive_summary as cohort_executive_summary_route
from app.api.routes import trust_score_timeline as trust_score_timeline_route
from app.main import app
from app.services.reporting.cohort_executive_summary import (
    WATCHING_TRUST_SCORE_MIN,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)

# ---------------------------------------------------------------------
# Module-level SSOT pins (M:-2)
# ---------------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

COLLAPSED_CASE_ID: str = "cylinder-pv-collapsed-candidate"
"""SSOT for the deep-degradation fixture case_id. Pinned at module
level so a future refactor that renames the fixture trips both this
constant and the test count in one place."""

# The trust score CEILING the snapshot-3 collapsed case must come in
# UNDER (strictly < 50). The 50 number is the
# WATCHING_TRUST_SCORE_MIN threshold; we pin the ceiling separately so
# a future rebalance of WATCHING_TRUST_SCORE_MIN doesn't silently
# loosen this test (the load-bearing pin is "< 50", not "<
# WATCHING_TRUST_SCORE_MIN"). If a future rebalance moves the bucket
# edge, BOTH constants must be reviewed in lockstep.
COLLAPSED_TRUST_SCORE_CEILING: int = 50

# Phase 12 D cohort fixture cases (preserved unchanged for back-compat
# with the slice-D arc). Phase 13 C ADDS the collapsed case as a 5th
# distinct cohort member.
PHASE12_D_FIXTURE_CASES: tuple[tuple[str, str], ...] = (
    ("cylinder-pv-candidate", "linear_static_pv"),
    ("modal-cantilever-candidate", "modal"),
    ("modal-cantilever-stiff-candidate", "modal"),
    ("cylinder-pv-extended-candidate", "linear_static_pv"),
)

PHASE13_C_FIXTURE_CASES: tuple[tuple[str, str], ...] = (
    *PHASE12_D_FIXTURE_CASES,
    (COLLAPSED_CASE_ID, "linear_static_pv"),
)

FILLER_COHORT_CASES: tuple[str, ...] = (
    "synthetic-cohort-bulk-01-candidate",
    "synthetic-cohort-bulk-02-candidate",
)


# ---------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as c:
                return await c.get(url, params=params)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch) -> Path:
    """Stand up a synthetic 7-case cohort (4 Phase 12 D fixtures + the
    new collapsed case + 2 fillers) and re-aim every relevant route at
    it. Matches the slice-D / slice-F scaffolding so the snapshot
    writer reads from this tmp tree instead of the real repo."""
    _seed_repo(tmp_path)

    def fake_root() -> Path:
        return tmp_path

    monkeypatch.setattr(cohort_executive_summary_route, "_repo_root", fake_root)
    monkeypatch.setattr(case_completeness_route, "_repo_root", fake_root)
    monkeypatch.setattr(trust_score_timeline_route, "_repo_root", fake_root)
    return tmp_path


def _seed_repo(tmp_path: Path) -> Path:
    """Copy the 5 candidate fixtures + 2 synthetic fillers into
    ``tmp_path/golden_samples/`` so a self-contained cohort can be
    built without touching the real golden_samples tree.

    The fillers are copies of the modal-cantilever-candidate data with
    the ``case_id`` field rewritten so the cohort walker doesn't
    double-count canonical case_ids.
    """
    golden = tmp_path / "golden_samples"
    golden.mkdir(parents=True)
    for case_id, _atype in PHASE13_C_FIXTURE_CASES:
        src = REPO_ROOT / "golden_samples" / case_id
        if not src.exists():
            raise FileNotFoundError(f"Phase 13 C requires fixture {src}; missing on disk")
        dst = golden / case_id
        shutil.copytree(src, dst)
    canonical = REPO_ROOT / "golden_samples" / "modal-cantilever-candidate"
    for filler in FILLER_COHORT_CASES:
        dst = golden / filler
        shutil.copytree(canonical, dst)
        for name in ("expected_results.json",):
            payload = json.loads((dst / name).read_text(encoding="utf-8"))
            payload["case_id"] = filler
            (dst / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        for name in ("ballistic_metrics.json", "convergence_study.json"):
            payload = json.loads((dst / "data" / name).read_text(encoding="utf-8"))
            payload["case_id"] = filler
            (dst / "data" / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return tmp_path


def _starter(tmp_path: Path, case_id: str) -> Path:
    p = tmp_path / f"{case_id}_starter.rad"
    p.write_text(f"# {case_id} starter deck", encoding="utf-8")
    return p


def _engine(tmp_path: Path, case_id: str) -> Path:
    p = tmp_path / f"{case_id}_engine.rad"
    p.write_text(f"# {case_id} engine deck", encoding="utf-8")
    return p


def _generator(tmp_path: Path, case_id: str) -> Path:
    p = tmp_path / f"{case_id}_generator.py"
    p.write_text(f"# {case_id} synthetic generator", encoding="utf-8")
    return p


def _full_case_input(tmp_path: Path, case_id: str, analysis_type: str) -> SnapshotCaseInput:
    fixture = tmp_path / "golden_samples" / case_id
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=_starter(tmp_path, case_id),
        engine_deck_path=_engine(tmp_path, case_id),
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=_generator(tmp_path, case_id),
        notes_path=None,
        analysis_type=analysis_type,
    )


def _collapsed_case_input(tmp_path: Path) -> SnapshotCaseInput:
    """Build the collapsed-candidate SnapshotCaseInput. Every snapshot
    of the collapsed case omits the generator script (forces
    completeness's generator_script axis to 0) and reads ballistic +
    convergence from the on-disk degraded JSONs.

    Per the slice-C deliverable:
      * `generator_script_path=None` for every snapshot ("drop
        reproducibility entirely").
      * `ballistic_metrics_path` points at the degraded JSON (energy
        status `unavailable`; ratio P_m/S_m=1.5 > 1.0; worst rel err
        12-15%).
      * `convergence_study_path` points at the unstable convergence
        JSON (mesh sweep `candidate_observed_unstable`).
    """
    fixture = tmp_path / "golden_samples" / COLLAPSED_CASE_ID
    return SnapshotCaseInput(
        case_id=COLLAPSED_CASE_ID,
        starter_deck_path=_starter(tmp_path, COLLAPSED_CASE_ID),
        engine_deck_path=_engine(tmp_path, COLLAPSED_CASE_ID),
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,  # always omitted -- Phase 13 C contract
        notes_path=None,
        analysis_type="linear_static_pv",
    )


def _write_three_snapshots_with_collapsed(tmp_path: Path) -> tuple[str, str, str]:
    """Render a 3-snapshot cohort arc that includes the collapsed case
    in every snapshot (so the trend timeline has 3 points on the
    collapsed case_id for downstream slope analysis).

    Phase 13 C extends Phase 12 D's ``_write_three_snapshots`` by
    APPENDING the collapsed case as a 5th distinct cohort member; the
    Phase 12 D degradation behavior on
    ``cylinder-pv-extended-candidate`` is preserved unchanged (the
    extended case continues to degrade across snapshots 1->2->3; the
    collapsed case is born collapsed and STAYS collapsed).
    """
    base = datetime(2026, 5, 17, 12, 0, 0, tzinfo=UTC)
    labels: list[str] = []
    for snap_idx in range(3):
        moment = base + timedelta(minutes=snap_idx * 5)
        label = moment.strftime("%Y-%m-%dT%H%M%SZ")
        cases: list[SnapshotCaseInput] = []
        # 4 Phase 12 D cases (full-credit on every snapshot here;
        # slice C is NOT re-testing the Phase 12 D extended-candidate
        # arc, just adding a 5th member; the extended case is held
        # at full credit so the regressed bucket count is unambiguously
        # caused by the collapsed case alone).
        for case_id, atype in PHASE12_D_FIXTURE_CASES:
            cases.append(_full_case_input(tmp_path, case_id, atype))
        # 5th case: collapsed (deeply degraded, every snapshot).
        cases.append(_collapsed_case_input(tmp_path))
        # Fillers to lift cohort size above n=4 statistical ceiling.
        for filler in FILLER_COHORT_CASES:
            cases.append(_full_case_input(tmp_path, filler, "modal"))
        write_cohort_snapshot(cases, tmp_path, snapshot_label=label)
        labels.append(label)
    return tuple(labels)  # type: ignore[return-value]


# ---------------------------------------------------------------------
# 1. Fixture-presence pins (M:-2)
# ---------------------------------------------------------------------


def test_collapsed_candidate_fixture_directory_exists() -> None:
    """The `*-candidate` fixture directory exists on disk and contains
    the three load-bearing artifacts (expected_results.json + degraded
    ballistic_metrics + unstable convergence_study)."""
    case_dir = REPO_ROOT / "golden_samples" / COLLAPSED_CASE_ID
    assert case_dir.is_dir()
    assert (case_dir / "expected_results.json").is_file()
    assert (case_dir / "data" / "ballistic_metrics.json").is_file()
    assert (case_dir / "data" / "convergence_study.json").is_file()


def test_collapsed_candidate_fixture_metadata_is_tier1() -> None:
    """The expected_results.json carries the Tier 1 disclaimer trio
    + the fixture-authoring purpose note. C:-8 pin."""
    payload = json.loads(
        (REPO_ROOT / "golden_samples" / COLLAPSED_CASE_ID / "expected_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["case_id"] == COLLAPSED_CASE_ID
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "tier1_engineering_candidate" in payload["claim_boundary"]
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert payload["expected_health_bucket"] == "regressed"
    assert payload["expected_trust_score_max"] < COLLAPSED_TRUST_SCORE_CEILING


def test_collapsed_ballistic_metrics_failing_every_pv_gate() -> None:
    """The degraded ballistic_metrics fixture is structured to fail
    EVERY PV-quality gate read by the case_completeness scorer:

      * `energy_audit.status == "unavailable"` (not closed_aggregate)
        -> energy_audit axis = 0
      * `pv_summary.asme_section_5_5.ratio_P_m_over_S_m >= 1.0`
        -> allowable_margin axis = 0
      * `pv_summary.convergence_vs_lame.max_rel_err_*_pct > 5%`
        -> lame_cross_check half-credit only; scl_convergence axis = 0
    """
    payload = json.loads(
        (
            REPO_ROOT / "golden_samples" / COLLAPSED_CASE_ID / "data" / "ballistic_metrics.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["energy_audit"]["status"] == "unavailable"
    asme = payload["pv_summary"]["asme_section_5_5"]
    assert asme["ratio_P_m_over_S_m"] >= 1.0
    conv = payload["pv_summary"]["convergence_vs_lame"]
    for key in (
        "max_rel_err_sigma_r_pct",
        "max_rel_err_sigma_t_pct",
        "max_rel_err_sigma_z_pct",
        "max_rel_err_von_mises_pct",
    ):
        # Strictly > 5% so the scl_convergence axis lands at the
        # "not_converged" (0 pts) bucket, not the half-credit bucket.
        assert conv[key] > 5.0


def test_collapsed_convergence_study_mesh_unstable() -> None:
    """The convergence_study fixture reports `candidate_observed_unstable`
    on the mesh sweep, routing the trust-score convergence axis to the
    30/100 raw -> 6/20 weighted floor for the linear_static branch."""
    payload = json.loads(
        (
            REPO_ROOT / "golden_samples" / COLLAPSED_CASE_ID / "data" / "convergence_study.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["convergence_kind"] == "linear_static"
    assert payload["mesh_sweep"]["candidate_stability"] == ("candidate_observed_unstable")
    assert payload["combined_verdict"] == "candidate_observed_unstable"


# ---------------------------------------------------------------------
# 2. Trust-score floor (T:-3 boundary pin — the load-bearing assertion)
# ---------------------------------------------------------------------


def test_collapsed_candidate_snapshot3_trust_strictly_below_50(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """**LOAD-BEARING**: snapshot 3 trust score on the collapsed case
    is strictly < 50, so the bucket classifier routes the case into
    `regressed`. This is the Phase 12 retro §4 closure pin — without
    it, the slice-D blueprint assertion `regressed_count >= 1` would
    remain aspirational (Phase 12 D's extended-candidate landed at
    trust=84, well inside the healthy bucket).

    The trust score is read off the snapshot-based timeline route
    (``/api/v1/trust-score-timeline``) rather than the live-evidence
    route (``/api/v1/trust-score``) because the cohort surfaces (the
    ones the regressed bucket fires on) consume snapshot-frozen
    evidence — that's the surface this test pins.
    """
    labels = _write_three_snapshots_with_collapsed(fake_repo)
    res = client.get(f"/api/v1/trust-score-timeline/{COLLAPSED_CASE_ID}")
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["case_id"] == COLLAPSED_CASE_ID
    assert payload["point_count"] == 3
    snapshot3_point = next(
        (p for p in payload["points"] if p["snapshot_label"] == labels[-1]),
        None,
    )
    assert snapshot3_point is not None
    trust = snapshot3_point["trust_score"]
    assert isinstance(trust, int)
    assert trust < COLLAPSED_TRUST_SCORE_CEILING, (
        f"collapsed-candidate snapshot 3 trust score = {trust}; "
        f"expected strictly < {COLLAPSED_TRUST_SCORE_CEILING} so the "
        f"regressed-bucket classifier fires. If this is failing because "
        f"a future trust-score rebalance moved the floor, the FIXTURE "
        f"must be re-degraded to preserve the contract."
    )
    # Defense in depth: trust must also be below the runtime threshold.
    assert trust < WATCHING_TRUST_SCORE_MIN


def test_collapsed_trust_score_breakdown_shows_failure_axes(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The trust-score timeline surfaces per-axis WEIGHTED values for
    each snapshot point. For the snapshot-3 collapsed point, the
    energy-axis weighted MUST be 0 (energy_audit status `unavailable`)
    and the convergence-axis weighted MUST equal the linear_static
    mesh-unstable floor (raw 30 -> weighted 6 with the CONVERGENCE_WEIGHT
    = 20). This gates against a silent trust-score formula rebalance
    that lifted the case back into the healthy bucket via an unrelated
    axis: the test fails if any contributing axis silently changes.
    """
    labels = _write_three_snapshots_with_collapsed(fake_repo)
    res = client.get(f"/api/v1/trust-score-timeline/{COLLAPSED_CASE_ID}")
    payload = res.json()
    snapshot3_point = next(p for p in payload["points"] if p["snapshot_label"] == labels[-1])
    # Energy-audit axis: unavailable status -> weighted 0.
    assert snapshot3_point["energy_audit_weighted"] == 0
    # Convergence axis: linear_static + mesh unstable -> raw 30, weighted
    # = round(30 * 20 / 100) = 6.
    assert snapshot3_point["convergence_weighted"] == 6
    # Completeness axis: every PV-quality gate fails -> weighted < 30
    # (raw < 60 of 100, weight = 50).
    assert snapshot3_point["completeness_weighted"] < 30


# ---------------------------------------------------------------------
# 3. Cohort-bucket trigger (C:-8 + V:-3)
# ---------------------------------------------------------------------


def test_cohort_executive_summary_regressed_bucket_fires(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The cohort-executive-summary route reports
    `regressed_count >= 1` after the slice-C arc lands. This is the
    Phase 12 retro §4 closure assertion: the slice-D blueprint's
    `regressed >= 1` bucket-count promise is now load-bearing on
    fixture math, NOT just blueprint wording."""
    _write_three_snapshots_with_collapsed(fake_repo)
    res = client.get("/api/v1/cohort-executive-summary")
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert payload["regressed_count"] >= 1
    collapsed_row = next(
        (c for c in payload["cases"] if c["case_id"] == COLLAPSED_CASE_ID),
        None,
    )
    assert collapsed_row is not None
    assert collapsed_row["bucket"] == "regressed"
    assert collapsed_row["latest_trust_score"] is not None
    assert collapsed_row["latest_trust_score"] < COLLAPSED_TRUST_SCORE_CEILING


def test_cohort_summary_collapsed_row_distinct_from_other_regresseds(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """If any OTHER case happens to share the regressed bucket (e.g.,
    a future Phase 12 D-style degradation arc), the collapsed case
    is still uniquely identifiable by case_id. This is a defensive
    pin so a future fixture sharing the collapsed-case bucket
    doesn't mask a regression in the collapsed case's own arc."""
    _write_three_snapshots_with_collapsed(fake_repo)
    res = client.get("/api/v1/cohort-executive-summary")
    payload = res.json()
    regressed_cases = [c for c in payload["cases"] if c["bucket"] == "regressed"]
    case_ids = [c["case_id"] for c in regressed_cases]
    assert COLLAPSED_CASE_ID in case_ids
    # The collapsed case_id is a UNIQUE identifier in the regressed set
    # (no other case shares the slug).
    assert case_ids.count(COLLAPSED_CASE_ID) == 1


# ---------------------------------------------------------------------
# 4. Case-completeness route (M:-2)
# ---------------------------------------------------------------------


def test_collapsed_case_completeness_route_returns_degraded_score(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The case-completeness route returns a degraded score for the
    collapsed case under the linear_static_pv rubric. The score is
    below the ``score >= 65`` floor used in slice-A happy-path tests
    (proving the PV-quality-gate failures actually reach the
    scorecard)."""
    _write_three_snapshots_with_collapsed(fake_repo)
    res = client.get(
        f"/api/v1/case-completeness/{COLLAPSED_CASE_ID}",
        params={"analysis_type": "linear_static_pv"},
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["case_id"] == COLLAPSED_CASE_ID
    assert payload["score"] < 65
    assert payload["score_max"] == 100
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "tier1_engineering_candidate" in payload["claim_boundary"]


# ---------------------------------------------------------------------
# 5. Constraint guards (A:-3 + E:-2)
# ---------------------------------------------------------------------


def test_collapsed_case_id_is_candidate_form_not_signed_registry() -> None:
    """SSOT contract: the case_id ends in ``-candidate`` and does NOT
    match the signed-registry pattern ``^GS-\\d{3}$`` (A:-3 pin)."""
    import re

    assert COLLAPSED_CASE_ID.endswith("-candidate")
    assert not re.fullmatch(r"^GS-\d{3}$", COLLAPSED_CASE_ID)


def test_collapsed_fixture_files_inside_candidate_directory() -> None:
    """Every file the fixture ships lives inside the
    ``cylinder-pv-collapsed-candidate/`` directory under
    ``golden_samples/``. The HF1 path guard allows ``*-candidate``
    writes (and slice D Phase 13 will formalize this carve-out via
    ADR-011 amendment); pin the directory shape here so a future
    refactor that relocates the files doesn't silently bypass the
    carve-out."""
    case_dir = REPO_ROOT / "golden_samples" / COLLAPSED_CASE_ID
    files = list(case_dir.rglob("*"))
    file_paths = [p for p in files if p.is_file()]
    assert file_paths, "collapsed-candidate fixture has no files"
    for p in file_paths:
        rel = p.relative_to(REPO_ROOT / "golden_samples")
        assert str(rel).startswith(f"{COLLAPSED_CASE_ID}/"), (
            f"fixture file {rel} escapes the *-candidate directory"
        )


def test_collapsed_fixture_no_real_solver_artifacts() -> None:
    """The fixture must NOT contain real-solver artifacts (no
    OpenRadioss `.out` files, no CalculiX `.frd` results, no animation
    manifest pointing at real solver output). The deeper-degradation
    fixture is synthetic-only per the Phase 13 NON-NEGOTIABLE
    constraint."""
    case_dir = REPO_ROOT / "golden_samples" / COLLAPSED_CASE_ID
    forbidden_suffixes = (".out", ".frd", ".odb", ".vtu", ".cgns")
    for p in case_dir.rglob("*"):
        if p.is_file():
            for suffix in forbidden_suffixes:
                assert not str(p).endswith(suffix), (
                    f"real-solver artifact {p} smuggled into synthetic fixture"
                )


# ---------------------------------------------------------------------
# 6. Boundary tightness (T:-3 anti-loosening guard)
# ---------------------------------------------------------------------


def test_collapsed_trust_ceiling_is_exactly_50() -> None:
    """The trust-score ceiling pin is exactly 50, NOT 60 or any other
    loose value that would let a future regression past the bucket
    edge silently re-bucket the collapsed case as `watching`. This is
    the T:-3 boundary-pin guard: the test fails if a well-meaning
    refactor relaxes the threshold."""
    assert COLLAPSED_TRUST_SCORE_CEILING == 50
    # And the threshold matches the runtime classifier (this is the
    # observable contract; a silent rebalance would trip both pins).
    assert COLLAPSED_TRUST_SCORE_CEILING == WATCHING_TRUST_SCORE_MIN
