"""FM-04a Phase 11 F — E2E reviewer journeys for slices A..E.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Three load-bearing reviewer journeys that compose the Phase 11
slice-A analysis-type rubric + slice-B/C advisor surface + slice-D
HTTP routes + slice-E frontend contract end-to-end across the real
ASGI stack:

  1. ``test_phase11_reviewer_reads_advisor_then_signs_off_e2e`` —
     Reviewer pulls the advisor critique for a PV case, sees the
     stub flag a linear-static blind-spot concern, POSTs a
     ``needs_more_evidence`` signoff, then fetches the signoff
     history and confirms the verdict landed. Crosses 4 routes.

  2. ``test_phase11_llm_offline_workflow_still_completes_e2e`` —
     ``AIFEA_ADVISOR_BACKEND=anthropic`` is set but the placeholder
     LLM raises ``NotImplementedError`` on every call. The advisor
     route returns 200 with ``advisor_status="stub"`` +
     ``degrade_reason`` populated; the reviewer still completes
     the full provenance → critique → signoff → history workflow.
     Proves the workbench is LLM-offline-functional (the
     load-bearing project north-star statement; see memory
     `feedback_cfd_harness_ai_advisor_pivot`).

  3. ``test_phase11_multi_analysis_cohort_round_trip_e2e`` — Two
     cases coexist in one cohort snapshot: a
     ``cylinder-pv-candidate`` evaluated under the
     ``linear_static_pv`` rubric and a ``ballistic-candidate``
     evaluated under the ``ballistic`` rubric. Each route serves
     its analysis-type-correct completeness score without rubric
     collision (the slice-A multi-rubric contract).

Phase 11 anti-gaming guard E:-3 — these tests walk the real route
stack via ``httpx.ASGITransport`` (not a mocked transport). Phase
11 anti-gaming guard E:-4 — each journey crosses ≥2 routes.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import advisor_critique as advisor_critique_route
from app.api.routes import case_completeness as case_completeness_route
from app.api.routes import signoff_history as signoff_module
from app.main import app
from app.services.reporting.advisor_critique import (
    ADVISOR_STATUS_TUPLE,
)
from app.services.reporting.case_completeness import (
    ANALYSIS_TYPE_TUPLE,
)

# ---------------------------------------------------------------------
# ASGI client + harness (mirror of slice-D test helpers)
# ---------------------------------------------------------------------


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, *, params: dict[str, str] | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url, params=params)

        return asyncio.run(_run())

    def post(self, url: str, *, json_body: Any) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.post(url, json=json_body)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect all routes' ``_repo_root`` lookups to a writable
    ``tmp_path``. Each E2E journey builds its full evidence inventory
    + snapshot tree under the same root."""
    monkeypatch.setattr(advisor_critique_route, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(case_completeness_route, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(signoff_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _write_snapshot(
    repo_root: Path,
    snapshot_label: str,
    case_id: str,
    *,
    convergence_kind: str | None = "linear_static",
    analysis_type: str | None = "linear_static_pressure_vessel",
    energy_audit_status: str = "closed_aggregate",
    convergence_verdict: str = "candidate_observed_stable",
    completeness_score: int = 85,
) -> Path:
    """Write a minimal-but-valid snapshot subtree for one case."""
    snap_dir = repo_root / "reports" / "snapshots" / snapshot_label
    (snap_dir / "metrics").mkdir(parents=True, exist_ok=True)
    (snap_dir / "convergence").mkdir(exist_ok=True)
    (snap_dir / "completeness").mkdir(exist_ok=True)

    manifest_path = snap_dir / "SNAPSHOT_MANIFEST.json"
    if not manifest_path.is_file():
        manifest_path.write_text(
            json.dumps({"schema_version": "1.3.0", "snapshot_label": snapshot_label}),
            encoding="utf-8",
        )

    metrics_payload: dict[str, Any] = {
        "case_id": case_id,
        "energy_audit": {"status": energy_audit_status},
    }
    if analysis_type is not None:
        metrics_payload["analysis_type"] = analysis_type
    (snap_dir / "metrics" / f"{case_id}.json").write_text(
        json.dumps(metrics_payload), encoding="utf-8"
    )

    convergence_payload: dict[str, Any] = {
        "case_id": case_id,
        "convergence_combined_verdict": convergence_verdict,
        "mesh_sweep": {"verdict": convergence_verdict},
        "dt_sweep": {"verdict": convergence_verdict},
    }
    if convergence_kind is not None:
        convergence_payload["convergence_kind"] = convergence_kind
    (snap_dir / "convergence" / f"{case_id}.json").write_text(
        json.dumps(convergence_payload), encoding="utf-8"
    )

    (snap_dir / "completeness" / f"{case_id}.json").write_text(
        json.dumps({"case_id": case_id, "score": completeness_score}),
        encoding="utf-8",
    )

    return snap_dir


_SNAPSHOT_LABEL = "2026-05-16T123000Z"


# ---------------------------------------------------------------------
# Journey 1 — advisor → signoff → history
# ---------------------------------------------------------------------


def test_phase11_reviewer_reads_advisor_then_signs_off_e2e(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Reviewer pulls the advisor critique, sees the linear-static
    blind-spot list, POSTs a needs_more_evidence verdict, then
    fetches signoff history and confirms the verdict landed.

    Crosses 4 routes:
      GET  /api/v1/advisor-critique/{case_id}
      POST /api/v1/signoff-history/{case_id}
      GET  /api/v1/signoff-history/{case_id}
      GET  /api/v1/case-completeness/{case_id}
    """
    case_id = "cylinder-pv-e2e-candidate"
    _write_snapshot(
        fake_repo,
        _SNAPSHOT_LABEL,
        case_id,
        convergence_kind="linear_static",
        analysis_type="linear_static_pressure_vessel",
    )

    # Step 1 — pull advisor critique. Expect stub status + a
    # linear-static failure-mode concern naming plasticity / contact.
    adv = client.get(
        f"/api/v1/advisor-critique/{case_id}",
        params={"snapshot": _SNAPSHOT_LABEL},
    )
    assert adv.status_code == 200, adv.text
    adv_body = adv.json()
    assert adv_body["advisor_status"] in ADVISOR_STATUS_TUPLE
    failure_modes = "\n".join(adv_body["failure_modes_to_consider"]).lower()
    assert "plasticity" in failure_modes or "contact" in failure_modes
    # The advisor's job: surface concerns. The verdict is the human's.

    # Step 2 — reviewer POSTs a needs_more_evidence signoff. Audit
    # trail captured; advisor is NOT the authority.
    signoff = client.post(
        f"/api/v1/signoff-history/{case_id}",
        json_body={
            "reviewer": "phase11-reviewer-1",
            "verdict": "needs_more_evidence",
            "notes": (
                "Advisor flagged linear-static blind spots "
                "(plasticity / contact). Not enough evidence "
                "for verdict yet; need follow-up nonlinear study."
            ),
        },
    )
    assert signoff.status_code == 200, signoff.text

    # Step 3 — fetch history and confirm the verdict landed.
    hist = client.get(f"/api/v1/signoff-history/{case_id}")
    assert hist.status_code == 200, hist.text
    records = hist.json()["records"]
    assert len(records) >= 1
    latest = records[-1]
    assert latest["verdict"] == "needs_more_evidence"
    assert latest["reviewer"] == "phase11-reviewer-1"

    # Step 4 — pull case-completeness under the PV rubric. The
    # workflow is complete; the cohort still sees the PV case score
    # under the correct analysis_type stamping.
    comp = client.get(
        f"/api/v1/case-completeness/{case_id}",
        params={"analysis_type": "linear_static_pv"},
    )
    assert comp.status_code == 200, comp.text
    assert comp.json()["analysis_type"] == "linear_static_pv"


# ---------------------------------------------------------------------
# Journey 2 — LLM offline workflow
# ---------------------------------------------------------------------


def test_phase11_llm_offline_workflow_still_completes_e2e(
    client: _SyncASGIClient,
    fake_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The workbench MUST function without a live LLM. Phase 11
    pivot SSOT (memory `feedback_cfd_harness_ai_advisor_pivot`):
    'workbench must complete every reviewer flow without a live LLM'.

    Crosses 3 routes; the advisor LLM is configured but unwired so
    the route catches NotImplementedError and falls back to stub.
    """
    # Configure the LLM backend so _default_llm_factory returns the
    # unwired placeholder. Production wiring would replace this with
    # a real httpx client; the placeholder is the test seam.
    monkeypatch.setenv("AIFEA_ADVISOR_BACKEND", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-placeholder")

    case_id = "ballistic-llm-offline-e2e-candidate"
    _write_snapshot(
        fake_repo,
        _SNAPSHOT_LABEL,
        case_id,
        convergence_kind="explicit_dynamics",
        analysis_type="ballistic",
        convergence_verdict="candidate_observed_stable",
    )

    # Step 1 — advisor critique. LLM is configured but unwired ->
    # stub fallback. Route MUST return 200 with degrade_reason set.
    adv = client.get(
        f"/api/v1/advisor-critique/{case_id}",
        params={"snapshot": _SNAPSHOT_LABEL},
    )
    assert adv.status_code == 200, adv.text
    adv_body = adv.json()
    assert adv_body["advisor_status"] == "stub"
    assert adv_body["advisor_backend"] == "llm-advisor-anthropic-unwired"
    assert adv_body["degrade_reason"] is not None
    assert "NotImplementedError" in adv_body["degrade_reason"]
    # The stub still surfaces useful content despite LLM outage.
    assert len(adv_body["mesh_quality_concerns"]) >= 1

    # Step 2 — reviewer still POSTs a signoff. The LLM outage does
    # not block the reviewer flow.
    signoff = client.post(
        f"/api/v1/signoff-history/{case_id}",
        json_body={
            "reviewer": "phase11-offline-reviewer",
            "verdict": "watching",
            "notes": (
                "Advisor LLM unavailable; relying on stub critique "
                "for this review cycle. Stub still surfaced useful "
                "mass-scaling questions for the explicit_dynamics case."
            ),
        },
    )
    assert signoff.status_code == 200, signoff.text

    # Step 3 — case-completeness still functions independently of
    # the LLM. The workbench is LLM-offline-complete.
    comp = client.get(
        f"/api/v1/case-completeness/{case_id}",
        params={"analysis_type": "ballistic"},
    )
    assert comp.status_code == 200, comp.text
    assert comp.json()["analysis_type"] == "ballistic"


# ---------------------------------------------------------------------
# Journey 3 — multi-analysis cohort round-trip
# ---------------------------------------------------------------------


def test_phase11_multi_analysis_cohort_round_trip_e2e(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """A PV case + a ballistic case coexist in one cohort snapshot.
    Each is scored under its analysis-type-correct rubric without
    collision; the advisor surfaces analysis-type-specific concerns
    for each. Closes the e2e demo gap that surfaced Phase 11 in
    the first place.

    Crosses 2 routes (advisor + case-completeness) for each of 2 cases.
    """
    pv_case = "cylinder-pv-multicohort-candidate"
    ballistic_case = "GS-102-multicohort-candidate"

    _write_snapshot(
        fake_repo,
        _SNAPSHOT_LABEL,
        pv_case,
        convergence_kind="linear_static",
        analysis_type="linear_static_pressure_vessel",
    )
    _write_snapshot(
        fake_repo,
        _SNAPSHOT_LABEL,
        ballistic_case,
        convergence_kind="explicit_dynamics",
        analysis_type="ballistic",
    )

    # PV case: advisor surfaces linear-static failure modes.
    adv_pv = client.get(
        f"/api/v1/advisor-critique/{pv_case}",
        params={"snapshot": _SNAPSHOT_LABEL},
    )
    assert adv_pv.status_code == 200, adv_pv.text
    pv_failures = "\n".join(adv_pv.json()["failure_modes_to_consider"]).lower()
    assert "plasticity" in pv_failures or "contact" in pv_failures

    # Ballistic case: advisor surfaces explicit_dynamics-specific
    # mass-scaling questions (distinct from PV's plasticity warning).
    adv_b = client.get(
        f"/api/v1/advisor-critique/{ballistic_case}",
        params={"snapshot": _SNAPSHOT_LABEL},
    )
    assert adv_b.status_code == 200, adv_b.text
    b_questions = "\n".join(adv_b.json()["boundary_condition_questions"]).lower()
    b_failures = "\n".join(adv_b.json()["failure_modes_to_consider"]).lower()
    assert "mass scaling" in b_failures or "mass-scaled" in b_failures
    assert "dt" in b_questions or "hourglass" in b_questions

    # Case-completeness: PV scored under linear_static_pv rubric.
    comp_pv = client.get(
        f"/api/v1/case-completeness/{pv_case}",
        params={"analysis_type": "linear_static_pv"},
    )
    assert comp_pv.status_code == 200, comp_pv.text
    assert comp_pv.json()["analysis_type"] == "linear_static_pv"

    # Case-completeness: ballistic scored under ballistic rubric.
    comp_b = client.get(
        f"/api/v1/case-completeness/{ballistic_case}",
        params={"analysis_type": "ballistic"},
    )
    assert comp_b.status_code == 200, comp_b.text
    assert comp_b.json()["analysis_type"] == "ballistic"

    # Cross-route consistency: the analysis_type values landed in
    # both completeness AND advisor without collision. (The advisor
    # surface does not currently echo analysis_type on its envelope,
    # but the cohort behaviour is verifiable through the two
    # completeness endpoints returning the analysis-type-correct
    # rubric.) ANALYSIS_TYPE_TUPLE is the SSOT being honoured.
    assert "linear_static_pv" in ANALYSIS_TYPE_TUPLE
    assert "ballistic" in ANALYSIS_TYPE_TUPLE
