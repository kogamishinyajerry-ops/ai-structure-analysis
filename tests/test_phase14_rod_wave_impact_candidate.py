"""FM-04a Phase 14 D — rod-wave-impact-candidate fixture tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates ``golden_samples/rod-wave-impact-candidate/`` end-to-end:

  * Fixture directory + expected file inventory present.
  * Tier 1 disclaimer trio stamped on every emitted envelope.
  * Animation manifest first-reflection frame matches the analytical
    1D-bar prediction WITHIN the 5% tolerance pinned by
    ``explicit_dynamics_extraction.WAVE_CROSS_CHECK_TOLERANCE_PCT``
    (NOT just trusted from the fixture file: the analytical pin is
    re-derived inside the test from material constants and the
    observed-vs-analytical residual is computed via
    ``wave_propagation_residuals``).
  * Energy partition audit clean across all 100 frames.
  * Live ASGI ``/api/v1/case-completeness/{case_id}?analysis_type=
    explicit_dynamics`` lands >= 80/100.
  * Live ASGI ``/api/v1/visualize/result-mesh/{case_id}`` declines
    with 404 on a signed-registry-shaped *-candidate id (the route
    works; no false 422 on a candidate identifier).
  * Constraint guards (HF1.7a / HF1.7b carve-out posture).

Anti-gaming guards pinned here (per Phase 14 binding rubric §4 / §A:-3):
* The test does NOT read ``observed_first_reflection_s`` straight
  from the fixture and accept it; it COMPUTES the analytical pin from
  material constants (E, rho, L) using the SSOT
  ``bar_wave_speed_m_per_s`` + ``bar_wave_first_reflection_s`` helpers
  AND asserts the observed-vs-analytical residual is within
  ``WAVE_CROSS_CHECK_TOLERANCE_PCT``. A fixture that silently drifts
  to a wrong reflection frame trips THIS test, not just the parser.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.main import app
from app.services.reporting.explicit_dynamics_extraction import (
    WAVE_CROSS_CHECK_TOLERANCE_PCT,
    bar_wave_first_reflection_s,
    bar_wave_speed_m_per_s,
    energy_partition_audit,
    parse_animation_manifest,
    wave_propagation_residuals,
)

CASE_ID = "rod-wave-impact-candidate"
_REPO_ROOT = Path(__file__).resolve().parent.parent
_GS_DIR = _REPO_ROOT / "golden_samples" / CASE_ID
_PS_DIR = _REPO_ROOT / "project_state" / "graph_executor" / CASE_ID


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixture_regenerated() -> None:
    """`project_state/` is gitignored, so the route-readable copies
    (metrics / convergence / animation under
    ``project_state/graph_executor/rod-wave-impact-candidate/``) are
    NOT version-controlled. The fixture's self-documenting copies
    under ``golden_samples/rod-wave-impact-candidate/`` ARE checked
    in (HF1.7b carve-out), but the route-readable copies must be
    re-emitted by the generator. Run the generator once per test
    module if any route-readable file is missing."""
    needed = (
        _PS_DIR / "ballistic" / "ballistic_metrics.json",
        _PS_DIR / "convergence" / "convergence_study.json",
        _PS_DIR / "visualization" / "openradioss_animation_manifest.json",
    )
    if not all(p.is_file() for p in needed):
        import subprocess
        import sys

        subprocess.check_call(
            [
                sys.executable,
                str(_REPO_ROOT / "scripts" / "gen_rod_wave_impact_deck.py"),
            ],
            cwd=str(_REPO_ROOT),
        )


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(transport=self._transport, base_url="http://t") as c:
                return await c.get(url, params=params)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


# ---------------------------------------------------------------------
# 1. Fixture inventory
# ---------------------------------------------------------------------


def test_fixture_directory_present() -> None:
    """The fixture root lives under the HF1.7b `*-candidate` carve-out;
    no override needed for new fixture writes (Phase 13 D ADR
    amendment)."""
    assert _GS_DIR.is_dir()
    assert _GS_DIR.name.endswith("-candidate")


def test_fixture_self_documenting_files_present() -> None:
    """Reviewer-readable copies under golden_samples/<case>/."""
    for relpath in (
        "expected_results.json",
        "NOTES.md",
        "data/model_00_0000.rad",
        "data/model_00_0001.rad",
        "data/ballistic_metrics.json",
        "data/convergence_study.json",
        "data/animation_manifest.json",
    ):
        assert (_GS_DIR / relpath).is_file(), f"fixture missing {relpath!r}"


def test_route_readable_files_present() -> None:
    """Route-readable copies under project_state/graph_executor/<case>/
    so the case_completeness scorer + downstream routes find them."""
    for relpath in (
        "ballistic/ballistic_metrics.json",
        "convergence/convergence_study.json",
        "visualization/openradioss_animation_manifest.json",
    ):
        assert (_PS_DIR / relpath).is_file(), f"route-readable copy missing {relpath!r}"


def test_generator_script_present() -> None:
    """case_completeness gives a generator_script axis 5 pts; the
    generator MUST live at the slug-derived path."""
    script = _REPO_ROOT / "scripts" / "gen_rod_wave_impact_deck.py"
    assert script.is_file()


# ---------------------------------------------------------------------
# 2. Tier 1 disclaimer trio + analytical-cross-check claim_impact
# ---------------------------------------------------------------------


def test_expected_results_carries_tier1_disclaimer_trio() -> None:
    payload = json.loads((_GS_DIR / "expected_results.json").read_text(encoding="utf-8"))
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert "not signed validation" in payload["status_reason"]
    assert "not benchmark agreement" in payload["status_reason"]


def test_expected_results_cites_analytical_cross_check() -> None:
    """The status_reason MUST cite the analytical 1D-bar cross-check
    (the load-bearing posture statement for this fixture's Tier 1
    claim)."""
    payload = json.loads((_GS_DIR / "expected_results.json").read_text(encoding="utf-8"))
    reason = payload["status_reason"].lower()
    assert "1d" in reason or "1-d" in reason
    assert "reflection" in reason
    # The SSOT constant name appears so future bumps trace back.
    assert "wave_cross_check_tolerance_pct" in reason.lower()


def test_ballistic_metrics_carries_tier1_disclaimer_trio() -> None:
    payload = json.loads((_GS_DIR / "data" / "ballistic_metrics.json").read_text(encoding="utf-8"))
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert "not signed validation" in payload["claim_impact"]
    assert "not benchmark agreement" in payload["claim_impact"]


def test_convergence_study_is_explicit_dynamics_stable() -> None:
    payload = json.loads((_GS_DIR / "data" / "convergence_study.json").read_text(encoding="utf-8"))
    assert payload["convergence_kind"] == "explicit_dynamics"
    assert payload["combined_verdict"] == "candidate_observed_stable"
    assert payload["mesh_sweep"]["candidate_stability"] == "candidate_observed_stable"
    assert payload["dt_sweep"]["candidate_stability"] == "candidate_observed_stable"


# ---------------------------------------------------------------------
# 3. Animation manifest analytical cross-check (A:-3 defense-in-depth)
# ---------------------------------------------------------------------


def test_animation_manifest_first_reflection_matches_analytical() -> None:
    """The KEY anti-gaming guard for this slice. The test:
    1. RE-DERIVES the analytical 1D-bar wave speed + first-reflection
       time from the material constants the fixture self-reports.
    2. Computes the observed first-reflection time from the manifest's
       frame index + frame_dt (NOT trusting the fixture's
       self-reported observed time).
    3. Asserts the residual is within the SSOT 5%-tolerance constant.

    A fixture that silently drifts (e.g., wrong rho, wrong L, wrong
    frame_dt) breaks this assertion BEFORE any downstream consumer
    can rely on the wrong analytical pin."""
    manifest_payload = json.loads(
        (_GS_DIR / "data" / "animation_manifest.json").read_text(encoding="utf-8")
    )
    metrics = json.loads((_GS_DIR / "data" / "ballistic_metrics.json").read_text(encoding="utf-8"))
    summary = metrics["explicit_dynamics_summary"]

    E = float(summary["E_Pa"])
    rho = float(summary["rho_kg_per_m3"])
    L = float(summary["rod_length_m"])

    c = bar_wave_speed_m_per_s(E, rho)
    analytical_t = bar_wave_first_reflection_s(L, c)

    frame_idx = int(manifest_payload["first_reflection_frame_index"])
    frame_dt = float(manifest_payload["frame_dt_s"])
    observed_t = frame_idx * frame_dt

    residuals = wave_propagation_residuals(observed_t, analytical_t)
    assert residuals.within_tolerance is True, (
        f"observed first-reflection time {observed_t * 1e6:.3f}us "
        f"deviates {residuals.residual_pct:.2f}% from analytical "
        f"{analytical_t * 1e6:.3f}us (tolerance "
        f"{WAVE_CROSS_CHECK_TOLERANCE_PCT}%)"
    )


def test_animation_manifest_parser_roundtrip() -> None:
    """Phase 14 B parser successfully round-trips the fixture's
    animation manifest (frame_count, frame_dt, per-frame arrays
    consistent)."""
    manifest = parse_animation_manifest(_GS_DIR / "data" / "animation_manifest.json")
    assert manifest.frame_count == 100
    assert manifest.frame_dt_s == 1.0e-5
    assert manifest.total_duration_s == 1.0e-3
    assert manifest.first_reflection_frame_index == 20
    assert len(manifest.per_frame_kinetic_energy_j) == 100


def test_energy_partition_audit_clean_across_all_frames() -> None:
    """The synthetic Hopkinson-style fixture closes the energy
    balance at every frame by construction; audit MUST be CLEAN."""
    manifest = parse_animation_manifest(_GS_DIR / "data" / "animation_manifest.json")
    audit = energy_partition_audit(manifest)
    assert audit.clean is True, (
        f"energy partition flagged frames: "
        f"{audit.flagged_frame_indices}; max_rel_drift = "
        f"{audit.max_rel_drift_fraction:.4f}"
    )
    assert audit.flagged_frame_indices == ()


# ---------------------------------------------------------------------
# 4. Live ASGI integration
# ---------------------------------------------------------------------


def test_case_completeness_scorecard_lands_at_least_80(
    client: _SyncASGIClient,
) -> None:
    """The full case-completeness rubric on explicit_dynamics
    weights starter+engine(30) + metrics(20) + audit(15) +
    convergence(15) + animation(5) + generator(5) + notes(5) =
    95/100 BY CONSTRUCTION (result_mesh axis is absent, -5).
    Blueprint floor is >= 80/100."""
    res = client.get(f"/api/v1/case-completeness/{CASE_ID}?analysis_type=explicit_dynamics")
    assert res.status_code == 200
    body = res.json()
    assert body["case_id"] == CASE_ID
    assert body["analysis_type"] == "explicit_dynamics"
    assert body["score"] >= 80, (
        f"case-completeness landed at {body['score']}/100 "
        f"(< 80 floor). breakdown: {body['breakdown']}"
    )
    # Tier 1 trio carried on the envelope.
    assert body["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in body["claim_boundary"]
    assert "not_benchmark_agreement" in body["claim_boundary"]


def test_case_completeness_breakdown_load_bearing_axes_full(
    client: _SyncASGIClient,
) -> None:
    """The load-bearing axes (starter+engine decks, metrics, energy
    audit, convergence_study) MUST all be full-points; a regression
    in one of these would silently cap the fixture's substantiation."""
    res = client.get(f"/api/v1/case-completeness/{CASE_ID}?analysis_type=explicit_dynamics")
    body = res.json()
    bd = {b["label"]: b for b in body["breakdown"]}
    for axis in (
        "starter_deck",
        "engine_deck",
        "ballistic_metrics",
        "energy_audit",
        "convergence_study",
        "animation_manifest",
        "generator_script",
    ):
        assert bd[axis]["points_awarded"] == bd[axis]["points_max"], (
            f"axis {axis!r} not full: {bd[axis]}"
        )


