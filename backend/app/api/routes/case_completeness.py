"""Tier 1 candidate evidence completeness endpoint (FM-04a Phase 4 A; Phase 11 D analysis-type extension).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/case-completeness/<case-id>?analysis_type=<type>`` reads
the case's evidence inventory off disk and returns a structured
completeness score against the rubric for the chosen analysis type.
Read-only; never writes inside ``golden_samples/**``. The score is an
evidence-presence signal, NOT a validation-quality signal: even
100/100 keeps every FM-04b blocker visible in the rendered output.

Phase 11 D extends the endpoint with:
  * ``?analysis_type=<type>`` query parameter ∈ ``ANALYSIS_TYPE_TUPLE``
    (currently ``ballistic`` / ``linear_static_pv`` / ``explicit_dynamics`` /
    ``modal``). Default: ``ballistic`` for back-compat with pre-Phase-11
    clients that did not send the parameter.
  * 422 with the allowed-set echoed in the detail on invalid value.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.reporting.case_completeness import (
    ANALYSIS_TYPE_TUPLE,
    DEFAULT_ANALYSIS_TYPE,
    CaseCompletenessInputs,
    render_case_completeness_json,
    score_case_completeness,
)

router = APIRouter(prefix="/case-completeness", tags=["case-completeness"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# Phase 13 B — signed-registry shape `^GS-\d{3}$`. The case-completeness
# route refuses signed-registry case_ids for the same reason advisor-critique
# does: Tier 1 candidate surfaces only accept ``*-candidate`` identifiers;
# sealed FM-04b packets are out of scope. Closes the slice-F LOW finding
# (Phase 12 retro / Phase 13 B carry-forward) where the advisor-critique
# route refused GS-NNN at 422 but case-completeness silently returned 200
# with an all-zero score (cohort surface inconsistency).
_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _build_inputs_for(case_id: str, analysis_type: str) -> CaseCompletenessInputs:
    repo_root = _repo_root()
    case_dir = repo_root / "golden_samples" / case_id
    starter_deck = case_dir / "data" / "model_00_0000.rad"
    engine_deck = case_dir / "data" / "model_00_0001.rad"
    notes = case_dir / "NOTES.md"

    metrics_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    convergence_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    animation_manifest_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    result_mesh_path = repo_root / "project_state" / "visualizations" / case_id / "result_mesh.json"

    # Generator script lives in scripts/gen_<slug>_deck.py.
    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator_script = repo_root / "scripts" / f"gen_{slug}_deck.py"

    return CaseCompletenessInputs(
        case_id=case_id,
        starter_deck_path=starter_deck,
        engine_deck_path=engine_deck,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path,
        animation_manifest_path=animation_manifest_path,
        result_mesh_path=result_mesh_path,
        generator_script_path=generator_script,
        notes_path=notes,
        analysis_type=analysis_type,
    )


@router.get("/{case_id}")
async def get_case_completeness(
    case_id: str,
    analysis_type: str = Query(
        DEFAULT_ANALYSIS_TYPE,
        description=(
            "Analysis type whose rubric to apply. One of "
            f"{ANALYSIS_TYPE_TUPLE}. Defaults to {DEFAULT_ANALYSIS_TYPE!r} "
            "for back-compat with pre-Phase-11 clients."
        ),
    ),
):
    """Score one Tier 1 candidate case's evidence completeness.

    Validation gate order:
      1. **400** if ``case_id`` shape is invalid (preserved from
         Phase 4 A for back-compat).
      2. **422** if ``case_id`` matches the signed-registry shape
         ``^GS-\\d{3}$`` (Phase 13 B: aligns with advisor-critique
         refusal so all cohort surfaces refuse signed-registry IDs
         consistently).
      3. **422** if ``analysis_type`` is not in
         :data:`ANALYSIS_TYPE_TUPLE`. The allowed set is echoed in
         the detail.
      4. **200** with the rebuilt scorecard JSON otherwise. The
         scorecard's top-level ``analysis_type`` field equals the
         requested value (Phase 11 A schema 1.1.0).
    """
    if not _CASE_ID_RE.fullmatch(case_id):
        # Preserved at 400 from Phase 4 A for back-compat with existing
        # Phase 4 endpoint tests. Phase 11 D only INTRODUCES the new
        # 422-on-invalid-analysis_type gate; existing 400 behavior is
        # unchanged.
        raise HTTPException(status_code=400, detail="invalid case_id")
    # Phase 13 B — signed-registry refusal at 422 (matches advisor-critique).
    # Closes the Phase 12 F slice-F LOW finding where GS-NNN silently
    # resolved to a 200 all-zero scorecard; cohort surfaces now refuse
    # signed-registry case_ids consistently across all reviewer-facing
    # routes.
    if _SIGNED_REGISTRY_RE.fullmatch(case_id):
        raise HTTPException(
            status_code=422,
            detail=(
                "case-completeness refuses signed-registry case_id; "
                "Tier 1 candidate surfaces only accept *-candidate "
                "identifiers (sealed FM-04b packets are out of scope)"
            ),
        )
    if analysis_type not in ANALYSIS_TYPE_TUPLE:
        raise HTTPException(
            status_code=422,
            detail=(
                f"invalid analysis_type {analysis_type!r}; allowed: "
                f"{list(ANALYSIS_TYPE_TUPLE)}"
            ),
        )
    inputs = _build_inputs_for(case_id, analysis_type)
    score = score_case_completeness(inputs)
    payload = render_case_completeness_json(score)
    return Response(content=payload, media_type="application/json")
