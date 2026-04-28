"""Layer-3 domain primitives — RFC-001 §4.3.

These are the *contracts* Layer 4 (report generation) consumes. Real
implementations live under ``app.domain.*`` (W3+). Definitions here
purposefully pin only the surface needed by ``ReaderHandle``.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping, Protocol, runtime_checkable

from .enums import UnitSystem

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


@runtime_checkable
class Mesh(Protocol):
    """Discretization of the model.

    ``node_id_array`` holds the original (possibly non-contiguous) IDs
    from the solver input; ``node_index`` maps those IDs to dense
    ``0..N-1`` indices for numpy work (§4.6 trap #4). UI shows IDs;
    arrays use indices.
    """

    @property
    def node_id_array(self) -> "npt.NDArray[np.int64]": ...

    @property
    def node_index(self) -> dict[int, int]: ...

    @property
    def coordinates(self) -> "npt.NDArray[np.float64]":
        """Node coordinates, shape ``(N, 3)``, in the ``unit_system``'s length unit."""
        ...

    @property
    def unit_system(self) -> UnitSystem: ...


@dataclass(frozen=True)
class Material:
    """Linear-elastic material card with strength + standards-citation
    fields needed for the engineer-signs-DOCX wedge (RFC-001 §2.2 step 4
    "材料属性" + ADR-019).

    The MVP wedge does not need plasticity / damage / temperature
    dependence; those land in M4+ once the wedge proves its value.

    ``yield_strength`` (σ_y) and ``ultimate_strength`` (σ_u) are
    required for the W6b allowable-stress pipeline and the W6c
    PASS/FAIL verdict — without them the safety-factor chain is
    structurally impossible.

    ``source_citation`` is the standard clause the strength values
    came from (e.g. ``"GB/T 1591-2018 §6.2 Table 7"``). It is rendered
    verbatim in the DOCX § 材料属性 row so the signing engineer can
    audit the value back to source.

    ``is_user_supplied=True`` means the engineer typed the values into
    the form rather than picking a built-in; the DOCX renderer adds a
    ``[需工程师确认]`` flag in that case (RFC-001 §2.4 rule 4).
    """

    name: str
    youngs_modulus: float          # E, in unit_system's stress unit
    poissons_ratio: float
    density: float | None          # in unit_system's mass-per-volume; None if unused
    yield_strength: float          # σ_y, in unit_system's stress unit
    ultimate_strength: float       # σ_u, in unit_system's stress unit
    code_standard: str             # "GB" | "ASME" | "EN"
    code_grade: str                # canonical grade per the standard, e.g. "Q345B"
    source_citation: str           # standard clause the values came from
    unit_system: UnitSystem
    is_user_supplied: bool = False


@dataclass(frozen=True)
class BoundaryCondition:
    """A single applied constraint or load.

    ``kind`` is a stringly-typed discriminator (``"fixed"`` / ``"force"`` /
    ``"pressure"`` / ``"displacement"`` / ``"thermal"`` / ...). Kept open
    for now because the cross-solver translation table is still being
    surveyed; an enum will follow once it stabilises.

    Deep immutability: ``components`` is wrapped in ``MappingProxyType``
    on construction so ``frozen=True`` extends to the dict payload too
    (Codex R1 finding MEDIUM-2 — bare ``dict`` allowed in-place mutation
    after construction, weakening the frozen contract).
    """

    name: str
    kind: str
    target: str          # mesh-set label as the solver named it (NSET, ELSET, ...)
    components: Mapping[str, float]
    unit_system: UnitSystem

    def __post_init__(self) -> None:
        # Convert any concrete mapping (typically dict) into an immutable view.
        # ``frozen=True`` only blocks attribute reassignment; without this the
        # caller's dict could still be mutated through ``bc.components[k] = v``.
        if not isinstance(self.components, MappingProxyType):
            object.__setattr__(
                self, "components", MappingProxyType(dict(self.components))
            )