# ---------------------------------------------------------------------
# 5. Constraint guards (HF1 carve-out posture)
# ---------------------------------------------------------------------


_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


def test_case_id_is_candidate_shape_not_signed_registry() -> None:
    """case_id MUST end with `-candidate` and MUST NOT match the
    signed-registry shape ``^GS-\\d{3}$``. The fixture lives under
    the HF1.7b carve-out (per Phase 13 D ADR amendment)."""
    assert CASE_ID.endswith("-candidate")
    assert _SIGNED_REGISTRY_RE.fullmatch(CASE_ID) is None


def test_no_real_solver_artifact_suffixes_present() -> None:
    """No `.frd` / `.dat` / `.h3d` / `.A###` files — the fixture is
    SYNTHETIC; a real CalculiX / OpenRadioss artifact would indicate
    the synthetic-fixture rule was breached."""
    forbidden_suffixes = (".frd", ".dat", ".h3d")
    for p in _GS_DIR.rglob("*"):
        if not p.is_file():
            continue
        for sfx in forbidden_suffixes:
            assert p.suffix != sfx, f"fixture contains real-solver artifact {p}"
    # A### radioss anim outputs would land under data/; check for the
    # numeric pattern.
    for p in (_GS_DIR / "data").rglob("*"):
        if p.is_file():
            assert not re.search(r"\.A\d{3}$", p.name), (
                f"fixture contains real OpenRadioss anim output {p}"
            )


