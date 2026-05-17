"""FM-04a Phase 19 C — materials breadth (3→8) + modal analysis tests.

Pins:

* **M:-1** library.json remains the single SSOT; each new entry pinned
  by per-material values tests (Phase 19 C parametrises across the 5
  new entries).
* **C:-1** every new material cites a real standard with section
  number; loader still refuses any entry without a reference.
* **T:-3** modal end-to-end pin (`requires_solver`): real ccx
  `*FREQUENCY` step produces 5 ascending positive eigenfrequencies
  parsed from the .dat file.
* **A:-3** modal doesn't regress static; the two paths produce
  different artifact shapes (no cross-contamination).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.adapters.calculix import (
    DEFAULT_STEEL,
    MinimalHexMaterial,
    write_minimal_hex_inp,
    write_modal_hex_inp,
)
from app.services.materials import get_material, list_materials
from app.services.modal_frequencies import extract_eigen_frequencies

LOCAL_CCX_BINARY = "/opt/homebrew/bin/ccx"


# ---------------------------------------------------------------------
# Materials breadth — library now has 8 entries
# ---------------------------------------------------------------------


def test_library_now_has_eight_entries() -> None:
    """Phase 19 C — library grew from 3 → 8."""
    assert len(list_materials()) == 8


def test_library_ids_in_phase_19c_order() -> None:
    """Phase 18 C baseline 3 at the head; Phase 19 C additions appended
    in commit order so the file diff is readable."""
    ids = [m.id for m in list_materials()]
    assert ids == [
        "steel-s355",
        "aluminium-6061-t6",
        "titanium-ti-6al-4v",
        "steel-s275",
        "stainless-304",
        "cast-iron-grade-250",
        "bronze-c93200",
        "inconel-718",
    ]


# Per-material value pins for the 5 new entries (M:-1 anti-drift).
@pytest.mark.parametrize(
    "material_id,e_pa,nu,rho,yield_pa,ultimate_pa",
    [
        ("steel-s275", 210e9, 0.3, 7850.0, 275e6, 430e6),
        ("stainless-304", 193e9, 0.29, 8000.0, 215e6, 505e6),
        ("cast-iron-grade-250", 100e9, 0.26, 7200.0, 165e6, 250e6),
        ("bronze-c93200", 100e9, 0.34, 8930.0, 125e6, 240e6),
        ("inconel-718", 200e9, 0.294, 8190.0, 1034e6, 1241e6),
    ],
)
def test_new_material_values_pinned(
    material_id: str,
    e_pa: float,
    nu: float,
    rho: float,
    yield_pa: float,
    ultimate_pa: float,
) -> None:
    """Per-material exact-value pin so a silent library edit trips
    the test. The pinned values are what the citation says; changing
    them requires editing both library.json AND the test."""
    mat = get_material(material_id)
    assert mat.youngs_modulus_pa == e_pa
    assert mat.poisson_ratio == nu
    assert mat.density_kg_m3 == rho
    assert mat.yield_stress_pa == yield_pa
    assert mat.ultimate_stress_pa == ultimate_pa


@pytest.mark.parametrize(
    "material_id,citation_substring",
    [
        ("steel-s275", "EN 10025-2:2019"),
        ("stainless-304", "ASM Specialty Handbook"),
        ("cast-iron-grade-250", "ASTM A48"),
        ("bronze-c93200", "SAE J462"),
        ("inconel-718", "AMS 5662"),
    ],
)
def test_new_material_carries_standard_citation(
    material_id: str, citation_substring: str
) -> None:
    """C:-1 — each new entry cites a real engineering standard with
    section info; substring pinned so a TODO/placeholder swap trips."""
    mat = get_material(material_id)
    assert citation_substring in mat.reference


@pytest.mark.parametrize(
    "material_id",
    [
        "steel-s275",
        "stainless-304",
        "cast-iron-grade-250",
        "bronze-c93200",
        "inconel-718",
    ],
)
def test_new_material_ultimate_at_least_yield(material_id: str) -> None:
    """Sanity invariant the loader enforces — checked here per-entry
    so the diagnostic is per-material when a future edit breaks it."""
    mat = get_material(material_id)
    assert mat.ultimate_stress_pa is not None
    assert mat.yield_stress_pa is not None
    assert mat.ultimate_stress_pa >= mat.yield_stress_pa


def test_all_eight_materials_have_distinct_ids() -> None:
    ids = [m.id for m in list_materials()]
    assert len(set(ids)) == len(ids)


# ---------------------------------------------------------------------
# Modal INP writer shape
# ---------------------------------------------------------------------


def test_modal_inp_carries_required_sections(tmp_path: Path) -> None:
    path = write_modal_hex_inp(
        tmp_path, jobname="modal", num_modes=5
    )
    body = path.read_text(encoding="utf-8")
    for required in (
        "*HEADING",
        "*NODE",
        "*ELEMENT, TYPE=C3D8",
        "*MATERIAL, NAME=STEEL_S355",
        "*ELASTIC",
        "*DENSITY",
        "*BOUNDARY",
        "*STEP",
        "*FREQUENCY",
        "*END STEP",
    ):
        assert required in body, f"modal INP missing required section {required!r}"


def test_modal_inp_requested_num_modes_in_body(tmp_path: Path) -> None:
    """The modal step carries the requested num_modes count on the
    line after *FREQUENCY."""
    path = write_modal_hex_inp(tmp_path, jobname="m", num_modes=7)
    body = path.read_text(encoding="utf-8")
    # *FREQUENCY then line carrying just `7` on its own line.
    assert "*FREQUENCY" in body
    lines = body.splitlines()
    freq_idx = next(i for i, l in enumerate(lines) if l.strip() == "*FREQUENCY")
    assert lines[freq_idx + 1].strip() == "7"


def test_modal_inp_writer_refuses_missing_case_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        write_modal_hex_inp(tmp_path / "missing", jobname="m")


def test_modal_inp_writer_refuses_zero_num_modes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="num_modes"):
        write_modal_hex_inp(tmp_path, jobname="m", num_modes=0)


def test_modal_inp_writer_refuses_nonpositive_density(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="density_kg_m3"):
        write_modal_hex_inp(tmp_path, jobname="m", density_kg_m3=0)


# ---------------------------------------------------------------------
# A:-3 — modal vs static produce distinct artifact shapes
# ---------------------------------------------------------------------


def test_modal_and_static_inp_shapes_differ(tmp_path: Path) -> None:
    """Same geometry, different step → static INP contains *STATIC +
    *CLOAD; modal INP contains *FREQUENCY + *DENSITY. The two paths
    cannot be confused for each other by a casual diff."""
    static_path = write_minimal_hex_inp(tmp_path, jobname="s")
    modal_path = write_modal_hex_inp(tmp_path, jobname="m", num_modes=3)
    static_body = static_path.read_text(encoding="utf-8")
    modal_body = modal_path.read_text(encoding="utf-8")
    assert "*STATIC" in static_body
    assert "*STATIC" not in modal_body
    assert "*FREQUENCY" in modal_body
    assert "*FREQUENCY" not in static_body
    assert "*DENSITY" in modal_body
    assert "*DENSITY" not in static_body
    assert "*CLOAD" in static_body
    assert "*CLOAD" not in modal_body


# ---------------------------------------------------------------------
# Eigenfrequency parser — synthetic .dat
# ---------------------------------------------------------------------


def test_extract_eigen_frequencies_parses_clean_dat(tmp_path: Path) -> None:
    """Synthetic CalculiX-style .dat snippet with 3 modes; parser
    returns frequencies in ascending order."""
    body = """\
