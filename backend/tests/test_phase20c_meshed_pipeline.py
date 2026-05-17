"""FM-04a Phase 20 C — Gmsh + STEP → Tier 2 meshed pipeline.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

Closes the Phase 19 E "Mesh-fidelity 6/20" finding by ending the
single-element-coupon regime: real CAD geometry (`.geo`/`.step`) is
now meshed by gmsh into C3D4 tets, parsed into a `ParsedMesh`, written
to a CalculiX INP, and solved by ccx — all wired through one entry
point `tier2_pipeline.run_tier2_meshed_pipeline`.

Anti-gaming guards:
* (T:-3) Mesh-to-INP byte pin: a known 1-cube .msh fixture produces
  an INP body with the expected `*NODE` rows + `*ELEMENT, TYPE=C3D4`
  rows + `*BOUNDARY` clamped node list + `*CLOAD` loaded node list.
* (A:-2) Malformed .msh files (wrong version, no volume elements,
  binary format) surface :class:`MeshParseError` with a citation
  pointing the caller at the right gmsh format flag.
* (A:-2) BC / load plane selecting zero nodes raises `ValueError`
  before the INP is written (prevents silently shipping a model with
  no constraints / no load).
* (T:-3 requires_solver) end-to-end pin: the canonical plate-with-hole
  geometry → real gmsh → real ccx → non-zero tensile displacement
  field. Verifies the whole composition works in production.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.adapters.calculix import (
    BoundaryConditionSpec,
    DEFAULT_STEEL,
    LoadSpec,
    MeshParseError,
    MinimalHexMaterial,
    ParsedMesh,
    PlanarSelection,
    parse_gmsh_msh22,
    write_meshed_static_inp,
)
from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY


# ---------------------------------------------------------------------
# Fixture: known 1-cube .msh body (gmsh v2.2 ASCII format).
# Six C3D4 tets tile the unit cube exactly; this is a minimal but
# real gmsh-format file we can feed through the parser without
# invoking the gmsh subprocess.
# ---------------------------------------------------------------------


_UNIT_CUBE_MSH = """$MeshFormat
2.2 0 8
$EndMeshFormat
$Nodes
8
1 0.0 0.0 0.0
2 1.0 0.0 0.0
3 1.0 1.0 0.0
4 0.0 1.0 0.0
5 0.0 0.0 1.0
6 1.0 0.0 1.0
7 1.0 1.0 1.0
8 0.0 1.0 1.0
$EndNodes
$Elements
6
1 4 2 1 1 1 2 3 5
2 4 2 1 1 2 3 6 5
3 4 2 1 1 3 6 5 7
4 4 2 1 1 3 7 5 8
5 4 2 1 1 3 8 5 4
6 4 2 1 1 3 4 5 1
$EndElements
"""


# ---------------------------------------------------------------------
# parse_gmsh_msh22 — happy path + defensive
# ---------------------------------------------------------------------


def test_parse_unit_cube_yields_8_nodes_6_tets(tmp_path: Path) -> None:
    """T:-3 — round-trip a known cube .msh fixture: 8 nodes, 6 C3D4
    tets, parser preserves gmsh node numbering."""
    msh_path = tmp_path / "cube.msh"
    msh_path.write_text(_UNIT_CUBE_MSH, encoding="utf-8")
    parsed = parse_gmsh_msh22(msh_path)
    assert len(parsed.nodes) == 8
    assert parsed.nodes[1] == (0.0, 0.0, 0.0)
    assert parsed.nodes[7] == (1.0, 1.0, 1.0)
    assert len(parsed.elements) == 6
    # Every element is C3D4 with exactly 4 nodes.
    for elem_id, ccx_type, node_ids in parsed.elements:
        assert ccx_type == "C3D4"
        assert len(node_ids) == 4


def test_parse_refuses_missing_file(tmp_path: Path) -> None:
    """A:-2 — missing file raises FileNotFoundError (not a silent zero
    mesh)."""
    with pytest.raises(FileNotFoundError):
        parse_gmsh_msh22(tmp_path / "nope.msh")


def test_parse_refuses_v4_format(tmp_path: Path) -> None:
    """A:-2 — v4 format (the modern gmsh default) is rejected with a
    citation pointing to the right `-format msh22` flag."""
    bad = tmp_path / "v4.msh"
    bad.write_text(
        "$MeshFormat\n4.1 0 8\n$EndMeshFormat\n", encoding="utf-8"
    )
    with pytest.raises(MeshParseError, match="version 2.2|msh22"):
        parse_gmsh_msh22(bad)


def test_parse_refuses_binary(tmp_path: Path) -> None:
    """A:-2 — binary format flag in the header is rejected."""
    bad = tmp_path / "binary.msh"
    bad.write_text(
        "$MeshFormat\n2.2 1 8\n$EndMeshFormat\n", encoding="utf-8"
    )
    with pytest.raises(MeshParseError, match="binary|ASCII"):
        parse_gmsh_msh22(bad)


def test_parse_refuses_zero_volume_elements(tmp_path: Path) -> None:
    """A:-2 — gmsh ran with `-2` (surface only) instead of `-3` →
    parser surfaces a clear error rather than producing an empty INP."""
    surface_only = """$MeshFormat
