"""CalculiX Layer-1 adapter — minimal INP input file writer (Phase 18 A).

Generates valid linear-static ``.inp`` solver input files for the
real ``ccx`` subprocess (paired with :class:`CalculiXRunner`).

Phase 18 A scope: a single canonical "smoke" geometry — one C3D8
hex element fixed at the bottom face with a uniform z-direction
nodal load on the top face. This is the minimum complete model that
proves the runner → solver → ``.frd`` chain works end-to-end on a
real ccx invocation without depending on external mesh generation
(Slice C territory).

Phase 18 C will extend this module with mesh + material composition
(Gmsh-meshed geometries + materials library lookups).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MinimalHexMaterial:
    """Linear elastic material for the minimal-hex smoke INP.

    Phase 18 A only supports linear elastic; Phase 20 B adds optional
    bilinear (or piecewise linear) plasticity via the hardening curve.

    Attributes:
        name: material label written into the INP (uppercase, no
            spaces; CalculiX is sensitive to label characters).
        youngs_modulus_pa: Young's modulus in pascals.
        poisson_ratio: dimensionless.
        plastic_hardening_curve: optional list of
            ``(plastic_strain, true_stress_pa)`` pairs ordered by
            ascending plastic strain. When present, the INP writer
            emits a ``*PLASTIC`` block so ccx promotes to a nonlinear
            (NLGEOM-capable) run. Phase 20 B addition.
    """

    name: str
    youngs_modulus_pa: float
    poisson_ratio: float
    plastic_hardening_curve: tuple[tuple[float, float], ...] | None = None


# Phase 18 A defaults — structural steel, S355 grade, SI units.
# The Phase 18 C materials library will surface these (and more) via
# JSON; Phase 18 A inlines the default so the smoke test is self-
# contained and doesn't take a dependency on the C-slice loader.
DEFAULT_STEEL = MinimalHexMaterial(
    name="STEEL_S355",
    youngs_modulus_pa=210e9,
    poisson_ratio=0.3,
)


def write_minimal_hex_inp(
    case_dir: Path,
    *,
    jobname: str,
    material: MinimalHexMaterial = DEFAULT_STEEL,
    edge_length_m: float = 0.1,
    top_face_load_n: float = -1000.0,
) -> Path:
    """Write a minimal single-C3D8-hex linear-static INP file.

    Geometry: a single hex element with corners at
    ``(0, 0, 0)..(L, L, L)`` where ``L = edge_length_m``.

    Boundary conditions: bottom face (z=0; nodes 1-4) fully clamped
    (DOF 1, 2, 3). Top face (z=L; nodes 5-8) carries the
    ``top_face_load_n`` nodal load on DOF 3 (z-direction). A negative
    value compresses the element; a positive value places it in
    tension.

    Args:
        case_dir: workspace directory; must exist.
        jobname: INP filename stem; the written file is
            ``case_dir/<jobname>.inp``.
        material: linear elastic material descriptor.
        edge_length_m: hex edge length in meters (default 100 mm).
        top_face_load_n: total z-direction load applied across the
            top face, split equally among the 4 top nodes (default
            -1000 N, i.e., 250 N compressive per corner node).

    Returns:
        Absolute path to the written INP file.
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(
            f"case_dir {case_dir!s} must exist before writing INP"
        )
    if edge_length_m <= 0:
        raise ValueError(
            f"edge_length_m must be positive; got {edge_length_m}"
        )
    if material.youngs_modulus_pa <= 0:
        raise ValueError(
            f"material.youngs_modulus_pa must be positive; got "
            f"{material.youngs_modulus_pa}"
        )
    if not (0.0 < material.poisson_ratio < 0.5):
        raise ValueError(
            f"material.poisson_ratio must be in (0, 0.5); got "
            f"{material.poisson_ratio}"
        )

    e_pa = material.youngs_modulus_pa
    nu = material.poisson_ratio
    length = float(edge_length_m)
    load_per_node = float(top_face_load_n) / 4.0

    # 8 corners of a unit-ish hex aligned with the global axes.
    # CalculiX C3D8 node ordering: bottom face counter-clockwise
    # viewed from above (1-2-3-4), top face counter-clockwise
    # viewed from above (5-6-7-8), with 5 directly above 1, etc.
    nodes = (
        (1, 0.0, 0.0, 0.0),
        (2, length, 0.0, 0.0),
        (3, length, length, 0.0),
        (4, 0.0, length, 0.0),
        (5, 0.0, 0.0, length),
        (6, length, 0.0, length),
        (7, length, length, length),
        (8, 0.0, length, length),
    )

    lines: list[str] = []
    lines.append(f"*HEADING")
    lines.append(f"Phase 18 A minimal-hex smoke ({jobname})")
    lines.append(f"*NODE")
    for node_id, x, y, z in nodes:
        lines.append(f"{node_id}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append(f"*ELEMENT, TYPE=C3D8, ELSET=EALL")
    lines.append(f"1, 1, 2, 3, 4, 5, 6, 7, 8")
    lines.append(f"*MATERIAL, NAME={material.name}")
    lines.append(f"*ELASTIC")
    lines.append(f"{e_pa:.6e}, {nu:.6f}")
    # Phase 20 B — optional bilinear / piecewise-linear plasticity.
    # When the material carries a hardening curve, emit *PLASTIC so
    # ccx auto-promotes to a nonlinear run. The curve is written
    # exactly as CalculiX's *PLASTIC consumes it: ``stress_pa,
    # plastic_strain`` per row (note the column order is the inverse
    # of the dataclass tuple ordering).
    if material.plastic_hardening_curve is not None:
        lines.append(f"*PLASTIC")
        for plastic_strain, stress_pa in material.plastic_hardening_curve:
            lines.append(f"{stress_pa:.6e}, {plastic_strain:.6f}")
    lines.append(f"*SOLID SECTION, ELSET=EALL, MATERIAL={material.name}")
    # Bottom face fully clamped: nodes 1-4 fixed in all 3 DOFs.
    lines.append(f"*BOUNDARY")
    for node_id in (1, 2, 3, 4):
        lines.append(f"{node_id}, 1, 3, 0.0")
    # Step: linear static; nodal load on top face (z=L) DOF 3.
    lines.append(f"*STEP")
    lines.append(f"*STATIC")
    lines.append(f"*CLOAD")
    for node_id in (5, 6, 7, 8):
        lines.append(f"{node_id}, 3, {load_per_node:.6f}")
    # Result requests: nodal displacement + stress tensor (the .frd
    # output the CalculiXReader Layer-1 adapter expects to parse).
    lines.append(f"*NODE FILE")
    lines.append(f"U")
    lines.append(f"*EL FILE")
    lines.append(f"S")
    lines.append(f"*END STEP")
    lines.append(f"")  # trailing newline

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


def write_modal_hex_inp(
    case_dir: Path,
    *,
    jobname: str,
    material: MinimalHexMaterial = DEFAULT_STEEL,
    edge_length_m: float = 0.1,
    density_kg_m3: float = 7850.0,
    num_modes: int = 5,
) -> Path:
    """Write a single-C3D8-hex modal-eigenvalue INP — Phase 19 C.

    Same geometry as :func:`write_minimal_hex_inp` but the step is a
    ``*FREQUENCY`` modal extraction instead of linear static. The
    bottom face is clamped (so the eigenmodes have proper boundary
    conditions, not free-free); top face is free. ccx writes the
    requested ``num_modes`` natural frequencies to the .frd `MODES`
    block and the corresponding mode shapes to `DISP`.

    Args:
        case_dir: workspace; must exist.
        jobname: INP filename stem.
        material: linear elastic material (E + ν used; density
            supplied separately because Phase 18 A's
            :class:`MinimalHexMaterial` doesn't carry density —
            avoiding a schema bump on that dataclass).
        edge_length_m: hex edge in meters.
        density_kg_m3: mass density in kg/m³; required for modal
            (eigenvalue depends on `K - λM`).
        num_modes: number of eigenfrequencies to compute (default 5).

    Returns:
        Absolute path to the written INP.
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(
            f"case_dir {case_dir!s} must exist before writing INP"
        )
    if edge_length_m <= 0:
        raise ValueError(f"edge_length_m must be positive; got {edge_length_m}")
    if material.youngs_modulus_pa <= 0:
        raise ValueError(
            f"material.youngs_modulus_pa must be positive; got "
            f"{material.youngs_modulus_pa}"
        )
    if not (0.0 < material.poisson_ratio < 0.5):
        raise ValueError(
            f"material.poisson_ratio must be in (0, 0.5); got "
            f"{material.poisson_ratio}"
        )
    if density_kg_m3 <= 0:
        raise ValueError(
            f"density_kg_m3 must be positive; got {density_kg_m3}"
        )
    if num_modes < 1:
        raise ValueError(f"num_modes must be >= 1; got {num_modes}")

    e_pa = material.youngs_modulus_pa
    nu = material.poisson_ratio
    length = float(edge_length_m)

    nodes = (
        (1, 0.0, 0.0, 0.0),
        (2, length, 0.0, 0.0),
        (3, length, length, 0.0),
        (4, 0.0, length, 0.0),
        (5, 0.0, 0.0, length),
        (6, length, 0.0, length),
        (7, length, length, length),
        (8, 0.0, length, length),
    )

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 19 C modal-hex ({jobname}, {num_modes} modes)")
    lines.append("*NODE")
    for nid, x, y, z in nodes:
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=EALL")
    lines.append("1, 1, 2, 3, 4, 5, 6, 7, 8")
    lines.append(f"*MATERIAL, NAME={material.name}")
    lines.append("*ELASTIC")
    lines.append(f"{e_pa:.6e}, {nu:.6f}")
    lines.append("*DENSITY")
    lines.append(f"{density_kg_m3:.6f}")
    lines.append(f"*SOLID SECTION, ELSET=EALL, MATERIAL={material.name}")
    # Bottom face fully clamped (cantilever-style modal extraction).
    lines.append("*BOUNDARY")
    for nid in (1, 2, 3, 4):
        lines.append(f"{nid}, 1, 3, 0.0")
    # Modal step. CalculiX accepts solver name on *FREQUENCY; default
    # is Lanczos. `num_modes` eigenvalues requested.
    lines.append("*STEP")
    lines.append("*FREQUENCY")
    lines.append(f"{num_modes}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


def write_single_c3d6_wedge_uniaxial_inp(
    case_dir: Path,
    *,
    jobname: str,
    material: MinimalHexMaterial = DEFAULT_STEEL,
    base_length_m: float = 0.1,
    height_m: float = 0.1,
    applied_strain: float = 1.0e-3,
) -> Path:
    """Write a single-C3D6 (6-node wedge) uniaxial Hooke's-law INP — Phase 38 B.

    Adds the **6th element class** to the cohort (C3D4 / C3D8 / C3D10 /
    S4 / B31 → + C3D6). The model is the minimal complete C3D6 case:
    one linear pentahedral wedge held in a PURE uniaxial-stress state,
    so the constant-strain element develops ``sigma_zz = E *
    applied_strain`` exactly (Hooke's law) — cross-checkable against
    ccx to machine precision.

    Geometry: a right triangular prism. Bottom triangle (z=0) at nodes
    1-3; top triangle (z=height) at nodes 4-6 (node 4 above 1, 5 above
    2, 6 above 3). Node order gives an outward normal from the bottom
    face toward the top face (positive ccx volume).

    Boundary conditions — statically-determinate uniaxial STRESS, with
    the lateral faces traction-free so the Poisson contraction is
    unconstrained and ``sigma_xx = sigma_yy = 0``:

      * bottom triangle z-clamped (``uz=0`` on nodes 1-3)
      * node 1 also fixed in x and y (origin pin — removes rigid-body
        translation/rotation in-plane)
      * node 2 fixed in y (leaves x free for Poisson)
      * node 3 fixed in x (leaves y free for Poisson)
      * top triangle prescribed ``uz = -applied_strain * height``
        (compression) inside the step

    Analytical: ``sigma_zz = -E * applied_strain`` (compressive); the
    magnitude is ``E * applied_strain``. A *positive* ``applied_strain``
    therefore produces a compressive (negative) axial stress.

    Args:
        case_dir: workspace directory; must exist.
        jobname: INP filename stem; written to ``case_dir/<jobname>.inp``.
        material: linear elastic material descriptor (E + ν used).
        base_length_m: leg length of the right-triangle base (meters).
        height_m: prism height along z (meters); the gauge length for
            the imposed axial strain.
        applied_strain: dimensionless axial strain imposed via the
            prescribed top-face displacement. Kept small (default 1e-3)
            so the linear-elastic σ = E·ε relation holds and the result
            stays well inside any yield envelope.

    Returns:
        Absolute path to the written INP file.
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(
            f"case_dir {case_dir!s} must exist before writing INP"
        )
    if base_length_m <= 0:
        raise ValueError(f"base_length_m must be positive; got {base_length_m}")
    if height_m <= 0:
        raise ValueError(f"height_m must be positive; got {height_m}")
    if material.youngs_modulus_pa <= 0:
        raise ValueError(
            f"material.youngs_modulus_pa must be positive; got "
            f"{material.youngs_modulus_pa}"
        )
    if not (0.0 < material.poisson_ratio < 0.5):
        raise ValueError(
            f"material.poisson_ratio must be in (0, 0.5); got "
            f"{material.poisson_ratio}"
        )
    if not (0.0 < abs(applied_strain) < 0.05):
        raise ValueError(
            f"applied_strain must be nonzero and |strain| < 0.05 to stay "
            f"in the linear-elastic regime; got {applied_strain}"
        )

    e_pa = material.youngs_modulus_pa
    nu = material.poisson_ratio
    base = float(base_length_m)
    height = float(height_m)
    delta = float(applied_strain) * height  # prescribed axial shortening

    # 6-node linear wedge (triangular prism). Bottom triangle 1-2-3 at
    # z=0; top triangle 4-5-6 at z=height (4 above 1, 5 above 2, 6 above
    # 3). 1→2→3 is counter-clockwise viewed from +z, so the right-hand
    # normal points toward the top face (positive ccx volume).
    nodes = (
        (1, 0.0, 0.0, 0.0),
        (2, base, 0.0, 0.0),
        (3, 0.0, base, 0.0),
        (4, 0.0, 0.0, height),
        (5, base, 0.0, height),
        (6, 0.0, base, height),
    )

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 38 B single-C3D6 wedge uniaxial Hooke's law ({jobname})")
    lines.append("*NODE")
    for nid, x, y, z in nodes:
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append("*ELEMENT, TYPE=C3D6, ELSET=EALL")
    lines.append("1, 1, 2, 3, 4, 5, 6")
    lines.append(f"*MATERIAL, NAME={material.name}")
    lines.append("*ELASTIC")
    lines.append(f"{e_pa:.6e}, {nu:.6f}")
    lines.append(f"*SOLID SECTION, ELSET=EALL, MATERIAL={material.name}")
    # Homogeneous BCs (before the step): bottom z-clamp + statically-
    # determinate in-plane pins that leave Poisson contraction free.
    lines.append("*BOUNDARY")
    lines.append("1, 3, 3, 0.0")  # node 1 uz=0
    lines.append("2, 3, 3, 0.0")  # node 2 uz=0
    lines.append("3, 3, 3, 0.0")  # node 3 uz=0
    lines.append("1, 1, 2, 0.0")  # node 1 ux=uy=0 (origin pin)
    lines.append("2, 2, 2, 0.0")  # node 2 uy=0 (x free for Poisson)
    lines.append("3, 1, 1, 0.0")  # node 3 ux=0 (y free for Poisson)
    lines.append("*STEP")
    lines.append("*STATIC")
    # Prescribed nonzero axial displacement on the top triangle (inside
    # the step). Negative = compression → compressive sigma_zz.
    lines.append("*BOUNDARY")
    for nid in (4, 5, 6):
        lines.append(f"{nid}, 3, 3, {-delta:.9e}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*EL FILE")
    lines.append("S")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path
