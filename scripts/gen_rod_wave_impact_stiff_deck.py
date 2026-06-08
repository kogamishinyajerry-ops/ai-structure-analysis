"""Re-generate the rod-wave-impact-stiff-candidate fixture artefacts.

FM-04a Phase 15 A. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Sibling of `scripts/gen_rod_wave_impact_deck.py` (Phase 14 D). Same
1D-rod axial-impact wave-propagation geometry, but emitted at a
stiffer Young's modulus (E=210 GPa tool steel vs the canonical case's
200 GPa SA-516 Gr.70 carbon steel). The stiffer rod produces a
faster wave (c ~= 5174 m/s vs 5048 m/s), so the first reflection
arrives EARLIER (~193 us vs ~198 us). The fixture rounds to
first_reflection_frame_index = 19 (observed=190us; analytical=
193.3us; residual ~1.71% — still well within the 5%
WAVE_CROSS_CHECK_TOLERANCE_PCT engineering tolerance band).

The case is HEALTHY by construction: case_completeness scorecard
expected to land at 95/100 (same axes-complete pattern as the
canonical candidate); trust score expected to land in the healthy
bucket (>=80). The Phase 15 B 3-snapshot arc drifts this case
INTO the watching bucket between snap-1 and snap-2 by emitting
LOWER per-snapshot scores (the fixture itself stays valid; the
SNAPSHOT manifest reflects degraded reviewer evidence).

HF1.7b ``*-candidate`` carve-out applies; no override needed.

Usage:
    .venv/bin/python scripts/gen_rod_wave_impact_stiff_deck.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

# -- material + geometry constants (SSOT for this stiff variant) ---------

CASE_ID = "rod-wave-impact-stiff-candidate"
L_M = 1.0
E_PA = 210e9  # tool steel; stiffer than the canonical 200 GPa
RHO_KG_PER_M3 = 7850.0  # same density
CROSS_SECTION_AREA_M2 = 1.0e-4
IMPACT_VELOCITY_M_PER_S = 10.0
FRAME_COUNT = 100
FRAME_DT_S = 1.0e-5
STEADY_STATE_FRAME = 50
TIER1_CLAIM_TIER = "Tier 1 engineering candidate"
TIER1_CLAIM_BOUNDARY = (
    "tier1_engineering_candidate; not_signed_validation; "
    "not_benchmark_agreement"
)


def _wave_speed_m_per_s() -> float:
    return math.sqrt(E_PA / RHO_KG_PER_M3)


def _analytical_first_reflection_s() -> float:
    return L_M / _wave_speed_m_per_s()


def _first_reflection_frame_index() -> int:
    return round(_analytical_first_reflection_s() / FRAME_DT_S)


def _per_frame_energies() -> tuple[list[float], list[float], list[float]]:
    """Mirror of `gen_rod_wave_impact_deck._per_frame_energies` but
    with the stiff variant's constants. Hopkinson-style closed
    energy balance preserved frame-by-frame."""
    c = _wave_speed_m_per_s()
    v = IMPACT_VELOCITY_M_PER_S
    rho = RHO_KG_PER_M3
    A = CROSS_SECTION_AREA_M2
    slope = 0.5 * rho * v * v * A * c * FRAME_DT_S
    kin: list[float] = []
    inn: list[float] = []
    ext: list[float] = []
    for f in range(FRAME_COUNT):
        eff = min(f, STEADY_STATE_FRAME)
        kin.append(slope * eff)
        inn.append(slope * eff)
        ext.append(2.0 * slope * eff)
    return kin, inn, ext


def _animation_manifest() -> dict[str, object]:
    kin, inn, ext = _per_frame_energies()
    return {
        "schema_version": "rod-wave-impact-animation-manifest.v1",
        "claim_tier": TIER1_CLAIM_TIER,
        "claim_boundary": TIER1_CLAIM_BOUNDARY,
        "claim_impact": (
            "Tier 1 candidate synthetic explicit_dynamics animation "
            "manifest (STIFF variant: E=210 GPa tool steel); not "
            "signed validation; not benchmark agreement. Per-frame "
            "energy partition emitted from a 1D-bar Hopkinson-style "
            "idealization. first_reflection_frame_index reflects "
            "the stiffer rod's faster wave speed (~5174 m/s) and "
            "earlier reflection (~193us); residual vs analytical "
            "still within the 5% WAVE_CROSS_CHECK_TOLERANCE_PCT "
            "engineering tolerance per Phase 14 B "
            "explicit_dynamics_extraction.py. No real OpenRadioss "
            "transient solve was invoked."
        ),
        "case_id": CASE_ID,
        "frame_count": FRAME_COUNT,
        "frame_dt_s": FRAME_DT_S,
        "total_duration_s": FRAME_DT_S * FRAME_COUNT,
        "per_frame_kinetic_energy_j": kin,
        "per_frame_internal_energy_j": inn,
        "per_frame_external_work_j": ext,
        "first_reflection_frame_index": _first_reflection_frame_index(),
    }


def _ballistic_metrics() -> dict[str, object]:
    return {
        "analysis_type": "explicit_dynamics_transient",
        "case_id": CASE_ID,
        "claim_tier": TIER1_CLAIM_TIER,
        "claim_boundary": TIER1_CLAIM_BOUNDARY,
        "claim_impact": (
            "Tier 1 candidate 1D-bar wave-propagation case (STIFF "
            "variant); not signed validation; not benchmark "
            "agreement. Synthetic explicit_dynamics_transient "
            "response cross-checked against the closed-form 1D "
            "elastic-rod axial wave (c=sqrt(E/rho), t_refl=L/c) "
            "with E=210 GPa (tool steel). Energy partition closed "
            "by construction; no real OpenRadioss invocation. Does "
            "not authorize Tier 2 promotion."
        ),
        "energy_audit": {
            "status": "closed_aggregate",
            "rationale": (
                "Per-frame kinetic + internal energy sum to "
                "external work at machine epsilon at every frame. "
                "Hopkinson-style idealization with no plasticity / "
                "contact / hourglass leakage; analytical balance "
                "preserved across the 100-frame synthetic "
                "animation. STIFF variant carries the same closed-"
                "aggregate posture as the canonical case."
            ),
        },
        "explicit_dynamics_summary": {
            "rod_length_m": L_M,
            "cross_section_area_m2": CROSS_SECTION_AREA_M2,
            "E_Pa": E_PA,
            "rho_kg_per_m3": RHO_KG_PER_M3,
            "impact_velocity_m_per_s": IMPACT_VELOCITY_M_PER_S,
            "analytical_wave_speed_m_per_s": _wave_speed_m_per_s(),
            "analytical_first_reflection_s": _analytical_first_reflection_s(),
            "observed_first_reflection_frame_index": _first_reflection_frame_index(),
            "observed_first_reflection_s": _first_reflection_frame_index() * FRAME_DT_S,
            "frame_count": FRAME_COUNT,
            "frame_dt_s": FRAME_DT_S,
        },
    }


def _convergence_study() -> dict[str, object]:
    return {
        "case_id": CASE_ID,
        "claim_tier": TIER1_CLAIM_TIER,
        "claim_boundary": TIER1_CLAIM_BOUNDARY,
        "convergence_kind": "explicit_dynamics",
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {
            "axis": "mesh_h",
            "candidate_stability": "candidate_observed_stable",
            "rationale": (
                "Synthetic 1D-bar STIFF variant; mesh axis held "
                "constant at h=0.025m (40 elements along L=1m). "
                "candidate_observed_stable asserted from the "
                "analytical 1D-rod manifold match at E=210 GPa, "
                "NOT from a real CFL/h sweep across a physical "
                "solver."
            ),
        },
        "dt_sweep": {
            "axis": "frame_dt_s",
            "candidate_stability": "candidate_observed_stable",
            "rationale": (
                "Synthetic frame_dt=1e-5 s; analytical first-"
                "reflection at t=L/c=193.3us rounds to frame index "
                "19 (observed=190us; residual ~1.71% within the 5% "
                "WAVE_CROSS_CHECK_TOLERANCE_PCT band). No real CFL-"
                "limit search performed."
            ),
        },
    }


def _expected_results() -> dict[str, object]:
    return {
        "analysis_type": "explicit_dynamics",
        "case_id": CASE_ID,
        "case_name": (
            "1D rod axial-impact wave propagation, L=1.0m, 10mm x "
            "10mm cross section, tool steel (E=210 GPa), impact "
            "velocity 10 m/s (synthetic Hopkinson-bar idealization "
            "STIFF variant)"
        ),
        "claim_tier": TIER1_CLAIM_TIER,
        "claim_boundary": TIER1_CLAIM_BOUNDARY,
        "status": "engineering_candidate",
        "status_reason": (
            "Tier 1 engineering candidate; not signed validation; "
            "not benchmark agreement. STIFF variant: E=210 GPa tool "
            "steel produces faster wave (~5174 m/s vs ~5048 m/s "
            "carbon-steel canonical) and earlier first reflection "
            "(~193us vs ~198us). Observed first_reflection_frame_"
            "index=19 (observed=190us) lands 1.71% from analytical "
            "(193.3us) — within the 5% WAVE_CROSS_CHECK_TOLERANCE_"
            "PCT engineering tolerance per Phase 14 B "
            "explicit_dynamics_extraction.py. Per-frame energy "
            "partition closed at machine epsilon. No real "
            "OpenRadioss invocation; Tier 2 promotion is explicitly "
            "deferred."
        ),
        "fixture_authoring_notes": {
            "wave_speed_m_per_s_analytical": _wave_speed_m_per_s(),
            "first_reflection_s_analytical": _analytical_first_reflection_s(),
            "first_reflection_frame_index_observed": _first_reflection_frame_index(),
            "first_reflection_s_observed": _first_reflection_frame_index() * FRAME_DT_S,
            "cross_check_tolerance_pct": 5.0,
            "delta_from_canonical_case": (
                "E increased 200->210 GPa (tool steel vs carbon "
                "steel); rho unchanged; geometry unchanged; impact "
                "velocity unchanged. Wave speed +2.5%; first-"
                "reflection time -2.5%."
            ),
        },
        "expected_first_reflection_s": _analytical_first_reflection_s(),
    }


def _notes_md() -> str:
    return (
        f"# rod-wave-impact-stiff-candidate — fixture notes\n\n"
        f"Tier 1 engineering candidate; not signed validation; not "
        f"benchmark agreement.\n\n"
        f"Sibling of `rod-wave-impact-candidate` (Phase 14 D). The "
        f"STIFF variant changes ONLY Young's modulus "
        f"(200 GPa -> 210 GPa) so the analytical 1D-bar wave-"
        f"propagation cross-check shifts to a faster wave and "
        f"earlier reflection.\n\n"
        f"## Geometry (unchanged from canonical)\n\n"
        f"* Rod length L = {L_M} m\n"
        f"* Cross-section area A = {CROSS_SECTION_AREA_M2} m^2 "
        f"(10 mm x 10 mm)\n"
        f"* Impact velocity v = {IMPACT_VELOCITY_M_PER_S} m/s at "
        f"x = 0; far end at x = L is FREE\n\n"
        f"## Material (STIFF variant)\n\n"
        f"* E = {E_PA:.3e} Pa (tool steel; vs 2.0e+11 carbon "
        f"steel in the canonical case)\n"
        f"* rho = {RHO_KG_PER_M3} kg/m^3 (unchanged)\n\n"
        f"## Analytical cross-check\n\n"
        f"* Wave speed c = sqrt(E/rho) = "
        f"{_wave_speed_m_per_s():.1f} m/s.\n"
        f"* First reflection t_refl = L/c = "
        f"{_analytical_first_reflection_s() * 1e6:.2f} us.\n"
        f"* Frame dt = {FRAME_DT_S * 1e6:.1f} us; first-reflection "
        f"frame index = {_first_reflection_frame_index()} "
        f"(observed = "
        f"{_first_reflection_frame_index() * FRAME_DT_S * 1e6:.1f} us; "
        f"residual = "
        f"{abs(_first_reflection_frame_index() * FRAME_DT_S - _analytical_first_reflection_s()) / _analytical_first_reflection_s() * 100:.2f}%; "
        f"within the 5% WAVE_CROSS_CHECK_TOLERANCE_PCT band).\n\n"
        f"## What this fixture is NOT\n\n"
        f"* Not a real OpenRadioss or CalculiX *DYNAMIC run; the "
        f"animation manifest is synthetic.\n"
        f"* Not Tier 2 benchmark agreement.\n"
        f"* Not a signed validation packet.\n\n"
        f"Regenerate with `python scripts/gen_rod_wave_impact_stiff_deck.py`.\n"
    )


def _starter_deck_rad() -> str:
    return (
        "# rod-wave-impact-stiff-candidate starter deck (SYNTHETIC stub)\n"
        "# Tier 1 engineering candidate; not signed validation; "
        "not benchmark agreement.\n"
        "# This is NOT a runnable OpenRadioss deck — see the\n"
        "# canonical rod-wave-impact-candidate's deck for the\n"
        "# synthetic-fixture rationale.\n"
        f"# L = {L_M} m, A = {CROSS_SECTION_AREA_M2} m^2, "
        f"E = {E_PA} Pa (tool steel), rho = {RHO_KG_PER_M3} kg/m^3\n"
        f"# Impact velocity {IMPACT_VELOCITY_M_PER_S} m/s at x=0; "
        f"free end at x=L\n"
    )


def _engine_deck_rad() -> str:
    return (
        "# rod-wave-impact-stiff-candidate engine deck (SYNTHETIC stub)\n"
        "# Tier 1 engineering candidate; not signed validation; "
        "not benchmark agreement.\n"
        "# This is NOT a runnable OpenRadioss deck.\n"
        f"# frame_count = {FRAME_COUNT}, frame_dt_s = {FRAME_DT_S}\n"
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    gs_root = repo_root / "golden_samples" / CASE_ID
    gs_data = gs_root / "data"
    ps_case = repo_root / "project_state" / "graph_executor" / CASE_ID
    ps_metrics = ps_case / "ballistic"
    ps_convergence = ps_case / "convergence"
    ps_anim = ps_case / "visualization"

    for d in (gs_root, gs_data, ps_metrics, ps_convergence, ps_anim):
        d.mkdir(parents=True, exist_ok=True)

    (gs_root / "expected_results.json").write_text(
        json.dumps(_expected_results(), indent=2) + "\n",
        encoding="utf-8",
    )
    (gs_root / "NOTES.md").write_text(_notes_md(), encoding="utf-8")
    (gs_data / "model_00_0000.rad").write_text(
        _starter_deck_rad(), encoding="utf-8"
    )
    (gs_data / "model_00_0001.rad").write_text(
        _engine_deck_rad(), encoding="utf-8"
    )
    ballistic = _ballistic_metrics()
    convergence = _convergence_study()
    animation = _animation_manifest()
    (gs_data / "ballistic_metrics.json").write_text(
        json.dumps(ballistic, indent=2) + "\n", encoding="utf-8"
    )
    (gs_data / "convergence_study.json").write_text(
        json.dumps(convergence, indent=2) + "\n", encoding="utf-8"
    )
    (gs_data / "animation_manifest.json").write_text(
        json.dumps(animation, indent=2) + "\n", encoding="utf-8"
    )
    (ps_metrics / "ballistic_metrics.json").write_text(
        json.dumps(ballistic, indent=2) + "\n", encoding="utf-8"
    )
    (ps_convergence / "convergence_study.json").write_text(
        json.dumps(convergence, indent=2) + "\n", encoding="utf-8"
    )
    (ps_anim / "openradioss_animation_manifest.json").write_text(
        json.dumps(animation, indent=2) + "\n", encoding="utf-8"
    )

    print(f"wrote stiff fixture to {gs_root}/ and {ps_case}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
