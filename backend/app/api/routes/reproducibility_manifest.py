"""Tier 1 candidate reproducibility manifest endpoint (FM-04a Phase 5 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/reproducibility-manifest/<case-id>`` returns a JSON
manifest capturing the *environment* in which a Tier 1 candidate case's
evidence was produced: git commit + dirty flag, Python interpreter,
tracked package versions, and SHA-256 fingerprints of the case's
generator scripts.

The endpoint does NOT execute the case and does NOT touch
``golden_samples/**``. The manifest is a Tier 1 reviewer aid; it is
NOT a Tier 2 byte-frozen dependency registry.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.reproducibility_manifest import (
    ReproducibilityManifestInputs,
    build_reproducibility_manifest,
    render_reproducibility_manifest_json,
)
from ._signed_registry_refusal import assert_not_signed_registry

router = APIRouter(
    prefix="/reproducibility-manifest", tags=["reproducibility-manifest"]
)

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _generator_script_for(case_id: str, repo_root: Path) -> Path:
    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    return repo_root / "scripts" / f"gen_{slug}_deck.py"


@router.get("/{case_id}")
async def get_reproducibility_manifest(case_id: str):
    """Return the Tier 1 reproducibility manifest for one case."""
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    # Phase 14 A — cross-route signed-registry refusal (SSOT helper).
    assert_not_signed_registry(case_id, "reproducibility-manifest")
    repo_root = _repo_root()
    inputs = ReproducibilityManifestInputs(
        case_id=case_id,
        repo_root=repo_root,
        generator_script_path=_generator_script_for(case_id, repo_root),
    )
    manifest = build_reproducibility_manifest(inputs)
    payload = render_reproducibility_manifest_json(manifest)
    return Response(content=payload, media_type="application/json")
