"""Tier 1 candidate cohort snapshot listing endpoint (FM-04a Phase 5 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/cohort-snapshots`` enumerates the cohort snapshots
already written under ``reports/snapshots/<UTC>/`` by the Phase 5 C
CLI (``scripts/write_cohort_snapshot.py``). Returns one entry per
snapshot directory whose ``SNAPSHOT_MANIFEST.json`` is readable.

Read-only; never writes inside ``golden_samples/**``. Listing is the
read side of the snapshot workflow; ``Phase 5 D`` adds the diff
endpoint over two listed snapshots.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

from ...services.reporting.cohort_snapshot import render_snapshot_listing_json

router = APIRouter(prefix="/cohort-snapshots", tags=["cohort-snapshots"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("")
async def get_cohort_snapshots():
    """List every cohort snapshot written under ``reports/snapshots/``."""
    payload = render_snapshot_listing_json(_repo_root())
    return Response(content=payload, media_type="application/json")
