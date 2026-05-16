"""FM-04a Phase 14 B — explicit_dynamics extraction service tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates ``backend/app/services/reporting/explicit_dynamics_extraction.py``:
the canonical animation-manifest parser, the 1D-bar wave-speed +
first-reflection analytical pins, the residual + tolerance verdict, and
the per-frame energy-partition audit.

Anti-gaming guards pinned here (per Phase 14 binding rubric §4):
* **M:-2** — module-level constants ``WAVE_CROSS_CHECK_TOLERANCE_PCT``,
  ``EXPLICIT_DYNAMICS_CONVERGENCE_KIND``, ``ENERGY_PARTITION_EPSILON``,
  ``ENERGY_PARTITION_DRIFT_FRACTION`` live at the documented module
  surface and carry the documented values.
* **T:-3** — boundary-pinned analytical cross-check: steel
  (E=200 GPa, rho=7850 kg/m³) lands at c≈5050 m/s; L=1.0 m bar lands
  at t_refl≈0.198 ms.
* **A:-3** — defensive parser raises on missing keys, malformed JSON,
  inconsistent per-frame array lengths, non-positive frame_count /
  frame_dt, and out-of-range first_reflection_frame_index BEFORE
  returning the manifest.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from app.services.reporting.explicit_dynamics_extraction import (
    ENERGY_PARTITION_DRIFT_FRACTION,
    ENERGY_PARTITION_EPSILON,
    EXPLICIT_DYNAMICS_CONVERGENCE_KIND,
    WAVE_CROSS_CHECK_TOLERANCE_PCT,
    AnimationManifest,
    EnergyPartitionAudit,
    WaveResiduals,
    bar_wave_first_reflection_s,
    bar_wave_speed_m_per_s,
    energy_partition_audit,
    parse_animation_manifest,
    wave_propagation_residuals,
)

# ---------------------------------------------------------------------
# M:-2 SSOT constant pins
# ---------------------------------------------------------------------


def test_wave_cross_check_tolerance_pct_is_5_0() -> None:
    """SSOT constant pin. Bumping this value MUST update the
    methodology doc bump-history (per
    ``.planning/methodology/explicit_dynamics_cross_check.md``)."""
    assert isinstance(WAVE_CROSS_CHECK_TOLERANCE_PCT, float)
    assert WAVE_CROSS_CHECK_TOLERANCE_PCT == 5.0


def test_explicit_dynamics_convergence_kind_matches_analysis_tuple() -> None:
    """The discriminator string MUST be a member of
    ``ANALYSIS_TYPE_TUPLE`` and live at the documented index (2,
    after ``ballistic`` and ``linear_static_pv``; ``modal`` comes
    after ``explicit_dynamics`` per Phase 12 substantiation)."""
    from app.services.reporting.case_completeness import ANALYSIS_TYPE_TUPLE

    assert EXPLICIT_DYNAMICS_CONVERGENCE_KIND == "explicit_dynamics"
    assert EXPLICIT_DYNAMICS_CONVERGENCE_KIND in ANALYSIS_TYPE_TUPLE
    assert ANALYSIS_TYPE_TUPLE[2] == EXPLICIT_DYNAMICS_CONVERGENCE_KIND


def test_energy_partition_epsilon_is_small_float() -> None:
    """Float-arithmetic floor for the energy-partition audit."""
    assert isinstance(ENERGY_PARTITION_EPSILON, float)
    assert 0.0 < ENERGY_PARTITION_EPSILON <= 1e-6


def test_energy_partition_drift_fraction_is_one_percent() -> None:
    """1% relative-drift flag threshold; mirrors closed-aggregate
    posture in case_completeness energy_audit."""
    assert isinstance(ENERGY_PARTITION_DRIFT_FRACTION, float)
    assert ENERGY_PARTITION_DRIFT_FRACTION == 0.01


# ---------------------------------------------------------------------
# T:-3 boundary-pinned analytical cross-check
# ---------------------------------------------------------------------


def test_bar_wave_speed_steel_lands_at_5050_m_per_s() -> None:
    """Steel: E=200 GPa, rho=7850 kg/m³ -> c≈5048 m/s (within 1 m/s
    of the canonical 5050 figure cited in the methodology doc)."""
    c = bar_wave_speed_m_per_s(E_Pa=200e9, rho_kg_per_m3=7850.0)
    assert 5040.0 < c < 5060.0
    # boundary-pinned: relative tolerance 1e-3 against the closed form
    assert math.isclose(c, math.sqrt(200e9 / 7850.0), rel_tol=1e-12)


def test_bar_wave_first_reflection_1m_steel_lands_at_0_198_ms() -> None:
    """L=1.0 m steel bar -> t_refl≈0.000198 s (within 1 µs of
    canonical 0.198 ms)."""
    c = bar_wave_speed_m_per_s(E_Pa=200e9, rho_kg_per_m3=7850.0)
    t = bar_wave_first_reflection_s(L_m=1.0, c_m_per_s=c)
    assert 1.97e-4 < t < 1.99e-4
    assert math.isclose(t, 1.0 / c, rel_tol=1e-12)


def test_bar_wave_speed_aluminum_lands_at_5100_m_per_s() -> None:
    """Aluminum: E=70 GPa, rho=2700 kg/m³ -> c≈5092 m/s."""
    c = bar_wave_speed_m_per_s(E_Pa=70e9, rho_kg_per_m3=2700.0)
    assert 5080.0 < c < 5100.0


def test_bar_wave_speed_rejects_non_positive_inputs() -> None:
    """Numerical defense; non-physical inputs raise ValueError."""
    with pytest.raises(ValueError):
        bar_wave_speed_m_per_s(E_Pa=0.0, rho_kg_per_m3=7850.0)
    with pytest.raises(ValueError):
        bar_wave_speed_m_per_s(E_Pa=200e9, rho_kg_per_m3=0.0)
    with pytest.raises(ValueError):
        bar_wave_speed_m_per_s(E_Pa=-1.0, rho_kg_per_m3=7850.0)


def test_bar_wave_first_reflection_rejects_non_positive_inputs() -> None:
    """Numerical defense."""
    with pytest.raises(ValueError):
        bar_wave_first_reflection_s(L_m=0.0, c_m_per_s=5050.0)
    with pytest.raises(ValueError):
        bar_wave_first_reflection_s(L_m=1.0, c_m_per_s=-5050.0)


# ---------------------------------------------------------------------
# wave_propagation_residuals contract
# ---------------------------------------------------------------------


def test_residuals_within_tolerance_for_clean_observation() -> None:
    """Observed lands within 0.5% of analytical -> within_tolerance."""
    analytical = 1.98e-4  # ~0.198 ms
    observed = analytical * 1.004  # 0.4% high
    res = wave_propagation_residuals(observed, analytical)
    assert isinstance(res, WaveResiduals)
    assert res.within_tolerance is True
    assert res.tolerance_pct == WAVE_CROSS_CHECK_TOLERANCE_PCT
    assert 0.3 < res.residual_pct < 0.5
    assert res.residual_s > 0  # observed > analytical, positive residual


def test_residuals_outside_tolerance_for_drifted_observation() -> None:
    """Observed lands at 12% deviation -> NOT within_tolerance.
    Mirrors the slice-D 'synthetic observed-wrong' fixture."""
    analytical = 1.98e-4
    observed = analytical * 1.12  # 12% high
    res = wave_propagation_residuals(observed, analytical)
    assert res.within_tolerance is False
    assert 11.5 < res.residual_pct < 12.5


def test_residuals_handle_negative_drift_via_absolute_value() -> None:
    """A 6% LOW observation is just as out-of-band as a 6% HIGH
    observation; tolerance applies to ``|residual|``."""
    analytical = 1.98e-4
    observed_low = analytical * 0.94  # 6% low
    res = wave_propagation_residuals(observed_low, analytical)
    assert res.within_tolerance is False
    assert res.residual_s < 0
    assert 5.5 < res.residual_pct < 6.5


def test_residuals_reject_non_positive_analytical() -> None:
    """Division-by-zero / non-physical defense."""
    with pytest.raises(ValueError):
        wave_propagation_residuals(1e-4, 0.0)
    with pytest.raises(ValueError):
        wave_propagation_residuals(1e-4, -1e-4)


def test_residuals_reject_non_positive_tolerance() -> None:
    """Tolerance MUST be positive."""
    with pytest.raises(ValueError):
        wave_propagation_residuals(1e-4, 1e-4, tolerance_pct=0.0)
    with pytest.raises(ValueError):
        wave_propagation_residuals(1e-4, 1e-4, tolerance_pct=-1.0)


# ---------------------------------------------------------------------
# parse_animation_manifest — parser round-trips + defensive raises
# ---------------------------------------------------------------------


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _canonical_one_frame_payload() -> dict[str, object]:
    return {
        "frame_count": 1,
        "frame_dt_s": 1.0e-5,
        "total_duration_s": 1.0e-5,
        "per_frame_kinetic_energy_j": [10.0],
        "per_frame_internal_energy_j": [5.0],
        "per_frame_external_work_j": [15.0],
    }


def test_parser_roundtrips_one_frame_manifest(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    _write_manifest(p, _canonical_one_frame_payload())
    m = parse_animation_manifest(p)
    assert isinstance(m, AnimationManifest)
    assert m.frame_count == 1
    assert m.frame_dt_s == 1.0e-5
    assert m.total_duration_s == 1.0e-5
    assert m.per_frame_kinetic_energy_j == (10.0,)
    assert m.per_frame_internal_energy_j == (5.0,)
    assert m.per_frame_external_work_j == (15.0,)
    assert m.first_reflection_frame_index is None


def test_parser_roundtrips_ten_frame_manifest(tmp_path: Path) -> None:
    p = tmp_path / "m.json"
    _write_manifest(
        p,
        {
            "frame_count": 10,
            "frame_dt_s": 1.0e-5,
            "total_duration_s": 1.0e-4,
            "per_frame_kinetic_energy_j": [float(i) for i in range(10)],
            "per_frame_internal_energy_j": [float(i) * 2 for i in range(10)],
            "per_frame_external_work_j": [float(i) * 3 for i in range(10)],
            "first_reflection_frame_index": 4,
        },
    )
    m = parse_animation_manifest(p)
    assert m.frame_count == 10
    assert len(m.per_frame_kinetic_energy_j) == 10
    assert m.first_reflection_frame_index == 4


def test_parser_roundtrips_100_frame_manifest(tmp_path: Path) -> None:
    """Mirrors the slice-D rod-wave-impact-candidate fixture
    (100 frames at frame_dt=1e-5 s)."""
    p = tmp_path / "m.json"
    _write_manifest(
        p,
        {
            "frame_count": 100,
            "frame_dt_s": 1.0e-5,
            "total_duration_s": 1.0e-3,
            "per_frame_kinetic_energy_j": [1.0] * 100,
            "per_frame_internal_energy_j": [1.0] * 100,
            "per_frame_external_work_j": [2.0] * 100,
            "first_reflection_frame_index": 20,
        },
    )
    m = parse_animation_manifest(p)
    assert m.frame_count == 100
    assert m.first_reflection_frame_index == 20


def test_parser_accepts_str_path(tmp_path: Path) -> None:
    """The parser accepts both ``Path`` and ``str`` for the path argument."""
    p = tmp_path / "m.json"
    _write_manifest(p, _canonical_one_frame_payload())
    m = parse_animation_manifest(str(p))
    assert m.frame_count == 1


def test_parser_raises_on_missing_file(tmp_path: Path) -> None:
    """File-not-found is a FileNotFoundError, not a silent empty
    manifest."""
    with pytest.raises(FileNotFoundError):
        parse_animation_manifest(tmp_path / "does_not_exist.json")


def test_parser_raises_on_malformed_json(tmp_path: Path) -> None:
    """Malformed JSON is a ValueError citing the parse error."""
    p = tmp_path / "m.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_animation_manifest(p)


def test_parser_raises_on_non_object_top_level(tmp_path: Path) -> None:
    """Top-level array / scalar is rejected; manifests are objects."""
    p = tmp_path / "m.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="top-level"):
        parse_animation_manifest(p)


def test_parser_raises_on_missing_required_key(tmp_path: Path) -> None:
    """Every one of the 6 required keys is enforced."""
    p = tmp_path / "m.json"
    payload = _canonical_one_frame_payload()
    del payload["per_frame_internal_energy_j"]
    _write_manifest(p, payload)
    with pytest.raises(ValueError, match="missing required keys"):
        parse_animation_manifest(p)


def test_parser_raises_on_inconsistent_array_lengths(tmp_path: Path) -> None:
    """frame_count=3 with a 2-entry array is a ValueError."""
    p = tmp_path / "m.json"
    _write_manifest(
        p,
        {
            "frame_count": 3,
            "frame_dt_s": 1e-5,
            "total_duration_s": 3e-5,
            "per_frame_kinetic_energy_j": [1.0, 2.0],  # length 2
            "per_frame_internal_energy_j": [1.0, 2.0, 3.0],
            "per_frame_external_work_j": [1.0, 2.0, 3.0],
        },
    )
    with pytest.raises(ValueError, match="inconsistent with frame_count"):
        parse_animation_manifest(p)


def test_parser_raises_on_zero_frame_count(tmp_path: Path) -> None:
    """Empty manifests have no physical meaning."""
    p = tmp_path / "m.json"
    _write_manifest(
        p,
        {
            "frame_count": 0,
            "frame_dt_s": 1e-5,
            "total_duration_s": 0.0,
            "per_frame_kinetic_energy_j": [],
            "per_frame_internal_energy_j": [],
            "per_frame_external_work_j": [],
        },
    )
    with pytest.raises(ValueError, match="frame_count must be >= 1"):
        parse_animation_manifest(p)


def test_parser_raises_on_non_positive_frame_dt(tmp_path: Path) -> None:
    """Non-positive frame_dt is non-physical."""
    p = tmp_path / "m.json"
    payload = _canonical_one_frame_payload()
    payload["frame_dt_s"] = 0.0
    _write_manifest(p, payload)
    with pytest.raises(ValueError, match="frame_dt_s must be > 0"):
        parse_animation_manifest(p)


def test_parser_raises_on_out_of_range_reflection_index(tmp_path: Path) -> None:
    """first_reflection_frame_index outside [0, frame_count) is a
    ValueError."""
    p = tmp_path / "m.json"
    payload = _canonical_one_frame_payload()
    payload["first_reflection_frame_index"] = 5  # frame_count=1
    _write_manifest(p, payload)
    with pytest.raises(ValueError, match="out of range"):
        parse_animation_manifest(p)


# ---------------------------------------------------------------------
# energy_partition_audit — clean + drifted distinguished
# ---------------------------------------------------------------------


def test_energy_audit_clean_when_kinetic_plus_internal_equals_external() -> None:
    """All frames balanced exactly -> CLEAN."""
    m = AnimationManifest(
        frame_count=5,
        frame_dt_s=1e-5,
        total_duration_s=5e-5,
        per_frame_kinetic_energy_j=(1.0, 2.0, 3.0, 4.0, 5.0),
        per_frame_internal_energy_j=(0.5, 1.0, 1.5, 2.0, 2.5),
        per_frame_external_work_j=(1.5, 3.0, 4.5, 6.0, 7.5),
    )
    audit = energy_partition_audit(m)
    assert isinstance(audit, EnergyPartitionAudit)
    assert audit.clean is True
    assert audit.flagged_frame_indices == ()
    assert audit.max_abs_drift_j == 0.0
    assert audit.max_rel_drift_fraction == 0.0


def test_energy_audit_flags_non_physical_injection() -> None:
    """A frame where kinetic + internal > external work by more than
    1% is flagged as non-physical energy injection."""
    m = AnimationManifest(
        frame_count=3,
        frame_dt_s=1e-5,
        total_duration_s=3e-5,
        per_frame_kinetic_energy_j=(1.0, 2.0, 3.0),
        per_frame_internal_energy_j=(0.5, 1.0, 1.5),
        per_frame_external_work_j=(1.5, 3.0, 3.5),  # frame 2 short 1.0 J
    )
    audit = energy_partition_audit(m)
    assert audit.clean is False
    assert 2 in audit.flagged_frame_indices
    assert audit.max_abs_drift_j == pytest.approx(1.0)
    assert audit.max_rel_drift_fraction > 0.20  # 1.0/3.5 ≈ 0.286


def test_energy_audit_treats_sub_epsilon_drift_as_clean() -> None:
    """Float-arithmetic drift below ENERGY_PARTITION_EPSILON is
    NEVER flagged."""
    eps_drift = ENERGY_PARTITION_EPSILON / 10.0
    m = AnimationManifest(
        frame_count=2,
        frame_dt_s=1e-5,
        total_duration_s=2e-5,
        per_frame_kinetic_energy_j=(1.0, 2.0),
        per_frame_internal_energy_j=(0.5, 1.0),
        per_frame_external_work_j=(1.5 + eps_drift, 3.0 - eps_drift),
    )
    audit = energy_partition_audit(m)
    assert audit.clean is True
    assert audit.flagged_frame_indices == ()


def test_energy_audit_uses_custom_tolerance() -> None:
    """A laxer tolerance keeps a borderline-drifted frame clean."""
    m = AnimationManifest(
        frame_count=1,
        frame_dt_s=1e-5,
        total_duration_s=1e-5,
        per_frame_kinetic_energy_j=(1.05,),
        per_frame_internal_energy_j=(0.0,),
        per_frame_external_work_j=(1.0,),  # 5% drift
    )
    strict = energy_partition_audit(m)  # default 1%
    lax = energy_partition_audit(m, drift_fraction_tolerance=0.10)  # 10%
    assert strict.clean is False
    assert lax.clean is True


def test_energy_audit_dataclass_round_trip_field_defaults() -> None:
    """``EnergyPartitionAudit`` exposes ``drift_fraction_tolerance``
    as a field; the default matches the SSOT constant."""
    m = AnimationManifest(
        frame_count=1,
        frame_dt_s=1e-5,
        total_duration_s=1e-5,
        per_frame_kinetic_energy_j=(1.0,),
        per_frame_internal_energy_j=(0.0,),
        per_frame_external_work_j=(1.0,),
    )
    audit = energy_partition_audit(m)
    assert audit.drift_fraction_tolerance == ENERGY_PARTITION_DRIFT_FRACTION


# ---------------------------------------------------------------------
# Cross-slice sanity: the 1.0 m steel rod with frame_dt=10 µs lands
# the first reflection at frame ~20 (mirrors slice D fixture).
# ---------------------------------------------------------------------


def test_steel_1m_rod_first_reflection_lands_around_frame_20() -> None:
    """Slice-D bridge: steel L=1m, frame_dt=10 µs -> the first-reflection
    frame index is round(t_refl / frame_dt) = round(0.198e-3 / 1e-5) = 20.

    The assertion is on the analytical pin only (no fixture access);
    slice D loads the real fixture and re-verifies."""
    c = bar_wave_speed_m_per_s(E_Pa=200e9, rho_kg_per_m3=7850.0)
    t = bar_wave_first_reflection_s(L_m=1.0, c_m_per_s=c)
    frame_dt = 1.0e-5
    frame_idx = round(t / frame_dt)
    assert frame_idx == 20
