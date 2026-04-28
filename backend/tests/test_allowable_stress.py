"""Allowable-stress tests — RFC-001 W6b / ADR-020 §6.

Four buckets per ADR-020 §6, plus the conservative-gap regression
test:

1. GB materials produce sensible [σ] with full provenance fields
2. ASME materials produce sensible [σ] with full provenance fields
3. Cross-standard requests refuse with ValueError
4. High-T (T > range max) requests refuse with NotImplementedError
5. Conservative gap vs GB 150.3 Table 4 is pinned in [150, 170] MPa
   for Q345R room-T (regression — future drift requires ADR update)
"""

from __future__ import annotations

import math

import pytest
from app.core.types import Material, UnitSystem
from app.services.report.allowable_stress import (
    ASME_FACTOR_TABLE,
    GB_FACTOR_TABLE,
    AllowableStress,
    AllowableStressError,
    compute_allowable_stress,
)
from app.services.report.materials_lib import lookup_builtin

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _material(
    *,
    code_standard: str,
    code_grade: str,
    yield_strength: float,
    ultimate_strength: float,
) -> Material:
    """Build a Material with the W6b-relevant fields populated.

    The other fields (E, ν, density, citation) are filler — the
    allowable-stress path only consumes σ_y, σ_u, code_standard,
    code_grade.
    """
    return Material(
        name=code_grade,
        youngs_modulus=200_000.0,
        poissons_ratio=0.30,
        density=7.85e-9,
        yield_strength=yield_strength,
        ultimate_strength=ultimate_strength,
        code_standard=code_standard,
        code_grade=code_grade,
        source_citation="test fixture",
        unit_system=UnitSystem.SI_MM,
    )


# ---------------------------------------------------------------------------
# Bucket 1 — GB materials
# ---------------------------------------------------------------------------


def test_gb_q345b_room_temperature() -> None:
    """Q345B per GB: σ_y=345, σ_u=470 → min(345/1.5, 470/3.0) ≈ 156.67 MPa."""
    mat = _material(
        code_standard="GB",
        code_grade="Q345B",
        yield_strength=345.0,
        ultimate_strength=470.0,
    )
    res = compute_allowable_stress(mat, "GB", temperature_C=20.0)

    assert isinstance(res, AllowableStress)
    assert math.isclose(res.sigma_allow, min(345 / 1.5, 470 / 3.0), rel_tol=1e-9)
    assert res.code_standard == "GB"
    assert "GB 150" in res.code_clause
    assert "min" in res.formula_used.lower()
    assert res.inputs == {
        "sigma_y": 345.0,
        "sigma_u": 470.0,
        "temperature_C": 20.0,
    }
    assert res.is_simplified is True


def test_gb_q235b_room_temperature() -> None:
    """Q235B per GB: σ_y=235, σ_u=370 → min(235/1.5, 370/3.0) ≈ 123.33 MPa."""
    mat = _material(
        code_standard="GB",
        code_grade="Q235B",
        yield_strength=235.0,
        ultimate_strength=370.0,
    )
    res = compute_allowable_stress(mat, "GB")

    assert math.isclose(res.sigma_allow, min(235 / 1.5, 370 / 3.0), rel_tol=1e-9)


def test_gb_default_temperature_is_20C() -> None:
    """Calling without ``temperature_C`` records 20 °C in inputs."""
    mat = _material(
        code_standard="GB",
        code_grade="Q345B",
        yield_strength=345.0,
        ultimate_strength=470.0,
    )
    res = compute_allowable_stress(mat, "GB")

    assert res.inputs["temperature_C"] == 20.0


def test_gb_all_builtin_materials_compute() -> None:
    """Every GB entry in materials.json must produce a positive [σ]
    at room T. Catches a future row addition that breaks the
    formula (e.g. via a non-positive σ_y typo in the JSON)."""
    # All GB grades currently in materials.json (per data file).
    gb_grades = (
        "Q235B",
        "Q345B",
        "Q345R",
        "Q370R",
        "16MnR",
        "15CrMoR",
        "14Cr1MoR",
        "20#",
    )
    for grade in gb_grades:
        mat = lookup_builtin(grade)
        assert mat is not None, f"materials.json missing built-in {grade!r}"
        res = compute_allowable_stress(mat, "GB", temperature_C=20.0)
        assert res.sigma_allow > 0


# ---------------------------------------------------------------------------
# Bucket 2 — ASME materials
# ---------------------------------------------------------------------------


