"""Canonical SimPlan contract with backward-compatible accessors.

PRD v0.2 names the top-level contract as:
``case_id / physics / geometry / material / bcs / loads / sweep /
objectives / solver / reference``.

The rest of the stack was initially built against a pre-PRD draft with names
like ``analysis_type`` and ``boundary_conditions``.  To let P0-04 land
cleanly without breaking P0-05..P0-08, this module accepts both shapes and
exposes lightweight compatibility properties for the older call sites.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AnalysisType(StrEnum):
    """Supported analysis types (PRD v0.2)."""

    STATIC = "static"
    MODAL = "modal"
    PRESTRESS_MODAL = "prestress_modal"
    CYCLIC_SYMMETRY = "cyclic_symmetry"
    STEADY_THERMAL = "steady_thermal"
    THERMO_STRUCTURAL = "thermo_structural"


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


def _coerce_model_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, BaseModel):
        return raw.model_dump()
    return dict(raw)


def _compat_geometry_kind(ref: str | None, params: dict[str, Any]) -> str:
    ref_value = (ref or "").strip().lower()
    profile = str(params.get("profile", "")).strip().lower()
    if "naca" in ref_value or profile.startswith("naca"):
        return "naca"
    if ref_value:
        return ref_value
    return "custom"


class PhysicsSpec(BaseModel):
    """High-level physics requested by the PRD contract."""

    type: AnalysisType = AnalysisType.STATIC
    nonlinear: bool = False


class GeometrySpec(BaseModel):
    """Canonical geometry definition used by the Geometry Agent."""

    mode: str = Field(
        default="knowledge",
        description="How geometry is resolved, e.g. knowledge / parametric / import.",
    )
    ref: str = Field(
        default="naca",
        description="Canonical geometry family or external reference identifier.",
    )
    params: dict[str, Any] = Field(default_factory=dict, description="Geometry parameters.")

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
        data = _coerce_model_dict(raw)
        if not data:
            return data
        if "kind" in data and "ref" not in data:
            data["ref"] = data.pop("kind")
        if "parameters" in data and "params" not in data:
            data["params"] = data.pop("parameters")
        data.setdefault("mode", "knowledge")
        return data

    @property
    def kind(self) -> str:
        """Compatibility alias for pre-PRD call sites."""
        return _compat_geometry_kind(self.ref, self.params)

    @property
    def parameters(self) -> dict[str, Any]:
        """Compatibility alias for pre-PRD call sites."""
        return self.params


class MaterialSpec(BaseModel):
    """Isotropic linear-elastic material."""

    name: str = "Aluminum 7075"
    youngs_modulus_pa: float = Field(71.7e9, description="Young's modulus [Pa]")
    poissons_ratio: float = Field(0.33, ge=0.0, le=0.5)
    density_kg_m3: float = Field(2810.0, description="Density [kg/m^3]")
    thermal_conductivity: float | None = Field(None, description="[W/m*K]")
    specific_heat: float | None = Field(None, description="[J/kg*K]")


class LoadSpec(BaseModel):
    """A single load definition in canonical PRD form."""

    semantic: str = Field(default="tip_load", description="User-facing load label.")
    kind: str = Field(default="concentrated_force")
    target: str | None = Field(default="Ntip")
    magnitude: float | None = Field(default=None, description="Scalar magnitude of the load.")
    direction: str | None = Field(default=None, description="Direction label such as -Z.")
    unit: str = Field(default="N")
    components: dict[str, float] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Legacy compatibility map.",
    )

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
        data = _coerce_model_dict(raw)
        if not data:
            return data

        params = dict(data.get("parameters") or {})
        if params:
            data.setdefault("target", params.get("node_set") or params.get("target"))
            data.setdefault("magnitude", params.get("magnitude"))
            data.setdefault("direction", params.get("direction"))
            components = dict(data.get("components") or {})
            for axis in ("fx", "fy", "fz"):
                if axis in params and axis not in components:
                    components[axis] = float(params[axis])
            if components:
                data["components"] = components
        return data

    @model_validator(mode="after")
    def _hydrate_legacy_parameters(self) -> LoadSpec:
        params = dict(self.parameters)
        if self.target is not None:
            params.setdefault("node_set", self.target)
            params.setdefault("target", self.target)
        if self.magnitude is not None:
            params.setdefault("magnitude", self.magnitude)
        if self.direction:
            params.setdefault("direction", self.direction)
        for axis, value in self.components.items():
            params.setdefault(axis, value)
        self.parameters = params
        return self


class BCSpec(BaseModel):
    """A single boundary-condition definition in canonical PRD form."""

    semantic: str = Field(default="fixed_base")
    kind: str = Field(default="fixed")
    target: str | None = Field(default="Nroot")
    constraints: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Legacy compatibility map.",
    )

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
        data = _coerce_model_dict(raw)
        if not data:
            return data

        params = dict(data.get("parameters") or {})
        if params:
            data.setdefault("target", params.get("node_set") or params.get("target"))
            if "constraints" not in data and "dofs" in params:
                data["constraints"] = {"dofs": params["dofs"]}
        return data

    @model_validator(mode="after")
    def _hydrate_legacy_parameters(self) -> BCSpec:
        params = dict(self.parameters)
        if self.target is not None:
            params.setdefault("node_set", self.target)
            params.setdefault("target", self.target)
        if self.constraints:
            params.setdefault("constraints", self.constraints)
        self.parameters = params
        return self


class SweepSpec(BaseModel):
    """Optional parameter sweep instructions."""

    enabled: bool = False
    parameters: list[dict[str, Any]] = Field(default_factory=list)


class ObjectiveSpec(BaseModel):
    """Requested result outputs and success metrics."""

    metrics: list[str] = Field(
        default_factory=lambda: ["max_displacement", "max_von_mises"],
        description="Quantities the report should surface.",
    )
    export_vtp: bool = True
    narrative_report: bool = True

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_post_spec(cls, raw: Any) -> Any:
        data = _coerce_model_dict(raw)
        if not data:
            return data
        if "fields" in data and "metrics" not in data:
            data["metrics"] = data.pop("fields")
        if "generate_report" in data and "narrative_report" not in data:
            data["narrative_report"] = data.pop("generate_report")
        return data


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
    """Solver-specific knobs in canonical PRD form."""

    name: SolverBackend = SolverBackend.CALCULIX
    version: str = "2.21"
    nonlinear: bool = False
    num_modes: int | None = Field(default=None, description="Number of modes for modal analyses.")
    max_increments: int = 100

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
        data = _coerce_model_dict(raw)
        if not data:
            return data
        if "backend" in data and "name" not in data:
            data["name"] = data.pop("backend")
        return data

    @property
    def backend(self) -> SolverBackend:
        """Compatibility alias for pre-PRD call sites."""
        return self.name


class ReferenceSpec(BaseModel):
    """Reference values used by the reviewer gate."""

    type: str = Field(default="analytical")
    value: dict[str, float] = Field(default_factory=dict)
    tol_pct: float = Field(default=5.0, ge=0.0, description="Approval tolerance in percent.")


class SimPlan(BaseModel):
    """Master simulation plan produced by the Architect Agent."""

    case_id: str = Field(
        ..., pattern=r"^AI-FEA-P\d+-\d+$", description="Case ID per naming convention."
    )
    physics: PhysicsSpec = Field(default_factory=PhysicsSpec)
    geometry: GeometrySpec
    material: MaterialSpec = Field(default_factory=MaterialSpec)
    bcs: list[BCSpec] = Field(default_factory=list)
    loads: list[LoadSpec] = Field(default_factory=list)
    sweep: SweepSpec = Field(default_factory=SweepSpec)
    objectives: ObjectiveSpec = Field(default_factory=ObjectiveSpec)
    solver: SolverControls = Field(default_factory=SolverControls)
    reference: ReferenceSpec = Field(default_factory=ReferenceSpec)
    mesh: MeshStrategy = Field(default_factory=MeshStrategy)
    description: str = ""

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
        data = _coerce_model_dict(raw)
        if not data:
            return data

        if "analysis_type" in data and "physics" not in data:
            data["physics"] = {"type": data.pop("analysis_type")}
        if "boundary_conditions" in data and "bcs" not in data:
            data["bcs"] = data.pop("boundary_conditions")
        if "reference_values" in data and "reference" not in data:
            data["reference"] = {"value": data.pop("reference_values")}
        if "post" in data and "objectives" not in data:
            data["objectives"] = data.pop("post")
        return data

    @property
    def analysis_type(self) -> AnalysisType:
        """Compatibility alias for pre-PRD call sites."""
        return self.physics.type

    @property
    def boundary_conditions(self) -> list[BCSpec]:
        """Compatibility alias for pre-PRD call sites."""
        return self.bcs

    @property
    def reference_values(self) -> dict[str, float]:
        """Compatibility alias for pre-PRD call sites."""
        return self.reference.value