2.2 0 8
$EndMeshFormat
$Nodes
3
1 0.0 0.0 0.0
2 1.0 0.0 0.0
3 0.0 1.0 0.0
$EndNodes
$Elements
1
1 2 2 1 1 1 2 3
$EndElements
"""
    bad = tmp_path / "surf.msh"
    bad.write_text(surface_only, encoding="utf-8")
    with pytest.raises(MeshParseError, match="C3D4|volume"):
        parse_gmsh_msh22(bad)


def test_parse_ignores_surface_triangle_elements(tmp_path: Path) -> None:
    """Mixed mesh — surface triangles (gmsh type 2) come along when
    gmsh runs in 3D mode. Parser keeps volume elements only."""
    mixed = """$MeshFormat
2.2 0 8
$EndMeshFormat
$Nodes
4
1 0.0 0.0 0.0
2 1.0 0.0 0.0
3 0.0 1.0 0.0
4 0.0 0.0 1.0
$EndNodes
$Elements
3
1 2 2 1 1 1 2 3
2 2 2 1 1 1 2 4
3 4 2 1 1 1 2 3 4
$EndElements
"""
    path = tmp_path / "mixed.msh"
    path.write_text(mixed, encoding="utf-8")
    parsed = parse_gmsh_msh22(path)
    assert len(parsed.elements) == 1  # only the type-4 tet
    assert parsed.elements[0][1] == "C3D4"


# ---------------------------------------------------------------------
# write_meshed_static_inp — happy path + defensive
# ---------------------------------------------------------------------


def _parsed_unit_cube() -> ParsedMesh:
    """Build a ParsedMesh from the fixture text (no file I/O)."""
    nodes = {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (1.0, 1.0, 0.0),
        4: (0.0, 1.0, 0.0),
        5: (0.0, 0.0, 1.0),
        6: (1.0, 0.0, 1.0),
        7: (1.0, 1.0, 1.0),
        8: (0.0, 1.0, 1.0),
    }
    elements = [
        (1, "C3D4", [1, 2, 3, 5]),
        (2, "C3D4", [2, 3, 6, 5]),
    ]
    return ParsedMesh(nodes=nodes, elements=elements)


def test_write_meshed_static_inp_emits_expected_sections(
    tmp_path: Path,
) -> None:
    """T:-3 — composed INP has the C3D4 *ELEMENT block, the *NSET
    clamp list, *CLOAD nodal loads on the selected face, and *STATIC."""
    mesh = _parsed_unit_cube()
    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=0.0)
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=1.0),
        dof=1,
        total_force_n=400.0,
    )
    inp_path = write_meshed_static_inp(
        tmp_path,
        jobname="cube",
        mesh=mesh,
        material=DEFAULT_STEEL,
        bc=bc,
        load=load,
    )
    body = inp_path.read_text(encoding="utf-8")
    # Required blocks
    for required in (
        "*HEADING",
        "*NODE",
        "*ELEMENT, TYPE=C3D4",
        "*MATERIAL, NAME=STEEL_S355",
        "*ELASTIC",
        "*SOLID SECTION",
        "*NSET, NSET=NCLAMP",
        "*BOUNDARY",
        "*STEP",
        "*STATIC",
        "*CLOAD",
        "*END STEP",
    ):
        assert required in body, f"missing {required!r}"


def test_write_meshed_static_inp_clamps_x0_nodes(tmp_path: Path) -> None:
    """The clamp plane x=0 selects nodes 1, 4, 5, 8 (the cube's left
    face). The NCLAMP set should list exactly those, ordered."""
    mesh = _parsed_unit_cube()
    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=0.0)
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=1.0),
        dof=1,
        total_force_n=400.0,
    )
    inp_path = write_meshed_static_inp(
        tmp_path,
        jobname="cube",
        mesh=mesh,
        material=DEFAULT_STEEL,
        bc=bc,
        load=load,
    )
    body = inp_path.read_text(encoding="utf-8")
    lines = body.splitlines()
    nclamp_idx = next(
        i for i, l in enumerate(lines) if l.strip() == "*NSET, NSET=NCLAMP"
    )
    nclamp_row = lines[nclamp_idx + 1]
    assert nclamp_row == "1, 4, 5, 8"


def test_write_meshed_static_inp_loads_xL_nodes(tmp_path: Path) -> None:
    """Load plane x=1.0 selects nodes 2, 3, 6, 7. Each receives
    400/4 = 100 N on DOF 1."""
    mesh = _parsed_unit_cube()
    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=0.0)
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=1.0),
        dof=1,
        total_force_n=400.0,
    )
    inp_path = write_meshed_static_inp(
        tmp_path,
        jobname="cube",
        mesh=mesh,
        material=DEFAULT_STEEL,
        bc=bc,
        load=load,
    )
    body = inp_path.read_text(encoding="utf-8")
    # 4 *CLOAD rows on DOF 1 with 100 N each.
    for nid in (2, 3, 6, 7):
        assert f"{nid}, 1, 100.000000" in body


def test_write_meshed_static_inp_refuses_empty_clamp_set(
    tmp_path: Path,
) -> None:
    """A:-2 — clamp plane that selects zero nodes raises ValueError
    BEFORE writing the INP (anti-foot-gun against ccx solving an
    unrestrained model)."""
    mesh = _parsed_unit_cube()
    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=-10.0)  # off-geometry
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=1.0),
        dof=1,
        total_force_n=400.0,
    )
    with pytest.raises(ValueError, match="BC plane"):
        write_meshed_static_inp(
            tmp_path,
            jobname="cube",
            mesh=mesh,
            material=DEFAULT_STEEL,
            bc=bc,
            load=load,
        )


def test_write_meshed_static_inp_refuses_empty_load_set(
    tmp_path: Path,
) -> None:
    """A:-2 — load plane selecting zero nodes raises before write."""
    mesh = _parsed_unit_cube()
    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=0.0)
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=99.0),  # off-geometry
        dof=1,
        total_force_n=400.0,
    )
    with pytest.raises(ValueError, match="Load plane"):
        write_meshed_static_inp(
            tmp_path,
            jobname="cube",
            mesh=mesh,
            material=DEFAULT_STEEL,
            bc=bc,
            load=load,
        )


def test_write_meshed_static_inp_emits_plastic_when_curve_present(
    tmp_path: Path,
) -> None:
    """Phase 20 B integration — if the MinimalHexMaterial carries a
    plastic_hardening_curve, the meshed INP also emits *PLASTIC."""
    plastic_mat = MinimalHexMaterial(
        name="STEEL_S355_BILINEAR",
        youngs_modulus_pa=210e9,
        poisson_ratio=0.3,
        plastic_hardening_curve=((0.0, 355e6), (0.2, 510e6)),
    )
    mesh = _parsed_unit_cube()
    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=0.0)
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=1.0),
        dof=1,
        total_force_n=400.0,
    )
    inp_path = write_meshed_static_inp(
        tmp_path,
        jobname="plastic",
        mesh=mesh,
        material=plastic_mat,
        bc=bc,
        load=load,
    )
    body = inp_path.read_text(encoding="utf-8")
    assert "*PLASTIC" in body
    assert "3.550000e+08, 0.000000" in body
    assert "5.100000e+08, 0.200000" in body


# ---------------------------------------------------------------------
# Plate-with-hole-candidate is registered
# ---------------------------------------------------------------------


def test_plate_with_hole_candidate_registered() -> None:
    """The case is in the registry. Phase 20 C registered it as
    tier_1_candidate baseline; Phase 21 A's Kirsch cross-check
    runner promotes it to tier_2_validated when the verdict file is
    present on disk. The promoted-state pin lives in
    `test_phase21a_cantilever_kirsch_runners.py
    ::test_phase21a_validated_count_is_three` — here we only assert
    the case is present and at one of the two valid tiers."""
    tier = CLAIM_TIER_REGISTRY["plate-with-hole-candidate"]
    assert tier in {"tier_1_candidate", "tier_2_validated"}


def test_plate_with_hole_geo_file_exists() -> None:
    """The canonical .geo for the Phase 20 C demonstration must be
    on disk; the meshed pipeline E2E pin (below, requires_solver)
    feeds it to gmsh."""
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    geo = (
        repo_root
        / "golden_samples"
        / "plate-with-hole-candidate"
        / "data"
        / "plate_with_hole.geo"
    )
    assert geo.is_file(), f"missing {geo}"
    body = geo.read_text(encoding="utf-8")
    # Geometry constants pinned so a future drive-by edit that
    # silently doubles plate dimensions trips this test.
    assert "L = 0.100" in body
    assert "W = 0.050" in body
    assert "T = 0.005" in body
    assert "R = 0.010" in body


# ---------------------------------------------------------------------
# T:-3 — real gmsh + real ccx end-to-end (requires_solver)
# ---------------------------------------------------------------------


@pytest.mark.requires_solver
def test_real_gmsh_and_ccx_plate_with_hole_yields_displacement(
    tmp_path: Path,
) -> None:
    """The load-bearing Phase 20 C pin. Real gmsh meshes the
    plate-with-hole .geo into C3D4 tets, the adapter writes a static
    INP, real ccx solves it, and the .frd contains a non-zero
    displacement field. Without this test the entire Slice C is just
    happy-path adapter plumbing."""
    from app.adapters.calculix import CalculiXReader
    from app.core.types import CanonicalField, UnitSystem
    from app.services.tier2_pipeline import (
        Tier2MeshedRunResult,
        run_tier2_meshed_pipeline,
    )

    # Copy the canonical .geo into the test workspace (HF1.7b
    # candidate carve-out path-guard requires the geometry to live
    # inside case_dir).
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    src_geo = (
        repo_root
        / "golden_samples"
        / "plate-with-hole-candidate"
        / "data"
        / "plate_with_hole.geo"
    )
    case_dir = tmp_path / "phase20c-meshed-candidate"
    case_dir.mkdir()
    dst_geo = case_dir / "plate_with_hole.geo"
    dst_geo.write_text(src_geo.read_text(encoding="utf-8"), encoding="utf-8")

    # Phase 20 C canonical BC + load (per the candidate NOTES.md).
    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=0.0, tol_m=1e-5)
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=0.100, tol_m=1e-5),
        dof=1,
        total_force_n=+1000.0,  # tensile pull along x
    )

    result = run_tier2_meshed_pipeline(
        case_dir,
        jobname="p20c",
        geometry_path=dst_geo,
        material_id="steel-s355",
        bc=bc,
        load=load,
        characteristic_length_m=0.005,
        gmsh_binary="/opt/homebrew/bin/gmsh",
        ccx_binary="/opt/homebrew/bin/ccx",
        ccx_timeout_sec=120.0,
        gmsh_timeout_sec=120.0,
    )
    assert isinstance(result, Tier2MeshedRunResult)
    assert result.ccx_result.returncode == 0
    assert result.node_count > 50, (
        f"mesh too coarse — expected >50 nodes, got {result.node_count}"
    )
    assert result.element_count > 20, (
        f"mesh too coarse — expected >20 tets, got {result.element_count}"
    )

    # Read displacement field from the .frd; the tensile loading
    # along x should produce non-zero positive u_x at the loaded face.
    reader = CalculiXReader(
        result.ccx_result.frd_path, unit_system=UnitSystem.SI
    )
    disp = reader.get_field(CanonicalField.DISPLACEMENT, step_id=1)
    assert disp is not None, ".frd missing displacement field"
    arr = disp.at_nodes()
    assert arr.shape[0] == result.node_count
    # Max |u_x| across nodes should be non-zero (the plate stretched).
    ux_max_abs = float(abs(arr[:, 0]).max())
    assert ux_max_abs > 0, (
        f"displacement field is identically zero; ccx ran but the "
        f"model is unrestrained or unloaded"
    )