def test_asme_sa_516_70_room_temperature() -> None:
    """SA-516-70 per ASME: σ_y=260, σ_u=485 → min(260/1.5, 485/2.4) ≈ 173.33 MPa."""
    mat = _material(
        code_standard="ASME",
        code_grade="SA-516-70",
        yield_strength=260.0,
        ultimate_strength=485.0,
    )
    res = compute_allowable_stress(mat, "ASME", temperature_C=20.0)

    assert math.isclose(res.sigma_allow, min(260 / 1.5, 485 / 2.4), rel_tol=1e-9)
    assert res.code_standard == "ASME"
    assert "ASME" in res.code_clause


def test_asme_all_builtin_materials_compute() -> None:
    asme_grades = ("SA-516-70", "SA-105", "SA-106-B", "SA-387-Gr11-Cl2")
    for grade in asme_grades:
        mat = lookup_builtin(grade)
        assert mat is not None, f"materials.json missing built-in {grade!r}"
        res = compute_allowable_stress(mat, "ASME", temperature_C=20.0)
        assert res.sigma_allow > 0


# ---------------------------------------------------------------------------
# Bucket 3 — cross-standard refusal
# ---------------------------------------------------------------------------


def test_cross_standard_gb_material_with_asme_request_refuses() -> None:
    mat = _material(
        code_standard="GB",
        code_grade="Q345B",
        yield_strength=345.0,
        ultimate_strength=470.0,
    )
    with pytest.raises(AllowableStressError, match="cross-standard"):
        compute_allowable_stress(mat, "ASME")


def test_cross_standard_asme_material_with_gb_request_refuses() -> None:
    mat = _material(
        code_standard="ASME",
        code_grade="SA-516-70",
        yield_strength=260.0,
        ultimate_strength=485.0,
    )
    with pytest.raises(AllowableStressError, match="cross-standard"):
        compute_allowable_stress(mat, "GB")


def test_unknown_code_refuses() -> None:
    mat = _material(
        code_standard="EN",
        code_grade="P355GH",
        yield_strength=355.0,
        ultimate_strength=510.0,
    )
    with pytest.raises(AllowableStressError, match="unknown code"):
        # type: ignore[arg-type] — testing the runtime guard
        compute_allowable_stress(mat, "EN")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Bucket 4 — high-T refusal
# ---------------------------------------------------------------------------


def test_high_temperature_gb_refuses() -> None:
    """GB validity ends at 50 °C per the YAML; 60 °C must refuse."""
    mat = _material(
        code_standard="GB",
        code_grade="Q345B",
        yield_strength=345.0,
        ultimate_strength=470.0,
    )
    with pytest.raises(NotImplementedError, match="M4"):
        compute_allowable_stress(mat, "GB", temperature_C=60.0)


def test_high_temperature_asme_refuses() -> None:
    """ASME validity ends at 38 °C per the YAML; 50 °C must refuse."""
    mat = _material(
        code_standard="ASME",
        code_grade="SA-516-70",
        yield_strength=260.0,
        ultimate_strength=485.0,
    )
    with pytest.raises(NotImplementedError, match="M4"):
        compute_allowable_stress(mat, "ASME", temperature_C=50.0)


def test_low_temperature_below_range_refuses() -> None:
    """Below the YAML's ``min`` (e.g. -50 °C for GB) also refuses;
    the simplified factors are pinned to a documented band, not a
    one-sided cap."""
    mat = _material(
        code_standard="GB",
        code_grade="Q345B",
        yield_strength=345.0,
        ultimate_strength=470.0,
    )
    with pytest.raises(NotImplementedError):
        compute_allowable_stress(mat, "GB", temperature_C=-50.0)


def test_temperature_at_range_boundary_succeeds() -> None:
    """Both endpoints of the validity range are inclusive — picking
    the upper boundary (50 °C for GB) must compute, not refuse.
    Catches an off-by-one between ``<`` and ``<=`` in the guard."""
    mat = _material(
        code_standard="GB",
        code_grade="Q345B",
        yield_strength=345.0,
        ultimate_strength=470.0,
    )
    res_low = compute_allowable_stress(mat, "GB", temperature_C=-20.0)
    res_high = compute_allowable_stress(mat, "GB", temperature_C=50.0)
    assert res_low.sigma_allow > 0
    assert res_high.sigma_allow > 0


# ---------------------------------------------------------------------------
# Bucket 5 — conservative-gap regression (ADR-020 §6 explicit pin)
# ---------------------------------------------------------------------------


