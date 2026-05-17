"""Tier 2 solver pipeline — FM-04a Phase 19 A.

Composes the Phase 18 building blocks into a single end-to-end
function that takes a case workspace + a material id + linear-static
parameters and returns a :class:`Tier2RunResult` carrying the ccx
``.frd`` path + the resolved material reference (for audit trail).

Layer split (RFC-001 §4.5):
* This service consumes Layer-1 adapters (``CalculiXRunner`` +
  ``write_minimal_hex_inp``) and the Layer-3 materials SSOT
  (``app.services.materials.get_material``).
* It is **purpose-built for Tier 2 candidate runs** — the existing
  async-streaming ``app.services.solver.SolverService`` keeps the
  Phase 1-17 reviewer flow intact; Tier 2 candidate runs go through
  here so the regression surface stays narrow.

Phase 19 A scope: minimal-hex Tier 2 run with picker-chosen material.
Phase 19 B extends this with the analytical cross-check + tier
promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.adapters.calculix import (
    BoundaryConditionSpec,
    CalculiXRunError,
    CalculiXRunner,
    CalculiXRunResult,
    DEFAULT_STEEL,
    LoadSpec,
    MeshParseError,
    MinimalHexMaterial,
    parse_gmsh_msh22,
    write_meshed_static_inp,
    write_minimal_hex_inp,
)
from app.services.materials import (
    Material,
    MaterialNotFoundError,
    get_material,
)
from app.services.meshing.gmsh_runner import GmshRunError, GmshRunner


class Tier2PipelineError(RuntimeError):
    """Raised when the Tier 2 pipeline cannot complete a run.

    Wraps subordinate errors (unknown material id, ccx failure) with
    a uniform surface so the calling route / UI can render one
    consistent error path.
    """

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.cause = cause


@dataclass(frozen=True)
class Tier2RunResult:
    """Outcome of a Phase 19 Tier 2 pipeline run.

    Attributes:
        material_resolved: the :class:`Material` actually used in the
            run (may be the DEFAULT_STEEL when ``material_id`` was
            omitted; the reviewer sees the resolved id in the audit
            trail).
        material_reference: the citation string carried with the
            material (e.g., "EN 10025-2:2019 §7.3").
        ccx_result: the underlying :class:`CalculiXRunResult` (frd
            path, runtime, etc.).
        inp_path: absolute path to the composed INP file.
    """

    material_resolved: Material
    material_reference: str
    ccx_result: CalculiXRunResult
    inp_path: Path


def resolve_material(material_id: str | None) -> Material | MinimalHexMaterial:
    """Resolve a UI-supplied ``material_id`` to a SSOT material.

    Args:
        material_id: stable id from the materials library, or ``None``
            (the reviewer omitted the pick → fall back to
            :data:`DEFAULT_STEEL` for back-compat with Phase 18 A).

    Returns:
        Either a :class:`app.services.materials.api.Material` (when
        the lookup succeeds) or the :data:`DEFAULT_STEEL`
        :class:`MinimalHexMaterial` (when ``material_id`` is None).

    Raises:
        Tier2PipelineError: when ``material_id`` is non-None but
            unknown to the library. The error carries the original
            :class:`MaterialNotFoundError` so the audit surface can
            cite the failed lookup explicitly.
    """
    if material_id is None or material_id == "":
        return DEFAULT_STEEL
    try:
        return get_material(material_id)
    except MaterialNotFoundError as exc:
        raise Tier2PipelineError(
            f"material_id {material_id!r} not in library; reviewer "
            f"must pick from app/services/materials/library.json",
            stage="resolve_material",
            cause=exc,
        ) from exc


def material_to_hex_descriptor(
    material: Material | MinimalHexMaterial,
) -> MinimalHexMaterial:
    """Convert a Material (or pass-through a MinimalHexMaterial) into
    the shape the Phase 18 A INP writer expects.

    The conversion is lossy w.r.t. density + yield + ultimate
    (the linear-static INP doesn't carry them); they are preserved
    on the audit trail via :attr:`Tier2RunResult.material_reference`.
    """
    if isinstance(material, MinimalHexMaterial):
        return material
    # Material id may include hyphens; CalculiX requires the label
    # to be alphanumeric + underscore. Upper-case canonicalises.
    label = material.id.replace("-", "_").upper()
    return MinimalHexMaterial(
        name=label,
        youngs_modulus_pa=material.youngs_modulus_pa,
        poisson_ratio=material.poisson_ratio,
        # Phase 20 B — forward the optional plasticity curve so the
        # INP writer can emit *PLASTIC when the SSOT material carries
        # a hardening definition.
        plastic_hardening_curve=material.plastic_hardening_curve,
    )


def material_reference_for_audit(
    material: Material | MinimalHexMaterial,
) -> str:
    """Return the citation reference string for the audit trail.

    The Phase 18 A :data:`DEFAULT_STEEL` is a :class:`MinimalHexMaterial`
    with no reference field — the function returns an inline
    description so the audit always carries non-empty provenance.
    """
    if isinstance(material, MinimalHexMaterial):
        return (
            f"Phase 18 A inline default ({material.name}; "
            f"E={material.youngs_modulus_pa:.3e} Pa; "
            f"ν={material.poisson_ratio})"
        )
    return material.reference


def compose_material_id_inp(
    case_dir: Path,
    *,
    jobname: str,
    material_id: str | None,
    edge_length_m: float = 0.1,
    top_face_load_n: float = -1000.0,
) -> tuple[Path, Material | MinimalHexMaterial, str]:
    """Phase 20 A — compose-only path (no ccx subprocess).

    Used by :mod:`app.api.routes.solver` to materialise a Tier 2 INP
    from a UI-supplied ``material_id`` before handing the file to the
    async-streaming legacy :class:`SolverService`. Decoupling the
    composition step from ccx invocation lets the FastAPI route stay
    non-blocking — the (potentially) 30 s ccx subprocess remains in
    the background task; only the deterministic file-write happens on
    the request path.

    Args:
        case_dir: workspace directory (must already exist).
        jobname: INP filename stem; the written file is
            ``case_dir/<jobname>.inp``.
        material_id: SSOT material library id, or ``None`` for the
            Phase 18 A :data:`DEFAULT_STEEL` back-compat fallback.
        edge_length_m: hex edge length in meters (default 100 mm).
        top_face_load_n: total z-direction load (default -1000 N).

    Returns:
        ``(inp_path, material, reference_str)`` triple. The caller
        uses ``inp_path`` to hand off to the solver service; the
        material + reference power the response envelope's audit
        citation.

    Raises:
        Tier2PipelineError: when ``material_id`` is unknown or the
            INP write refuses (the ``stage`` attribute names the
            failure point).
    """
    material = resolve_material(material_id)
    hex_descriptor = material_to_hex_descriptor(material)
    try:
        inp_path = write_minimal_hex_inp(
            case_dir,
            jobname=jobname,
            material=hex_descriptor,
            edge_length_m=edge_length_m,
            top_face_load_n=top_face_load_n,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise Tier2PipelineError(
            f"INP composition refused: {exc}",
            stage="write_inp",
            cause=exc,
        ) from exc
    return inp_path, material, material_reference_for_audit(material)


def run_tier2_minimal_hex(
    case_dir: Path,
    *,
    jobname: str,
    material_id: str | None,
    edge_length_m: float = 0.1,
    top_face_load_n: float = -1000.0,
    ccx_binary: str = "ccx",
    timeout_sec: float = 30.0,
) -> Tier2RunResult:
    """End-to-end Tier 2 minimal-hex pipeline.

    Steps:
      1. Resolve ``material_id`` to a SSOT :class:`Material` (or fall
         back to :data:`DEFAULT_STEEL` when None).
      2. Compose the linear-static INP with the chosen material via
         :func:`write_minimal_hex_inp`.
      3. Invoke the real ``ccx`` subprocess via :class:`CalculiXRunner`.
      4. Return :class:`Tier2RunResult` carrying the resolved material
         + ccx result + INP path.

    Args:
        case_dir: workspace directory (must exist); not a signed
            registry shape (HF1.7a defense applies via
            :class:`CalculiXRunner`).
        jobname: stem for the INP / log / .frd files.
        material_id: SSOT material library id, or ``None`` for default.
        edge_length_m: hex edge length in meters (passed through).
        top_face_load_n: total load on top face (passed through).
        ccx_binary: ccx executable path; default `"ccx"` from PATH.
        timeout_sec: wall-clock cap on the ccx invocation.

    Raises:
        Tier2PipelineError: on any stage failure (unknown material,
            INP write refused, ccx error). The ``stage`` attribute
            indicates where it failed.
    """
    material = resolve_material(material_id)
    hex_descriptor = material_to_hex_descriptor(material)
    try:
        inp_path = write_minimal_hex_inp(
            case_dir,
            jobname=jobname,
            material=hex_descriptor,
            edge_length_m=edge_length_m,
            top_face_load_n=top_face_load_n,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise Tier2PipelineError(
            f"INP composition refused: {exc}",
            stage="write_inp",
            cause=exc,
        ) from exc

    runner = CalculiXRunner(ccx_binary=ccx_binary, timeout_sec=timeout_sec)
    try:
        ccx_result = runner.run(case_dir, jobname)
    except CalculiXRunError as exc:
        raise Tier2PipelineError(
            f"ccx subprocess failed: {exc}",
            stage="run_ccx",
            cause=exc,
        ) from exc

    return Tier2RunResult(
        material_resolved=material,
        material_reference=material_reference_for_audit(material),
        ccx_result=ccx_result,
        inp_path=inp_path,
    )


@dataclass(frozen=True)
class Tier2MeshedRunResult:
    """Outcome of a Phase 20 C Tier 2 meshed pipeline run.

    Attributes:
        material_resolved: the :class:`Material` actually used.
        material_reference: the citation string for audit.
        ccx_result: the :class:`CalculiXRunResult` (frd path, runtime).
        inp_path: absolute path to the composed INP file.
        mesh_path: absolute path to the gmsh-produced .msh file.
        node_count: number of nodes in the parsed mesh.
        element_count: number of volume elements (C3D4 in Phase 20 C).
    """

    material_resolved: Material
    material_reference: str
    ccx_result: CalculiXRunResult
    inp_path: Path
    mesh_path: Path
    node_count: int
    element_count: int


def run_tier2_meshed_pipeline(
    case_dir: Path,
    *,
    jobname: str,
    geometry_path: Path,
    material_id: str | None,
    bc: BoundaryConditionSpec,
    load: LoadSpec,
    characteristic_length_m: float = 0.05,
    ccx_binary: str = "ccx",
    gmsh_binary: str = "gmsh",
    ccx_timeout_sec: float = 120.0,
    gmsh_timeout_sec: float = 300.0,
) -> Tier2MeshedRunResult:
    """End-to-end Tier 2 pipeline on a meshed CAD geometry.

    Steps:
      1. Resolve ``material_id`` via the SSOT library.
      2. Invoke real ``gmsh`` to mesh ``geometry_path`` into
         ``<case_dir>/<jobname>.msh`` (ASCII v2.2, linear tets).
      3. Parse the .msh file → ``ParsedMesh`` (nodes + C3D4 elements).
      4. Compose a linear-static INP with the picked material + BC
         + load specifications (BC selects nodes by coordinate plane).
      5. Invoke real ``ccx`` on the composed INP.
      6. Return :class:`Tier2MeshedRunResult` with audit trail.

    Args:
        case_dir: workspace directory (must exist; HF1.7a refused
            on signed-registry shapes via GmshRunner + CalculiXRunner).
        jobname: stem for all output artifacts.
        geometry_path: input CAD file (must resolve inside case_dir;
            extensions .step / .stp / .stl / .brep / .geo supported).
        material_id: SSOT library id, or None for DEFAULT_STEEL.
        bc: boundary condition (clamp-by-plane); see
            :class:`BoundaryConditionSpec`.
        load: load specification (force-on-plane); see :class:`LoadSpec`.
        characteristic_length_m: gmsh target edge length.
        ccx_binary / gmsh_binary: executable paths.
        ccx_timeout_sec / gmsh_timeout_sec: wall-clock caps.

    Raises:
        Tier2PipelineError: on any stage failure; the ``stage``
            attribute names where it failed (resolve_material /
            run_gmsh / parse_mesh / write_inp / run_ccx).
    """
    material = resolve_material(material_id)
    hex_descriptor = material_to_hex_descriptor(material)

    # Step 2 — gmsh mesh production.
    gmsh_runner = GmshRunner(
        gmsh_binary=gmsh_binary, timeout_sec=gmsh_timeout_sec
    )
    try:
        gmsh_result = gmsh_runner.run(
            case_dir,
            geometry_path,
            output_name=jobname,
            characteristic_length_m=characteristic_length_m,
            element_order=1,
            output_format="msh22",
        )
    except GmshRunError as exc:
        raise Tier2PipelineError(
            f"gmsh subprocess failed: {exc}",
            stage="run_gmsh",
            cause=exc,
        ) from exc

    # Step 3 — parse the .msh file.
    try:
        parsed_mesh = parse_gmsh_msh22(gmsh_result.mesh_path)
    except (FileNotFoundError, MeshParseError) as exc:
        raise Tier2PipelineError(
            f"mesh parse refused: {exc}",
            stage="parse_mesh",
            cause=exc,
        ) from exc

    # Step 4 — compose the INP from the parsed mesh + material + BC.
    try:
        inp_path = write_meshed_static_inp(
            case_dir,
            jobname=jobname,
            mesh=parsed_mesh,
            material=hex_descriptor,
            bc=bc,
            load=load,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise Tier2PipelineError(
            f"INP composition refused: {exc}",
            stage="write_inp",
            cause=exc,
        ) from exc

    # Step 5 — invoke ccx.
    ccx_runner = CalculiXRunner(
        ccx_binary=ccx_binary, timeout_sec=ccx_timeout_sec
    )
    try:
        ccx_result = ccx_runner.run(case_dir, jobname)
    except CalculiXRunError as exc:
        raise Tier2PipelineError(
            f"ccx subprocess failed: {exc}",
            stage="run_ccx",
            cause=exc,
        ) from exc

    return Tier2MeshedRunResult(
        material_resolved=material,
        material_reference=material_reference_for_audit(material),
        ccx_result=ccx_result,
        inp_path=inp_path,
        mesh_path=gmsh_result.mesh_path,
        node_count=len(parsed_mesh.nodes),
        element_count=len(parsed_mesh.elements),
    )


__all__ = [
    "Tier2PipelineError",
    "Tier2RunResult",
    "Tier2MeshedRunResult",
    "resolve_material",
    "material_to_hex_descriptor",
    "material_reference_for_audit",
    "compose_material_id_inp",
    "run_tier2_minimal_hex",
    "run_tier2_meshed_pipeline",
]
