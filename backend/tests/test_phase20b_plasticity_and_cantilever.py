"""FM-04a Phase 20 B — plasticity *PLASTIC + cantilever cross-check.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

Pins both Phase 20 B sub-deliverables:

* **Plasticity** — the materials library carries optional
  ``plastic_hardening_curve`` data; the loader validates monotonicity
  + non-negativity + yield-anchor consistency; the INP writer emits
  a ``*PLASTIC`` block when the curve is present (so ccx auto-
  promotes to a nonlinear run).
* **Cantilever cross-check (analytical half)** — the Euler-Bernoulli
  ``δ = PL³/(3EI)`` formula is pinned per-input; the slender-beam
  validity envelope is enforced; ``cantilever-beam-candidate`` is
  added to ``CLAIM_TIER_REGISTRY`` as tier_1 baseline. The
  ccx-running ``cantilever_runner`` is Phase 21+ scope (single-hex
  coupons cannot capture bending; Slice C's Gmsh-meshed pipeline
  delivers the multi-element route).

Anti-gaming guards:
* (M:-1) Plasticity curves load through the SSOT library — no inline
  duplication of curve data in tests; tests assert per-row values
  via ``get_material``.
* (C:-1) Each hardening curve cites a real engineering standard with
  section number in the material's ``reference`` field.
* (T:-3) Cantilever analytical formula pinned on KNOWN inputs with
  hand-computed expected δ_tip.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.adapters.calculix import (
    DEFAULT_STEEL,
    MinimalHexMaterial,
    write_minimal_hex_inp,
)
from app.services.cross_check import (
    CANTILEVER_ASPECT_RATIO_MIN,
    CantileverValidityError,
    assert_slender_beam_envelope,
    compute_analytical_tip_deflection,
)
from app.services.materials import (
    MaterialLibraryError,
    get_material,
    list_materials,
    load_library,
)
from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY
from app.services.tier2_pipeline import material_to_hex_descriptor


# ---------------------------------------------------------------------
# Plasticity — Material dataclass + library loader
# ---------------------------------------------------------------------


def test_steel_s355_carries_bilinear_hardening_curve() -> None:
    """C:-1 / M:-1 — steel-S355 has a 2-row bilinear curve pinned to
    yield + ultimate from EN 1993-1-5 Annex C.6."""
    mat = get_material("steel-s355")
    assert mat.plastic_hardening_curve is not None
    assert len(mat.plastic_hardening_curve) == 2
    # Row 0 anchors at yield (0 plastic strain).
    assert mat.plastic_hardening_curve[0] == (0.0, 355_000_000.0)
    # Row 1 is the ultimate (510 MPa at 20% plastic strain — EN
    # 1993-1-5 Annex C bilinear approximation).
    assert mat.plastic_hardening_curve[1] == (0.2, 510_000_000.0)
    # Reference field cites the standard with section number.
    assert "EN 1993-1-5" in mat.reference
    assert "C.6" in mat.reference


def test_aluminium_6061_t6_carries_bilinear_hardening_curve() -> None:
    """C:-1 — aluminium-6061-T6 has a 2-row curve anchored to MMPDS
    yield + ultimate."""
    mat = get_material("aluminium-6061-t6")
    assert mat.plastic_hardening_curve is not None
    assert mat.plastic_hardening_curve[0] == (0.0, 276_000_000.0)
    assert mat.plastic_hardening_curve[1] == (0.12, 310_000_000.0)
    assert "MMPDS-2023 §9.2" in mat.reference


def test_titanium_has_no_hardening_curve() -> None:
    """Phase 20 B only ships curves for steel-s355 + aluminium-6061-t6.
    Confirm titanium (and other 6 materials) stay None so the INP
    writer's elastic-only path remains the default."""
    mat = get_material("titanium-ti-6al-4v")
    assert mat.plastic_hardening_curve is None