def test_simplified_vs_table4_conservative_gap_is_pinned() -> None:
    """ADR-020 §6 anchor: Q345R room-T simplified [σ] must land in
    [150, 170] MPa.

    For Q345R (σ_y=345, σ_u=510, per materials.json):
      simplified = min(345/1.5, 510/3.0) = min(230, 170) = **170.0** MPa.

    Note: ADR-020 §3 cites "156.7 MPa" for Q345R simplified, but
    that calculation in §3 mixed Q345R's σ_y (345) with Q345B's
    σ_u (470); the correct Q345R simplified value is 170.0 MPa.
    Per GB 150.3-2011 Table 4, Q345R published [σ] at room T is
    also ≈170 MPa, so the simplified formula and Table 4 happen to
    agree for this grade — there is *no* meaningful conservative
    gap at room T for Q345R. The "[150, 170] MPa" band still pins
    the value (a future drift outside this band signals either a
    materials.json change or a formula change, both of which need
    ADR review).

    Filed as a follow-up: ADR-020 §3 should be edited to either
    pick a different example material that genuinely shows a gap
    (e.g. 16MnR if its Table 4 value differs from simplified) or
    drop the "8-10%" wording since Q345R doesn't substantiate it.
    Out of scope for this W6b PR — no code change here would fix it.
    """
    mat = lookup_builtin("Q345R")
    assert mat is not None
    res = compute_allowable_stress(mat, "GB", temperature_C=20.0)

    assert 150.0 <= res.sigma_allow <= 170.0, (
        f"Q345R room-T simplified [σ] = {res.sigma_allow:.2f} MPa drifted "
        f"outside the [150, 170] band pinned in ADR-020 §6. Update the "
        f"ADR before changing this test."
    )
    # Sub-pin the actual computed value so a future formula tweak that
    # still lands in [150, 170] but moves Q345R can't slip silently.
    assert math.isclose(res.sigma_allow, 170.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Defensive: non-positive σ in a hand-built Material
# ---------------------------------------------------------------------------


def test_non_positive_yield_strength_refuses() -> None:
    """A hand-built Material with σ_y=0 (slipping past ADR-019's
    loader) must fail loudly here, not silently return 0 / 1.5 = 0."""
    mat = _material(
        code_standard="GB",
        code_grade="malformed",
        yield_strength=0.0,
        ultimate_strength=470.0,
    )
    with pytest.raises(AllowableStressError, match="non-positive"):
        compute_allowable_stress(mat, "GB")


# ---------------------------------------------------------------------------
# YAML-table contract sanity (catches data drift breaking the API)
# ---------------------------------------------------------------------------


def test_factor_tables_have_required_provenance_fields() -> None:
    """Both tables expose the keys the DOCX renderer (W6c) will read.
    These fields aren't enforced by the YAML loader (it only validates
    what the formula needs); pinning here protects W6c-side rendering."""
    for name, table in (("GB", GB_FACTOR_TABLE), ("ASME", ASME_FACTOR_TABLE)):
        assert "clause_citation" in table, name
        assert "formula" in table, name
        assert "rationale" in table["formula"], name


# ---------------------------------------------------------------------------
# Loader defensive paths (private API exercised directly so the
# error messages can't drift silently into the runtime)
# ---------------------------------------------------------------------------


from app.services.report.allowable_stress import _load_factor_table  # noqa: E402


def test_loader_rejects_missing_file(tmp_path) -> None:
    bogus = tmp_path / "nonexistent.yaml"
    with pytest.raises(AllowableStressError, match="not found"):
        _load_factor_table(bogus, code_label="TEST")


def test_loader_rejects_non_mapping_top(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(AllowableStressError, match="top-level"):
        _load_factor_table(p, code_label="TEST")


def test_loader_rejects_missing_top_keys(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("formula:\n  expression: foo\n", encoding="utf-8")
    with pytest.raises(AllowableStressError, match="missing required top-level"):
        _load_factor_table(p, code_label="TEST")


def test_loader_rejects_non_positive_safety_factor(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "formula:\n"
        "  expression: 'min(sigma_y/n, sigma_u/m)'\n"
        "  yield_safety_factor: 0\n"
        "  ultimate_safety_factor: 3.0\n"
        "temperature_range_celsius:\n"
        "  min: 0\n"
        "  max: 50\n"
        "clause_citation: x\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowableStressError, match="positive number"):
        _load_factor_table(p, code_label="TEST")


def test_loader_rejects_inverted_temperature_range(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "formula:\n"
        "  expression: 'min(sigma_y/n, sigma_u/m)'\n"
        "  yield_safety_factor: 1.5\n"
        "  ultimate_safety_factor: 3.0\n"
        "temperature_range_celsius:\n"
        "  min: 100\n"
        "  max: 50\n"
        "clause_citation: x\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowableStressError, match="min < max"):
        _load_factor_table(p, code_label="TEST")


def test_loader_rejects_non_mapping_formula(tmp_path) -> None:
    """`formula` must itself be a mapping; a list / scalar must be
    rejected so the formula-key validator never tries to subscript a
    non-mapping."""
    p = tmp_path / "bad.yaml"
    p.write_text(
        "formula:\n"
        "  - expression\n"
        "  - 1.5\n"
        "  - 3.0\n"
        "temperature_range_celsius:\n"
        "  min: 0\n"
        "  max: 50\n"
        "clause_citation: x\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowableStressError, match="'formula' must be a mapping"):
        _load_factor_table(p, code_label="TEST")


def test_loader_rejects_missing_formula_keys(tmp_path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "formula:\n"
        "  expression: 'min(...)'\n"  # missing yield/ultimate factors
        "temperature_range_celsius:\n"
        "  min: 0\n"
        "  max: 50\n"
        "clause_citation: x\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowableStressError, match="missing required 'formula'"):
        _load_factor_table(p, code_label="TEST")


def test_loader_rejects_temperature_range_non_mapping(tmp_path) -> None:
    """`temperature_range_celsius` must be a mapping (not a list /
    string) so the min/max validator never crashes on an unexpected
    type."""
    p = tmp_path / "bad.yaml"
    p.write_text(
        "formula:\n"
        "  expression: 'min(...)'\n"
        "  yield_safety_factor: 1.5\n"
        "  ultimate_safety_factor: 3.0\n"
        "temperature_range_celsius: '0..50'\n"
        "clause_citation: x\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowableStressError, match="temperature_range_celsius"):
        _load_factor_table(p, code_label="TEST")


def test_loader_rejects_temperature_range_non_numeric(tmp_path) -> None:
    """min/max must be numeric — strings or None must reject before
    the min < max comparison runs."""
    p = tmp_path / "bad.yaml"
    p.write_text(
        "formula:\n"
        "  expression: 'min(...)'\n"
        "  yield_safety_factor: 1.5\n"
        "  ultimate_safety_factor: 3.0\n"
        "temperature_range_celsius:\n"
        "  min: 'cold'\n"
        "  max: 50\n"
        "clause_citation: x\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowableStressError, match="temperature_range_celsius"):
        _load_factor_table(p, code_label="TEST")


# ---------------------------------------------------------------------------
# Deep-immutability regression — Codex R1 MEDIUM
# ---------------------------------------------------------------------------


def test_factor_tables_are_deep_frozen() -> None:
    """Codex R1 (gpt-5.4 xhigh) demonstrated that wrapping only the
    top-level YAML object in MappingProxyType left
    ``GB_FACTOR_TABLE['formula']`` mutable, so an attacker / buggy
    caller could change ``yield_safety_factor`` mid-process and
    silently corrupt every subsequent allowable-stress computation
    (Q345B dropped from 156.67 MPa to 38.33 MPa in their POC).

    Pin: nested dicts under both factor tables MUST raise TypeError
    when mutated. If a future change reverts to shallow proxying
    this test will fail loudly.
    """
    for _name, table in (("GB", GB_FACTOR_TABLE), ("ASME", ASME_FACTOR_TABLE)):
        # Top level frozen
        with pytest.raises(TypeError):
            table["formula"] = {}  # type: ignore[index]
        # Nested 'formula' sub-mapping frozen
        with pytest.raises(TypeError):
            table["formula"]["yield_safety_factor"] = 0.001  # type: ignore[index]
        # Nested 'temperature_range_celsius' sub-mapping frozen
        with pytest.raises(TypeError):
            table["temperature_range_celsius"]["max"] = 9999  # type: ignore[index]


def test_factor_tables_compute_unchanged_after_attempted_mutation() -> None:
    """Even if a caller catches the TypeError from the mutation
    attempt, the factor tables and derived [σ] must remain at their
    YAML-pinned values. Belt-and-braces against a future regression
    that lets mutation through silently."""
    mat = _material(
        code_standard="GB",
        code_grade="Q345B",
        yield_strength=345.0,
        ultimate_strength=470.0,
    )
    expected = compute_allowable_stress(mat, "GB").sigma_allow

    # Try every plausible mutation; each must raise. We assert through
    # `pytest.raises` so the test fails loudly if any mutation slips
    # through (which would mean the deep-freeze regressed).
    with pytest.raises(TypeError):
        GB_FACTOR_TABLE["formula"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        GB_FACTOR_TABLE["formula"]["yield_safety_factor"] = 0.001  # type: ignore[index]

    again = compute_allowable_stress(mat, "GB").sigma_allow
    assert math.isclose(again, expected, rel_tol=1e-12)
