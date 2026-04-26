"""Result-viewer manifest schema (ADR-016).

The `manifest.json` written under `runs/{run_id}/viz/` indexes the `.vtu`
artifacts produced by the `.frd → .vtu` writer. The viewer SPA fetches
`manifest.json` first to learn which fields exist, default increment,
color-map ranges, and bbox; then fetches specific `.vtu` URIs on demand.

See `docs/adr/ADR-016-frd-vtu-result-viz.md`.
"""

from __future__ import annotations

from typing import (  # noqa: UP035 — Union kept for runtime PEP-604 portability
    Annotated,
    Literal,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field, model_validator

VIZ_MANIFEST_SCHEMA_VERSION: Literal["v1"] = "v1"

IncrementType = Literal["static", "vibration", "buckling"]

# Cell types we currently emit (Phase 2.2 initial coverage).
SupportedCellType = Literal[
    "C3D4",  # tet4
    "C3D10",  # tet10
    "C3D8",  # hex8
    "C3D20",  # hex20
    "S3",  # tri3 shell
    "S4",  # quad4 shell
]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class BBox(_Frozen):
    """Axis-aligned bounding box in mesh-coordinate units."""

    min: tuple[float, float, float]
    max: tuple[float, float, float]

    @model_validator(mode="after")
    def _min_le_max_per_axis(self) -> BBox:
        """R2 (post Codex R1 MED): each axis of `min` must be <= the
        corresponding axis of `max`. A degenerate bbox would render
        the camera-framing logic in vtk.js incorrectly.
        """
        for axis in range(3):
            lo = self.min[axis]
            hi = self.max[axis]
            if lo > hi:
                raise ValueError(f"BBox axis {axis}: min={lo} > max={hi}")
        return self


class Units(_Frozen):
    """Physical units carried over from the originating SimPlan.

    Populated by `run_orchestrator` (ADR-015), NOT inferred from `.frd`.
    """

    length: Literal["m", "mm", "in"]
    stress: Literal["Pa", "MPa", "psi"] | None = None


class MeshSection(_Frozen):
    uri: str = Field(..., description="filename relative to manifest.json")
    n_nodes: int = Field(..., ge=1)
    n_elements: int = Field(..., ge=1)
    element_types: tuple[SupportedCellType, ...]
    bbox: BBox
    units: Units


class DisplacementField(_Frozen):
    kind: Literal["displacement"] = "displacement"
    uri: str
    units: Literal["m", "mm", "in"]
    max_magnitude: float = Field(..., ge=0.0)


class ScalarStressField(_Frozen):
    kind: Literal["von_mises", "max_principal", "min_principal", "mid_principal"]
    uri: str
    units: Literal["Pa", "MPa", "psi"]
    min: float
    max: float

    @model_validator(mode="after")
    def _min_le_max(self) -> ScalarStressField:
        """R2 (post Codex R1 MED): a stress field's `min` must be
        <= `max`. A reversed range would cause vtk.js to render an
        empty / inverted color map silently.
        """
        if self.min > self.max:
            raise ValueError(f"ScalarStressField {self.kind}: min={self.min} > max={self.max}")
        return self


FieldEntry = Annotated[
    Union[DisplacementField, ScalarStressField],  # noqa: UP007 — runtime PEP-604 portability (3.9)
    Field(discriminator="kind"),
]


class IncrementEntry(_Frozen):
    index: int = Field(..., ge=0)
    step: int = Field(..., ge=1)
    type: IncrementType
    value: float
    fields: dict[str, FieldEntry]

    @model_validator(mode="after")
    def _field_keys_match_kinds(self) -> IncrementEntry:
        """R2 (post Codex R1 MED): each `fields` dict key MUST equal
        the `kind` of the FieldEntry it maps to. Without this check,
        the writer could emit `{"displacement": ScalarStressField(...)}`
        and the viewer would fetch the wrong .vtu when the user picks
        "displacement" from the field selector.
        """
        for key, entry in self.fields.items():
            if entry.kind != key:
                raise ValueError(
                    f"IncrementEntry.fields: key {key!r} does not match "
                    f"entry.kind={entry.kind!r}; the dict key is the "
                    f"viewer's field selector and must equal the entry's kind"
                )
        return self


class WriterInfo(_Frozen):
    tool: Literal["backend.app.viz.frd_to_vtu"] = "backend.app.viz.frd_to_vtu"
    version: str
    frd_parser_version: str
    wrote_at: str = Field(..., description="ISO 8601 UTC")


class VizManifest(_Frozen):
    """Top-level manifest written to `runs/{run_id}/viz/manifest.json`."""

    schema_version: Literal["v1"] = VIZ_MANIFEST_SCHEMA_VERSION
    run_id: str = Field(..., min_length=1)
    mesh: MeshSection
    increments: tuple[IncrementEntry, ...] = Field(..., min_length=1)
    skipped_cells: int = Field(0, ge=0)
    writer: WriterInfo


__all__ = [
    "VIZ_MANIFEST_SCHEMA_VERSION",
    "IncrementType",
    "SupportedCellType",
    "BBox",
    "Units",
    "MeshSection",
    "DisplacementField",
    "ScalarStressField",
    "FieldEntry",
    "IncrementEntry",
    "WriterInfo",
    "VizManifest",
]
