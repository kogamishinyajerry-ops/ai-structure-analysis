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


class CanonicalElementType(str, Enum):
    """Cross-solver element-type vocabulary (RFC-001 §4.6 trap #3).

    HEX8 / SOLID185 / C3D8 / CHEXA all denote the same 8-node hex; the
    adapter is responsible for mapping its native label onto one of
    these canonical names. Keeping this closed-set means the renderer
    and the cross-solver consistency tests share a single dictionary.
    """

    BAR2 = "bar2"               # 2-node truss / line element
    BEAM2 = "beam2"             # 2-node beam (with rotational DOFs)
    TRI3 = "tri3"               # 3-node triangular shell / plane
    TRI6 = "tri6"               # 6-node triangular
    QUAD4 = "quad4"             # 4-node quadrilateral shell / plane
    QUAD8 = "quad8"             # 8-node serendipity quadrilateral
    TET4 = "tet4"               # 4-node tetrahedron
    TET10 = "tet10"             # 10-node tetrahedron
    HEX8 = "hex8"               # 8-node hexahedron (HEX8 / SOLID185 / C3D8 / CHEXA)
    HEX20 = "hex20"             # 20-node hexahedron
    WEDGE6 = "wedge6"           # 6-node prism / pentahedron
    WEDGE15 = "wedge15"         # 15-node prism
    UNKNOWN = "unknown"         # adapter could not classify


class CoordinateSystemKind(str, Enum):
    """How a field's tensor / vector values are oriented in space.

    RFC-001 §4.6 trap #1: ANSYS (and some Nastran sets) emit fields in
    a *local* coordinate frame; assuming "global" silently breaks
    cross-solver consistency. The adapter MUST tag every Layer-2 field
    with one of these; ``app.domain.coordinates`` rotates ``LOCAL`` /
    ``NODAL_LOCAL`` into ``GLOBAL`` before stress-derivative work.

    ``UNKNOWN`` exists for adapters that genuinely cannot tell;
    Layer-3 MUST refuse to convert from ``UNKNOWN`` rather than guess
    (ADR-003).
    """

    GLOBAL = "global"
    LOCAL = "local"
    NODAL_LOCAL = "nodal_local"
    UNKNOWN = "unknown"
