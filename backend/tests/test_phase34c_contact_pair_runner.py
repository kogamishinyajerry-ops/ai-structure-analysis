"""FM-04a Phase 34 C — *CONTACT PAIR validated case tests.

Phase 34 C ships the FIRST *CONTACT PAIR validated cross-check
under the FM-04a cohort. Cohort 11 → 12. Solver kind #6
contact_pair_static.

Tests cover:
  * 1D uniaxial analytical helper (closed-form δ = F·H/(E·A))
  * mesh-builder topology (two stacked C3D8 hex bodies, separate
    node IDs on the contact interface for master-slave alignment)
  * INP composer (key CCX keywords present + correct surface types)
  * verdict YAML schema 1.4.0 + solver_kind enum extension
  * @requires_solver E2E pin (live ccx run; gated by ccx availability)

Anti-gaming guards:
  * H:-1 — the @requires_solver E2E test invokes ccx for real; mock
    tests are forbidden for cohort-lift validation
  * D:-3 — analytical helper SSOT-pinned in contact_pair_runner.py;
    tests reuse via import
  * E:-1 — INP composer test reads the FILE OUTPUT, not the in-memory
    string, to catch encoding / line-ending bugs
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import yaml

from app.services.cross_check.contact_pair_runner import (
    CONTACT_PAIR_TOLERANCE_PCT,
    ContactPairCrossCheckResult,
    DEFAULT_CROSS_SECTION_M,
    DEFAULT_PUNCH_HEIGHT_M,
    DEFAULT_SUBSTRATE_HEIGHT_M,
    DEFAULT_TOTAL_LOAD_N,
    _bonded_uniaxial_indentation_m,
    _build_stacked_hex_mesh,
    _write_contact_pair_inp,
    run_contact_pair_cross_check,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
HERTZ_CASE_DIR = REPO_ROOT / "golden_samples" / "hertz-contact-candidate"


# ─── 1D uniaxial analytical helper ────────────────────────────────


def test_bonded_uniaxial_known_case() -> None:
    """4000 N on 20×20 mm with stack height 40 mm of E=210 GPa steel.

    δ = F·H/(E·A) = 4000 × 0.040 / (210e9 × 0.0004)
      = 160 / 8.4e7 = 1.9048e-6 m
    """
    delta = _bonded_uniaxial_indentation_m(
        total_load_n=4000.0,
        stack_height_m=0.040,
        youngs_modulus_pa=210e9,
        cross_section_m=0.020,
    )
    assert delta == pytest.approx(1.9048e-6, rel=1e-3)


def test_bonded_uniaxial_load_scaling_linear() -> None:
    """δ ∝ F for uniaxial compression."""
    d1 = _bonded_uniaxial_indentation_m(
        total_load_n=1000.0,
        stack_height_m=0.040,
        youngs_modulus_pa=210e9,
        cross_section_m=0.020,
    )
    d3 = _bonded_uniaxial_indentation_m(
        total_load_n=3000.0,
        stack_height_m=0.040,
        youngs_modulus_pa=210e9,
        cross_section_m=0.020,
    )
    assert d3 / d1 == pytest.approx(3.0, rel=1e-6)


def test_bonded_uniaxial_inverse_modulus_scaling() -> None:
    """δ ∝ 1/E for like materials."""
    soft = _bonded_uniaxial_indentation_m(
        total_load_n=1000.0,
        stack_height_m=0.040,
        youngs_modulus_pa=70e9,
        cross_section_m=0.020,
    )
    stiff = _bonded_uniaxial_indentation_m(
        total_load_n=1000.0,
        stack_height_m=0.040,
        youngs_modulus_pa=210e9,
        cross_section_m=0.020,
    )
    assert soft / stiff == pytest.approx(3.0, rel=1e-6)


# ─── Mesh-builder topology ────────────────────────────────────────


def test_mesh_builder_node_count() -> None:
    """4×4×2 punch + 4×4×6 substrate = (5×5×3) + (5×5×7) = 75 + 175 = 250."""
    nodes, *_ = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=4,
        n_z_punch=2,
        n_z_substrate=6,
    )
    assert len(nodes) == 250


def test_mesh_builder_element_count() -> None:
    """4×4×2 punch (32) + 4×4×6 substrate (96) = 128 hex."""
    _, elements, punch_eids, substrate_eids, *_ = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=4,
        n_z_punch=2,
        n_z_substrate=6,
    )
    assert len(elements) == 128
    assert len(punch_eids) == 32
    assert len(substrate_eids) == 96


def test_mesh_builder_contact_interface_has_distinct_node_ids() -> None:
    """The punch-bottom and substrate-top nodes occupy the same
    geometric (x,y,z) at z = h_substrate, but their NODE IDs are
    DISJOINT — this is what *CONTACT PAIR needs (two surfaces with
    coincident geometry, separate topology)."""
    (
        _nodes,
        _elements,
        _peids,
        _seids,
        punch_bottom_nodes,
        substrate_top_nodes,
        _stf,
        _pt,
        _sb,
        _probe,
    ) = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=4,
        n_z_punch=2,
        n_z_substrate=6,
    )
    assert set(punch_bottom_nodes).isdisjoint(set(substrate_top_nodes))
    # Same number of nodes on each side (aligned mesh).
    assert len(punch_bottom_nodes) == 25
    assert len(substrate_top_nodes) == 25


def test_mesh_builder_substrate_top_faces_use_s2_label() -> None:
    """Master surface for *CONTACT PAIR requires element-face
    notation; substrate top is the +Z face which is S2 in CCX C3D8."""
    *_, substrate_top_faces, _pt, _sb, _probe = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=4,
        n_z_punch=2,
        n_z_substrate=6,
    )
    # 4×4 = 16 element faces.
    assert len(substrate_top_faces) == 16
    for _, face_label in substrate_top_faces:
        assert face_label == "S2"


def test_mesh_builder_probe_node_is_at_punch_top_center(tmp_path) -> None:
    """Probe = (n_xy/2, n_xy/2, n_z_punch) of the punch grid → must
    be at (cross_section/2, cross_section/2, total_height)."""
    nodes, *_, probe = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=4,
        n_z_punch=2,
        n_z_substrate=6,
    )
    x, y, z = nodes[probe]
    assert x == pytest.approx(0.010, abs=1e-12)
    assert y == pytest.approx(0.010, abs=1e-12)
    assert z == pytest.approx(0.040, abs=1e-12)


# ─── INP composer ─────────────────────────────────────────────────


def test_inp_composer_emits_contact_pair_keywords(tmp_path) -> None:
    """INP must contain the CCX-canonical *CONTACT PAIR + *SURFACE
    INTERACTION + *SURFACE BEHAVIOR keyword triple."""
    (
        nodes,
        elements,
        peids,
        seids,
        pbot,
        stop,
        stf,
        ptop,
        sbot,
        _probe,
    ) = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=2,
        n_z_punch=1,
        n_z_substrate=2,
    )
    inp_path = _write_contact_pair_inp(
        tmp_path,
        jobname="test_inp",
        nodes=nodes,
        elements=elements,
        punch_element_ids=peids,
        substrate_element_ids=seids,
        punch_bottom_nodes=pbot,
        substrate_top_nodes=stop,
        substrate_top_faces=stf,
        punch_top_nodes=ptop,
        substrate_bottom_nodes=sbot,
        material_name="STEEL_TEST",
        youngs_modulus_pa=210e9,
        poisson_ratio=0.30,
        total_load_n=1000.0,
        contact_stiffness_n_per_m3=1.0e15,
    )
    inp_text = inp_path.read_text(encoding="utf-8")
    assert "*CONTACT PAIR" in inp_text
    assert "*SURFACE INTERACTION" in inp_text
    assert "*SURFACE BEHAVIOR" in inp_text
    assert "PRESSURE-OVERCLOSURE=LINEAR" in inp_text


def test_inp_composer_master_surface_is_element_type(tmp_path) -> None:
    """*CONTACT PAIR master MUST be TYPE=ELEMENT per CCX 2.23
    allocont check (slave can be TYPE=NODE for NODE TO SURFACE
    contact)."""
    (
        nodes,
        elements,
        peids,
        seids,
        pbot,
        stop,
        stf,
        ptop,
        sbot,
        _probe,
    ) = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=2,
        n_z_punch=1,
        n_z_substrate=2,
    )
    inp_path = _write_contact_pair_inp(
        tmp_path,
        jobname="test_inp",
        nodes=nodes,
        elements=elements,
        punch_element_ids=peids,
        substrate_element_ids=seids,
        punch_bottom_nodes=pbot,
        substrate_top_nodes=stop,
        substrate_top_faces=stf,
        punch_top_nodes=ptop,
        substrate_bottom_nodes=sbot,
        material_name="STEEL_TEST",
        youngs_modulus_pa=210e9,
        poisson_ratio=0.30,
        total_load_n=1000.0,
        contact_stiffness_n_per_m3=1.0e15,
    )
    inp_text = inp_path.read_text(encoding="utf-8")
    assert "*SURFACE, NAME=PUNCH_BOTTOM_S, TYPE=NODE" in inp_text
    assert "*SURFACE, NAME=SUBSTRATE_TOP_S, TYPE=ELEMENT" in inp_text
    # Each substrate element-face row uses S2 (+Z face of C3D8).
    assert ", S2" in inp_text


def test_inp_composer_emits_two_solid_section_blocks(tmp_path) -> None:
    """One *SOLID SECTION for the punch ELSET, one for the substrate."""
    (
        nodes,
        elements,
        peids,
        seids,
        pbot,
        stop,
        stf,
        ptop,
        sbot,
        _probe,
    ) = _build_stacked_hex_mesh(
        cross_section_m=0.020,
        punch_height_m=0.010,
        substrate_height_m=0.030,
        n_xy=2,
        n_z_punch=1,
        n_z_substrate=2,
    )
    inp_path = _write_contact_pair_inp(
        tmp_path,
        jobname="test_inp",
        nodes=nodes,
        elements=elements,
        punch_element_ids=peids,
        substrate_element_ids=seids,
        punch_bottom_nodes=pbot,
        substrate_top_nodes=stop,
        substrate_top_faces=stf,
        punch_top_nodes=ptop,
        substrate_bottom_nodes=sbot,
        material_name="STEEL_TEST",
        youngs_modulus_pa=210e9,
        poisson_ratio=0.30,
        total_load_n=1000.0,
        contact_stiffness_n_per_m3=1.0e15,
    )
    inp_text = inp_path.read_text(encoding="utf-8")
    assert "*SOLID SECTION, ELSET=PUNCH, MATERIAL=STEEL_TEST" in inp_text
    assert "*SOLID SECTION, ELSET=SUBSTRATE, MATERIAL=STEEL_TEST" in inp_text


# ─── Verdict YAML ─────────────────────────────────────────────────


def test_verdict_yaml_exists_and_is_valid() -> None:
    """cross_check_verdict.yaml must be present + parseable for the
    Phase 34 C validated case."""
    verdict_path = HERTZ_CASE_DIR / "cross_check_verdict.yaml"
    assert verdict_path.is_file(), f"missing {verdict_path}"
    data = yaml.safe_load(verdict_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.4.0"
    assert data["case_id"] == "hertz-contact-candidate"
    assert data["solver_kind"] == "contact_pair_static"
    assert data["tier_2_status"] == "validated"
    assert data["verdict_outcome"]["verdict"] == "PASS"


def test_verdict_yaml_cohort_count_bumps_11_to_12() -> None:
    verdict_path = HERTZ_CASE_DIR / "cross_check_verdict.yaml"
    data = yaml.safe_load(verdict_path.read_text(encoding="utf-8"))
    assert data["cohort_count_after_phase_34c"] == 12


def test_verdict_yaml_solver_kind_is_new_enum_entry() -> None:
    """contact_pair_static is the 6th solver kind in the cohort
    (after linear_static, modal, buckling, dynamic_implicit,
    heat_transfer_steady_state)."""
    verdict_path = HERTZ_CASE_DIR / "cross_check_verdict.yaml"
    data = yaml.safe_load(verdict_path.read_text(encoding="utf-8"))
    assert data["solver_kind"] == "contact_pair_static"


def test_verdict_yaml_documents_honest_pivot_from_hertz() -> None:
    """The case_kind is stacked-cube uniaxial, NOT Hertz curvature.
    The Phase 33 D Hertz analytical SSOT preservation should be
    documented in expected_results.json (companion file)."""
    expected_path = HERTZ_CASE_DIR / "expected_results.json"
    import json
    data = json.loads(expected_path.read_text(encoding="utf-8"))
    assert data["geometry"]["kind"] == "stacked_cube_uniaxial_contact"
    assert "phase_33_d_analytical_ssot_preserved" in data
    assert (
        "hertz_contact.py"
        in data["phase_33_d_analytical_ssot_preserved"]["module"]
    )


def test_residual_within_tolerance() -> None:
    """Phase 34 C session: residual -6.823% (within 20% tolerance)."""
    verdict_path = HERTZ_CASE_DIR / "cross_check_verdict.yaml"
    data = yaml.safe_load(verdict_path.read_text(encoding="utf-8"))
    res = data["verdict_outcome"]["residual_pct"]
    tol = data["verdict_outcome"]["tolerance_pct"]
    assert abs(res) <= tol


# ─── @requires_solver E2E ─────────────────────────────────────────


@pytest.mark.skipif(
    shutil.which("ccx") is None,
    reason="ccx not on PATH; @requires_solver E2E skipped",
)
def test_contact_pair_runner_live_ccx_e2e_pass(tmp_path) -> None:
    """E2E: run ccx for real on the stacked-cube contact case and
    assert PASS verdict at the default tolerance."""
    result = run_contact_pair_cross_check(
        tmp_path,
        case_id="hertz-contact-candidate",
        material_id="steel-s355",
    )
    assert isinstance(result, ContactPairCrossCheckResult)
    assert result.verdict == "PASS"
    assert abs(result.residual_pct) <= CONTACT_PAIR_TOLERANCE_PCT
    assert result.element_count == 128
    assert result.node_count == 250
    assert result.contact_pair_node_count == 50
