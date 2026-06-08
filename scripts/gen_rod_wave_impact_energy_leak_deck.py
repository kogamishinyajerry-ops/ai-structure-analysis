"""Re-generate the rod-wave-impact-energy-leak-candidate fixture.

FM-04a Phase 15 A. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Regressed-bucket variant of `gen_rod_wave_impact_deck.py` (Phase 14 D).
Same 1D-rod geometry + material as the canonical case (E=200 GPa
carbon steel, rho=7850, L=1m, v=10 m/s, frame_dt=10us), but the
animation manifest INJECTS 50% non-physical energy at frame 30:
KE[30] and SE[30] each scaled to 1.5x the analytical Hopkinson-style
value while W_ext[30] stays at the analytical value. The
`energy_partition_audit` flags frame 30 with rel_drift ~= 0.50,
well above the 1% ENERGY_PARTITION_DRIFT_FRACTION threshold from
Phase 14 B.

By construction this case lands BELOW the case_completeness healthy
80-pt floor (energy_audit axis is 0/15 because the metrics file
emits `energy_audit.status = "open_residual"`) AND the cohort trust-
score lands in the regressed bucket (<50) per Phase 15 B.

HF1.7b ``*-candidate`` carve-out applies; no override needed.

Usage:
    .venv/bin/python scripts/gen_rod_wave_impact_energy_leak_deck.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

# -- material + geometry constants (identical to canonical) ---------------

CASE_ID = "rod-wave-impact-energy-leak-candidate"
L_M = 1.0
E_PA = 200e9
RHO_KG_PER_M3 = 7850.0
CROSS_SECTION_AREA_M2 = 1.0e-4
IMPACT_VELOCITY_M_PER_S = 10.0
FRAME_COUNT = 100
FRAME_DT_S = 1.0e-5
STEADY_STATE_FRAME = 50

# -- leak injection SSOTs -------------------------------------------------

LEAK_INJECTION_FRAME: int = 30
"""Frame index where 50% non-physical energy is injected into the
synthetic manifest. Pinned by tests so a drifted leak frame trips
the audit assertion."""

LEAK_INJECTION_SCALE: float = 1.5
"""Multiplier applied to KE[30] + SE[30] (W_ext[30] unchanged). The
resulting per-frame relative drift is approximately
(scale - 1) * (KE + SE) / W_ext = 0.5 * 1.0 = 0.50, far above the
1% ENERGY_PARTITION_DRIFT_FRACTION threshold from
``explicit_dynamics_extraction.py``."""

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
    """Hopkinson-style pre-leak energies, then inject 50% non-physical
    energy at frame ``LEAK_INJECTION_FRAME``."""
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
        k = slope * eff
        s = slope * eff
        w = 2.0 * slope * eff
        if f == LEAK_INJECTION_FRAME:
            # 50% non-physical energy injection: KE + SE inflated
            # while external work stays at the analytical value.
            k *= LEAK_INJECTION_SCALE
            s *= LEAK_INJECTION_SCALE
        kin.append(k)
        inn.append(s)
        ext.append(w)
    return kin, inn, ext


def _animation_manifest() -> dict[str, object]:
    kin, inn, ext = _per_frame_energies()
    return {
        "schema_version": "rod-wave-impact-animation-manifest.v1",
        "claim_tier": TIER1_CLAIM_TIER,
        "claim_boundary": TIER1_CLAIM_BOUNDARY,
        "claim_impact": (
            "Tier 1 candidate synthetic explicit_dynamics animation "
            "manifest (ENERGY-LEAK variant: 50% non-physical energy "
            "injected at frame {leak}); not signed validation; not "
            "benchmark agreement. By construction the per-frame "
            "energy_partition_audit flags frame {leak} as a "
            "deviation; the case is REGRESSED and lands below the "
            "healthy 80-pt case_completeness floor. No real "
            "OpenRadioss transient solve was invoked; the leak is "
            "synthetic and pinned by Phase 15 A "
            "LEAK_INJECTION_FRAME + LEAK_INJECTION_SCALE."
        ).format(leak=LEAK_INJECTION_FRAME),
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
            "Tier 1 candidate 1D-bar wave-propagation case (ENERGY-"
            "LEAK variant); not signed validation; not benchmark "
            "agreement. Synthetic non-physical energy injection at "
            "frame {leak} flags the energy_partition_audit; "
            "energy_audit.status is open_residual by construction. "
            "Does not authorize Tier 2 promotion."
        ).format(leak=LEAK_INJECTION_FRAME),
        "energy_audit": {
            "status": "open_residual",
            "rationale": (
                "Per-frame audit flags frame {leak} with relative "
                "drift ~= 0.50, well above the 1% "
                "ENERGY_PARTITION_DRIFT_FRACTION threshold. The "
                "case_completeness energy_audit axis lands 0/15 "
                "because closed_aggregate posture is not met."
            ).format(leak=LEAK_INJECTION_FRAME),
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
            "leak_injection_frame": LEAK_INJECTION_FRAME,
            "leak_injection_scale": LEAK_INJECTION_SCALE,
        },
    }


def _convergence_study() -> dict[str, object]:
    return {
        "case_id": CASE_ID,
        "claim_tier": TIER1_CLAIM_TIER,
        "claim_boundary": TIER1_CLAIM_BOUNDARY,
        "convergence_kind": "explicit_dynamics",
        "combined_verdict": "candidate_observed_unstable",
        "mesh_sweep": {
            "axis": "mesh_h",
            "candidate_stability": "candidate_observed_unstable",
            "rationale": (
                "Synthetic 1D-bar ENERGY-LEAK variant; mesh axis "
                "held constant but the audit's energy_partition "
                "deviation propagates as an unstable verdict — the "
                "per-frame energy balance is non-physical, so the "
                "convergence_combined_verdict cannot be stable."
            ),
        },
        "dt_sweep": {
            "axis": "frame_dt_s",
            "candidate_stability": "candidate_observed_unstable",
            "rationale": (
                "frame_dt unchanged from canonical (1e-5 s); the dt "
                "axis instability reflects the synthetic energy "
                "injection at frame {leak}, not a CFL violation. A "
                "reviewer reading this case must check the audit "
                "first."
            ).format(leak=LEAK_INJECTION_FRAME),
        },
    }


def _expected_results() -> dict[str, object]:
    return {
        "analysis_type": "explicit_dynamics",
        "case_id": CASE_ID,
        "case_name": (
            "1D rod axial-impact wave propagation with synthetic "
            "energy injection at frame {leak}, L=1.0m, 10mm x 10mm "
            "SA-516 Gr.70 steel (synthetic Hopkinson-bar with "
            "ENERGY-LEAK injection)"
        ).format(leak=LEAK_INJECTION_FRAME),
        "claim_tier": TIER1_CLAIM_TIER,
        "claim_boundary": TIER1_CLAIM_BOUNDARY,
        "status": "engineering_candidate_regressed",
        "status_reason": (
            "Tier 1 engineering candidate; not signed validation; "
            "not benchmark agreement. ENERGY-LEAK variant: synthetic "
            "50% non-physical energy injected at frame {leak} trips "
            "the per-frame energy_partition_audit (rel_drift ~= "
            "0.50 vs ENERGY_PARTITION_DRIFT_FRACTION=0.01). The "
            "audit deviation propagates to "
            "energy_audit.status=open_residual; the case_completeness "
            "scorecard lands below the healthy 80-pt floor by "
            "construction. No real OpenRadioss invocation; Tier 2 "
            "promotion is explicitly deferred."
        ).format(leak=LEAK_INJECTION_FRAME),
        "fixture_authoring_notes": {
            "wave_speed_m_per_s_analytical": _wave_speed_m_per_s(),
            "first_reflection_s_analytical": _analytical_first_reflection_s(),
            "first_reflection_frame_index_observed": _first_reflection_frame_index(),
            "cross_check_tolerance_pct": 5.0,
            "leak_injection_frame": LEAK_INJECTION_FRAME,
            "leak_injection_scale": LEAK_INJECTION_SCALE,
            "expected_flagged_frame_indices": (LEAK_INJECTION_FRAME,),
            "expected_max_rel_drift_fraction_approx": 0.50,
            "delta_from_canonical_case": (
                "Geometry + material + velocity + frame_dt all "
                "identical to canonical. ONLY the animation "
                "manifest's per_frame_kinetic_energy_j[{leak}] and "
                "per_frame_internal_energy_j[{leak}] are scaled by "
                "1.5 to inject 50% non-physical energy."
            ).format(leak=LEAK_INJECTION_FRAME),
        },
        "expected_first_reflection_s": _analytical_first_reflection_s(),
    }


def _notes_md() -> str:
    return (
        f"# rod-wave-impact-energy-leak-candidate — fixture notes\n\n"
        f"Tier 1 engineering candidate; not signed validation; not "
        f"benchmark agreement.\n\n"
        f"Regressed-bucket sibling of the canonical "
        f"`rod-wave-impact-candidate` (Phase 14 D). Same geometry / "
        f"material / velocity / frame_dt; ONLY the animation manifest "
        f"injects 50% non-physical energy at frame "
        f"{LEAK_INJECTION_FRAME}.\n\n"
        f"## Failure mode (by construction)\n\n"
        f"* `per_frame_kinetic_energy_j[{LEAK_INJECTION_FRAME}]` "
        f"and `per_frame_internal_energy_j[{LEAK_INJECTION_FRAME}]` "
        f"each scaled by {LEAK_INJECTION_SCALE}.\n"
        f"* `per_frame_external_work_j[{LEAK_INJECTION_FRAME}]` "
        f"unchanged.\n"
        f"* `energy_partition_audit.flagged_frame_indices` = "
        f"`({LEAK_INJECTION_FRAME},)`.\n"
        f"* `energy_partition_audit.max_rel_drift_fraction` ~= 0.50 "
        f"(well above the 1% "
        f"ENERGY_PARTITION_DRIFT_FRACTION threshold).\n"
        f"* `ballistic_metrics.energy_audit.status` = "
        f"`open_residual`.\n"
        f"* `case_completeness` scorecard lands "
        f"below the 80-pt healthy floor.\n\n"
        f"## What this fixture is NOT\n\n"
        f"* Not a real OpenRadioss or CalculiX *DYNAMIC run.\n"
        f"* Not a real physical energy injection; the leak is "
        f"synthetic and pinned by `LEAK_INJECTION_FRAME` + "
        f"`LEAK_INJECTION_SCALE` SSOT constants.\n"
        f"* Not Tier 2 benchmark agreement.\n"
        f"* Not a signed validation packet.\n\n"
        f"Regenerate with "
        f"`python scripts/gen_rod_wave_impact_energy_leak_deck.py`.\n"
    )


def _starter_deck_rad() -> str:
    return (
        "# rod-wave-impact-energy-leak-candidate starter deck "
        "(SYNTHETIC stub)\n"
        "# Tier 1 engineering candidate; not signed validation; "
        "not benchmark agreement.\n"
        "# Identical to canonical rod-wave-impact-candidate; the\n"
        "# leak is in the animation manifest only.\n"
        f"# L = {L_M} m, A = {CROSS_SECTION_AREA_M2} m^2, "
        f"E = {E_PA} Pa, rho = {RHO_KG_PER_M3} kg/m^3\n"
    )


def _engine_deck_rad() -> str:
    return (
        "# rod-wave-impact-energy-leak-candidate engine deck "
        "(SYNTHETIC stub)\n"
        "# Tier 1 engineering candidate; not signed validation; "
        "not benchmark agreement.\n"
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

    print(f"wrote energy-leak fixture to {gs_root}/ and {ps_case}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