\n     E I G E N V A L U E   N U M B E R
\n\n      MODE NO     EIGENVALUE             ANGULAR FREQ  FREQUENCY    PERIOD
\n            1   1.234560E+06   1.111100E+03   1.768500E+02   5.654400E-03
\n            2   4.938240E+06   2.222200E+03   3.537000E+02   2.827200E-03
\n            3   1.111100E+07   3.333000E+03   5.305000E+02   1.884900E-03
"""
    path = tmp_path / "synth.dat"
    path.write_text(body, encoding="utf-8")
    freqs = extract_eigen_frequencies(path)
    assert freqs == sorted(freqs)
    assert len(freqs) == 3
    assert freqs[0] == pytest.approx(176.85, rel=1e-4)
    assert freqs[1] == pytest.approx(353.70, rel=1e-4)
    assert freqs[2] == pytest.approx(530.50, rel=1e-4)


def test_extract_eigen_frequencies_returns_empty_when_no_block(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.dat"
    path.write_text("\n*nothing here*\n", encoding="utf-8")
    assert extract_eigen_frequencies(path) == []


def test_extract_eigen_frequencies_refuses_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        extract_eigen_frequencies(tmp_path / "nope.dat")


# ---------------------------------------------------------------------
# T:-3 — real-ccx modal end-to-end pin (requires_solver)
# ---------------------------------------------------------------------


@pytest.mark.requires_solver
def test_real_ccx_modal_run_produces_ascending_positive_frequencies(
    tmp_path: Path,
) -> None:
    """The load-bearing pin: write a modal INP → real ccx → 5 ascending
    positive frequencies in the .dat file. A malformed modal step
    would exit 0 but produce 0 modes; this catches that."""
    from app.adapters.calculix import CalculiXRunner

    case_dir = tmp_path / "phase19c-modal-candidate"
    case_dir.mkdir()
    write_modal_hex_inp(
        case_dir,
        jobname="modal5",
        material=DEFAULT_STEEL,
        edge_length_m=0.1,
        density_kg_m3=7850.0,
        num_modes=5,
    )
    runner = CalculiXRunner(ccx_binary=LOCAL_CCX_BINARY, timeout_sec=60.0)
    result = runner.run(case_dir, "modal5")
    assert result.returncode == 0
    assert result.dat_path is not None
    freqs = extract_eigen_frequencies(result.dat_path)
    assert len(freqs) == 5, f"expected 5 modes, got {len(freqs)}: {freqs}"
    for f in freqs:
        assert f > 0, f"all eigenfrequencies should be positive; got {freqs}"
    assert freqs == sorted(freqs), (
        f"eigenfrequencies should be ascending; got {freqs}"
    )