def test_at_least_six_of_eight_materials_have_no_curve_yet() -> None:
    """Honest scope: Phase 20 B adds curves to 2 of 8 materials.
    Pinning the count so a future drive-by edit that adds an unsourced
    curve to a third material trips the test."""
    materials_with_curve = [
        m for m in list_materials() if m.plastic_hardening_curve is not None
    ]
    assert len(materials_with_curve) == 2
    ids_with_curve = {m.id for m in materials_with_curve}
    assert ids_with_curve == {"steel-s355", "aluminium-6061-t6"}


def test_loader_rejects_non_monotonic_curve(tmp_path: Path) -> None:
    """A:-2 — a curve with decreasing plastic strain is refused at
    load time (the SSOT loader is the audit boundary, not the runner)."""
    bad_lib = tmp_path / "bad.json"
    bad_lib.write_text(
        """
        {
          "schema_version": "1.0.0",
          "materials": [
            {
              "id": "bad-curve",
              "name": "Bad",
              "youngs_modulus_pa": 1e9,
              "poisson_ratio": 0.3,
              "density_kg_m3": 1000.0,
              "yield_stress_pa": 1e6,
              "reference": "test",
              "plastic_hardening_curve": [
                [0.0, 1000000.0],
                [0.1, 2000000.0],
                [0.05, 1500000.0]
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(MaterialLibraryError, match="strictly increasing"):
        load_library(bad_lib)


def test_loader_rejects_curve_without_yield_anchor(tmp_path: Path) -> None:
    """A:-2 — first curve row must anchor at plastic_strain=0."""
    bad_lib = tmp_path / "bad.json"
    bad_lib.write_text(
        """
        {
          "schema_version": "1.0.0",
          "materials": [
            {
              "id": "bad-anchor",
              "name": "Bad",
              "youngs_modulus_pa": 1e9,
              "poisson_ratio": 0.3,
              "density_kg_m3": 1000.0,
              "yield_stress_pa": 1e6,
              "reference": "test",
              "plastic_hardening_curve": [
                [0.01, 1000000.0],
                [0.1, 2000000.0]
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(MaterialLibraryError, match="anchor at"):
        load_library(bad_lib)


def test_loader_rejects_curve_first_row_stress_not_matching_yield(
    tmp_path: Path,
) -> None:
    """A:-2 — first curve row stress must equal yield_stress_pa
    (anti-drift: prevents a future edit from declaring a yield of
    300 MPa while the curve says yield-at-strain-0 is 250 MPa)."""
    bad_lib = tmp_path / "bad.json"
    bad_lib.write_text(
        """
        {
          "schema_version": "1.0.0",
          "materials": [
            {
              "id": "bad-stress",
              "name": "Bad",
              "youngs_modulus_pa": 1e9,
              "poisson_ratio": 0.3,
              "density_kg_m3": 1000.0,
              "yield_stress_pa": 300000000.0,
              "reference": "test",
              "plastic_hardening_curve": [
                [0.0, 250000000.0],
                [0.1, 350000000.0]
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(MaterialLibraryError, match="must equal"):
        load_library(bad_lib)


def test_loader_rejects_negative_strain(tmp_path: Path) -> None:
    """A:-2 — negative plastic_strain is physically invalid."""
    bad_lib = tmp_path / "bad.json"
    bad_lib.write_text(
        """
        {
          "schema_version": "1.0.0",
          "materials": [
            {
              "id": "bad-neg",
              "name": "Bad",
              "youngs_modulus_pa": 1e9,
              "poisson_ratio": 0.3,
              "density_kg_m3": 1000.0,
              "yield_stress_pa": 1e6,
              "reference": "test",
              "plastic_hardening_curve": [
                [-0.01, 1000000.0],
                [0.0, 1500000.0]
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(MaterialLibraryError, match="negative plastic_strain"):
        load_library(bad_lib)


# ---------------------------------------------------------------------
# INP writer emits *PLASTIC when curve present
# ---------------------------------------------------------------------


def test_inp_writer_emits_plastic_block_for_steel_s355(tmp_path: Path) -> None:
    """T:-3 — when material has a hardening curve, the INP body
    contains the *PLASTIC keyword followed by the curve rows in
    CalculiX's ``stress, plastic_strain`` column order."""
    steel_mat = get_material("steel-s355")
    hex_mat = material_to_hex_descriptor(steel_mat)
    inp_path = write_minimal_hex_inp(
        tmp_path, jobname="plast", material=hex_mat
    )
    body = inp_path.read_text(encoding="utf-8")
    assert "*PLASTIC" in body
    # Stress comes first in CalculiX *PLASTIC, plastic_strain second.
    # Row 1: yield = 355 MPa @ 0 strain
    assert "3.550000e+08, 0.000000" in body
    # Row 2: ultimate = 510 MPa @ 0.20 strain
    assert "5.100000e+08, 0.200000" in body


def test_inp_writer_no_plastic_block_when_curve_absent(tmp_path: Path) -> None:
    """Back-compat — Phase 18 A default steel + every non-Phase-20-B
    material produces an ELASTIC-only INP."""
    inp_path = write_minimal_hex_inp(
        tmp_path, jobname="elas", material=DEFAULT_STEEL
    )
    body = inp_path.read_text(encoding="utf-8")
    assert "*ELASTIC" in body
    assert "*PLASTIC" not in body


def test_inp_writer_plastic_block_appears_after_elastic(tmp_path: Path) -> None:
    """Order matters: ccx requires *ELASTIC before *PLASTIC."""
    steel_mat = get_material("steel-s355")
    hex_mat = material_to_hex_descriptor(steel_mat)
    inp_path = write_minimal_hex_inp(
        tmp_path, jobname="order", material=hex_mat
    )
    body = inp_path.read_text(encoding="utf-8")
    elastic_pos = body.index("*ELASTIC")
    plastic_pos = body.index("*PLASTIC")
    assert elastic_pos < plastic_pos


def test_minimal_hex_material_can_carry_inline_curve(tmp_path: Path) -> None:
    """Sanity: the MinimalHexMaterial dataclass accepts an inline
    curve (so Phase 18 A inline defaults can be extended with
    plasticity by hand without going through the library JSON)."""
    inline_mat = MinimalHexMaterial(
        name="INLINE_BILINEAR",
        youngs_modulus_pa=200e9,
        poisson_ratio=0.3,
        plastic_hardening_curve=((0.0, 250e6), (0.10, 400e6)),
    )
    inp_path = write_minimal_hex_inp(
        tmp_path, jobname="inline", material=inline_mat
    )
    body = inp_path.read_text(encoding="utf-8")
    assert "*MATERIAL, NAME=INLINE_BILINEAR" in body
    assert "*PLASTIC" in body
    assert "2.500000e+08, 0.000000" in body
    assert "4.000000e+08, 0.100000" in body


# ---------------------------------------------------------------------
# Cantilever cross-check — analytical formula
# ---------------------------------------------------------------------


def test_cantilever_formula_known_input() -> None:
    """T:-3 — pin δ_tip = PL³/(3EI) on a known hand-computed input.

    L=1 m, E=210e9 Pa, I=8.3333e-6 m⁴ (h=0.1 m square section,
    I = bh³/12 = 0.1·0.001/12), P=-1000 N (downward)
    → δ_tip = (-1000)·1³ / (3·210e9·8.3333e-6)
            = -1000 / 5.25e6
            = -1.9048e-4 m  (-0.19 mm).
    """
    delta = compute_analytical_tip_deflection(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=8.3333e-6,
        tip_load_n=-1000.0,
    )
    # 5e-9 m absolute tolerance covers I truncation to 4 sig figs.
    assert delta == pytest.approx(-1.9048e-4, abs=5e-9)


def test_cantilever_formula_sign_preserved() -> None:
    """Positive load → positive deflection in the load direction."""
    delta_up = compute_analytical_tip_deflection(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=8.3333e-6,
        tip_load_n=+1000.0,
    )
    assert delta_up > 0


def test_cantilever_formula_scales_linear_with_load() -> None:
    """Linear elastic — doubling P doubles δ_tip."""
    base = compute_analytical_tip_deflection(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=8.3333e-6,
        tip_load_n=-1000.0,
    )
    doubled = compute_analytical_tip_deflection(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=8.3333e-6,
        tip_load_n=-2000.0,
    )
    assert doubled == pytest.approx(2.0 * base, rel=1e-9)


def test_cantilever_formula_scales_cubically_with_length() -> None:
    """δ ∝ L³ — doubling L gives 8× δ_tip."""
    base = compute_analytical_tip_deflection(
        length_m=1.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=8.3333e-6,
        tip_load_n=-1000.0,
    )
    doubled_length = compute_analytical_tip_deflection(
        length_m=2.0,
        youngs_modulus_pa=210e9,
        second_moment_m4=8.3333e-6,
        tip_load_n=-1000.0,
    )
    assert doubled_length == pytest.approx(8.0 * base, rel=1e-9)


@pytest.mark.parametrize(
    "kwarg,value",
    [
        ("length_m", 0.0),
        ("length_m", -1.0),
        ("youngs_modulus_pa", 0.0),
        ("youngs_modulus_pa", -1.0),
        ("second_moment_m4", 0.0),
        ("second_moment_m4", -1.0e-9),
    ],
)
def test_cantilever_formula_rejects_non_positive_inputs(
    kwarg: str, value: float
) -> None:
    """A:-2 — geometric / material inputs must be strictly positive."""
    defaults = {
        "length_m": 1.0,
        "youngs_modulus_pa": 210e9,
        "second_moment_m4": 8.3333e-6,
        "tip_load_n": -1000.0,
    }
    defaults[kwarg] = value
    with pytest.raises(ValueError):
        compute_analytical_tip_deflection(**defaults)


def test_slender_beam_envelope_accepts_aspect_ratio_10() -> None:
    """L/h = 10 is the threshold — should pass."""
    assert_slender_beam_envelope(length_m=1.0, section_depth_m=0.1)


def test_slender_beam_envelope_rejects_short_beam() -> None:
    """L/h = 5 is below the slender threshold; raise with a citation
    hint pointing at the Timoshenko shear correction."""
    with pytest.raises(CantileverValidityError, match="Timoshenko"):
        assert_slender_beam_envelope(length_m=0.5, section_depth_m=0.1)


def test_aspect_ratio_min_constant_pinned() -> None:
    """SSOT constant should not drift silently."""
    assert CANTILEVER_ASPECT_RATIO_MIN == 10.0


# ---------------------------------------------------------------------
# Cantilever-beam-candidate registry entry
# ---------------------------------------------------------------------


def test_cantilever_beam_candidate_registered() -> None:
    """Phase 20 B added the case to the registry as tier_1_candidate;
    Phase 21 A's `cantilever_runner` promotes it to tier_2_validated
    when the verdict YAML is present. The post-promotion pin lives in
    `test_phase21a_cantilever_kirsch_runners.py
    ::test_phase21a_validated_count_is_three`. Here we accept either
    tier so the test survives the promotion."""
    tier = CLAIM_TIER_REGISTRY["cantilever-beam-candidate"]
    assert tier in {"tier_1_candidate", "tier_2_validated"}


def test_cantilever_beam_candidate_notes_md_exists() -> None:
    """Honest scope: the candidate dir + NOTES.md must be on disk so
    the reviewer can find the case + understand what was/wasn't
    delivered in Phase 20 B."""
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    notes = (
        repo_root / "golden_samples" / "cantilever-beam-candidate" / "NOTES.md"
    )
    assert notes.is_file(), f"missing {notes}"
    body = notes.read_text(encoding="utf-8")
    assert "Euler-Bernoulli" in body
    assert "Phase 21" in body  # Honest scope disclosure required.
    assert "-1.9048e-4" in body  # The pinned analytical answer.
