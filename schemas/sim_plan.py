"""SimPlan — the master simulation specification produced by the Architect Agent.

This Pydantic model captures *everything* downstream agents need:
geometry definition, material properties, loads, boundary conditions,
mesh strategy, solver controls, and post-processing requests.

This module is a stub (AI-FEA-P0-01).  Fields will be expanded in P0-04.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AnalysisType(StrEnum):
    """Supported analysis types (PRD v0.2 §物理域)."""

    STATIC = "static"
    MODAL = "modal"
    PRESTRESS_MODAL = "prestress_modal"
    CYCLIC_SYMMETRY = "cyclic_symmetry"
    STEADY_THERMAL = "steady_thermal"  # stretch goal
    THERMO_STRUCTURAL = "thermo_structural"  # stretch goal


class SolverBackend(StrEnum):
    """Available solver backends."""

    CALCULIX = "calculix"
    FENICS = "fenics"


class ElementOrder(StrEnum):
    """Finite-element polynomial order."""

    LINEAR = "linear"
    QUADRATIC = "quadratic"


class MeshLevel(StrEnum):
    """Named mesh density presets for the Mesh Agent."""

    COARSE = "coarse"
    MEDIUM = "medium"
    FINE = "fine"
    VERY_FINE = "very_fine"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class GeometrySpec(BaseModel):
    """Geometry definition — consumed by the Geometry Agent."""

    kind: str = Field(
        ..., description="Geometry type: 'naca', 'pressure_vessel', 'plate', 'truss', 'custom'"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific geometry parameters. For 'naca', use 'profile' (e.g. 'NACA0012'), 'chord_length' (float), 'span' (float).",
    )


class MaterialSpec(BaseModel):
    """Isotropic linear-elastic material."""

    name: str = "Steel"
    youngs_modulus_pa: float = Field(210e9, description="Young's modulus [Pa]")
    poissons_ratio: float = Field(0.3, ge=0.0, le=0.5)
    density_kg_m3: float = Field(7850.0, description="Density [kg/m³]")
    thermal_conductivity: float | None = Field(None, description="[W/m·K] — for thermal analyses")
    specific_heat: float | None = Field(None, description="[J/kg·K] — for thermal analyses")


class LoadSpec(BaseModel):
    """A single load definition."""

    kind: str = Field(..., description="concentrated_force | pressure | gravity | thermal")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Load parameters. For 'concentrated_force', use 'magnitude' (float, N) and 'node_set' (string, e.g. 'Ntip').",
    )


class BCSpec(BaseModel):
    """A single boundary-condition definition."""

    kind: str = Field(..., description="fixed | displacement | symmetry | cyclic")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Boundary Condition parameters. For 'fixed', use 'node_set' (string, e.g. 'Nroot').",
    )


class MeshStrategy(BaseModel):
    """Meshing parameters for the Mesh Agent."""

    element_order: ElementOrder = ElementOrder.QUADRATIC
    mesh_level: MeshLevel = MeshLevel.MEDIUM
    global_size: float | None = Field(None, description="Global element size [m]")
    refinement_regions: list[dict[str, Any]] = Field(default_factory=list)
    min_scaled_jacobian: float = Field(0.2, gt=0.0, description="Scaled Jacobian threshold")
    max_aspect_ratio: float = Field(10.0, gt=1.0, description="Aspect ratio threshold")
    thin_wall_threshold_m: float = Field(
        5e-4,
        gt=0.0,
        description="Minimum feature size below which thin-wall refinement is forced",
    )


class SolverControls(BaseModel):
    """Solver-specific knobs."""

    backend: SolverBackend = SolverBackend.CALCULIX
    num_modes: int | None = Field(None, description="Number of modes (modal analysis)")
    nonlinear: bool = False
    max_increments: int = 100


class PostSpec(BaseModel):
    """Post-processing requests."""

    fields: list[str] = Field(default_factory=lambda: ["displacement", "von_mises_stress"])
    export_vtp: bool = True
    generate_report: bool = True


# ---------------------------------------------------------------------------
# Top-level SimPlan
# ---------------------------------------------------------------------------


class SimPlan(BaseModel):
    """Master simulation plan — the single contract between agents.

    Produced by the Architect Agent, consumed (read-only) by all others.
    """

    case_id: str = Field(
        ..., pattern=r"^AI-FEA-P\d+-\d+$", description="Case ID per naming convention"
    )
    analysis_type: AnalysisType = AnalysisType.STATIC
    description: str = ""

    geometry: GeometrySpec
    material: MaterialSpec = Field(default_factory=MaterialSpec)
    loads: list[LoadSpec] = Field(default_factory=list)
    boundary_conditions: list[BCSpec] = Field(default_factory=list)

    mesh: MeshStrategy = Field(default_factory=MeshStrategy)
    solver: SolverControls = Field(default_factory=SolverControls)
    post: PostSpec = Field(default_factory=PostSpec)

    reference_values: dict[str, float] = Field(
        default_factory=dict,
        description="Analytical / known reference values for reviewer comparison",
    )