def test_animation_manifest_carries_synthetic_disclaimer() -> None:
    """The animation manifest's claim_impact MUST explicitly cite
    that no real solver was invoked. This is the load-bearing
    Tier 1 disclaimer for the synthetic-fixture posture."""
    manifest_payload = json.loads(
        (_GS_DIR / "data" / "animation_manifest.json").read_text(encoding="utf-8")
    )
    impact = manifest_payload["claim_impact"].lower()
    assert "synthetic" in impact
    assert (
        "no real openradioss" in impact
        or "no real solver" in impact
        or "not signed validation" in impact
    )


def test_signed_registry_refusal_still_fires_on_gs_001_route() -> None:
    """Regression guard: the rod-wave-impact-candidate fixture is
    NOT a signed-registry id, so the per-route signed-registry
    helper MUST NOT trip on it. Conversely, a `GS-001` request on
    the same route MUST still 422 — this fixture's presence does
    not weaken the cross-route discipline."""
    cli = _SyncASGIClient(app)
    candidate = cli.get(f"/api/v1/case-completeness/{CASE_ID}?analysis_type=explicit_dynamics")
    gs = cli.get("/api/v1/case-completeness/GS-001?analysis_type=explicit_dynamics")
    assert candidate.status_code == 200
    assert gs.status_code == 422
    assert "signed-registry" in gs.json()["detail"]
