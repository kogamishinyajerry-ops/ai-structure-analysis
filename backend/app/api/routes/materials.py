"""Materials library HTTP route — FM-04a Phase 18 E (round 2).

Exposes the Phase 18 C `app.services.materials` library via:

  * ``GET /api/v1/materials/`` — list all materials in file order.
  * ``GET /api/v1/materials/{material_id}`` — fetch one by id.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

The route is read-only (HTTP GET only). The library JSON is
authoritative; the route renders a UI-friendly JSON shape including
the per-material citation source so the reviewer + UI surface can
display provenance without re-reading the JSON.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.materials import (
    MaterialNotFoundError,
    get_material,
    list_materials,
)
from app.services.reporting._claim_tier import CLAIM_TIER_LABELS

router = APIRouter(prefix="/materials", tags=["materials"])

# Phase 18 C inlines a structural-steel default at the smoke-INP
# writer; the live library is broader. The materials API does NOT
# bind a per-material tier — every entry is library data, applicable
# to either Tier 1 candidate or Tier 2 validated cases. The envelope
# that *uses* the material chooses its tier per ADR-025.
_LIBRARY_CLAIM_TIER = CLAIM_TIER_LABELS["tier_1_candidate"]
_LIBRARY_CLAIM_BOUNDARY = (
    "tier1_engineering_candidate; not_signed_validation; "
    "not_benchmark_agreement"
)


def _to_payload(material: Any) -> dict[str, Any]:
    """Render a :class:`Material` as a UI-friendly dict.

    Mirrors the dataclass fields verbatim + carries the library-level
    tier banner so the UI can render the standard Tier 1 disclaimer
    inline without an extra request.
    """
    body = asdict(material)
    body["claim_tier"] = _LIBRARY_CLAIM_TIER
    body["claim_boundary"] = _LIBRARY_CLAIM_BOUNDARY
    return body


@router.get("/")
def get_materials_list() -> dict[str, Any]:
    """Return the full materials library.

    Response shape:

      {
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": "tier1_engineering_candidate; ...",
        "count": 3,
        "materials": [ <Material payload>, ... ]
      }
    """
    materials = list_materials()
    return {
        "claim_tier": _LIBRARY_CLAIM_TIER,
        "claim_boundary": _LIBRARY_CLAIM_BOUNDARY,
        "count": len(materials),
        "materials": [_to_payload(m) for m in materials],
    }


@router.get("/{material_id}")
def get_material_by_id(material_id: str) -> dict[str, Any]:
    """Return one material by stable id, or 404 if unknown."""
    try:
        mat = get_material(material_id)
    except MaterialNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"unknown material id {material_id!r}",
        ) from exc
    return _to_payload(mat)
