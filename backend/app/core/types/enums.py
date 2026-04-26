"""Closed-set enums for the cross-solver ResultReader contract.

RFC-001 §4.3 + ADR-002. Adding a member requires an RFC.
"""

from __future__ import annotations

from enum import Enum


class FieldLocation(str, Enum):
    """Where a field's values live on the mesh."""

    NODE = "node"
    INTEGRATION_POINT = "ip"
    ELEMENT_CENTROID = "centroid"
    ELEMENT = "element"


class ComponentType(str, Enum):
    """Per-point algebraic shape of a field's value."""

    SCALAR = "scalar"
    VECTOR_3D = "vec3"
    TENSOR_SYM_3D = "tensor_sym3"  # 6 components: σxx σyy σzz σxy σyz σxz


class UnitSystem(str, Enum):
    """Unit system for the *raw* field values out of an adapter.

    ADR-003 forbids heuristic guessing — ``UNKNOWN`` must be resolved by
    explicit user choice in the wizard before Layer-3 reads the field.
    """

    SI = "SI"             # m, Pa, kg, N, s
    SI_MM = "SI_mm"       # mm, MPa, t, N, s — design-institute default
    ENGLISH = "English"   # in, psi, slug, lbf, s
    UNKNOWN = "unknown"


class CanonicalField(str, Enum):
    """Cross-solver vocabulary of physical fields (closed set, ADR-002).

    MVP wedge holds 6 members. New entries require an RFC; never expand
    this enum from a feature branch.
    """

    DISPLACEMENT = "displacement"
    STRESS_TENSOR = "stress_tensor"
    STRAIN_TENSOR = "strain_tensor"
    REACTION_FORCE = "reaction_force"
    NODAL_COORDINATES = "node_coords"
    ELEMENT_VOLUME = "elem_volume"
