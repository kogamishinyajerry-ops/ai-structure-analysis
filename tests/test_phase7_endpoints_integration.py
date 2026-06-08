"""HTTP-layer integration tests for FM-04a Phase 7 endpoints.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Drives every Phase 7 endpoint through a real httpx ASGI transport.
Same ``_SyncASGIClient`` shim as Phase 5 / 6.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import cohort_snapshot_diff as cohort_snapshot_diff_module
from app.api.routes import snapshot_narrative as snapshot_narrative_module
from app.api.routes import trust_score_alerts as trust_score_alerts_module
from app.main import app
from app.services.reporting._schema_versions import (
    SNAPSHOT_NARRATIVE_SCHEMA_VERSION,
    TRUST_SCORE_ALERTS_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_MANIFEST_FILENAME,
    snapshots_root,
)


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url, params=params)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_root = tmp_path

    def fake_repo_root() -> Path:
        return fake_root

    monkeypatch.setattr(snapshot_narrative_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshot_diff_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(trust_score_alerts_module, "_repo_root", fake_repo_root)
    return fake_root


def _seed_snapshot(
    repo_root: Path,
    label: str,
    *,
    case_id: str = "GS-A-candidate",
    completeness: int = 80,
    convergence_verdict: str = "candidate_observed_stable",
    git_dirty: bool = False,
) -> None:
    root = snapshots_root(repo_root) / label
    root.mkdir(parents=True, exist_ok=True)
    (root / "completeness").mkdir(parents=True, exist_ok=True)
    (root / "reproducibility").mkdir(parents=True, exist_ok=True)
    (root / "metrics").mkdir(parents=True, exist_ok=True)
    (root / "convergence").mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.2.0",
        "snapshot_label": label,
        "captured_at_utc": f"2026-05-16T{label[11:13]}:00:00+00:00",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "cohort_count": 1,
        "cases": [case_id],
        "members": [],
        "reviewer_bundle_written": False,
        "tier2_blockers_remaining": [],
        "claim_impact": (
            "Tier 1 candidate cohort snapshot only; not signed validation; not benchmark agreement"
        ),
    }
    (root / SNAPSHOT_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    (root / "completeness" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "case_id": case_id,
                "score": completeness,
                "score_max": 100,
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )
    (root / "reproducibility" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "case_id": case_id,
                "git_commit_sha": "a" * 40,
                "git_dirty": git_dirty,
                "python_version": "3.11.5",
                "tracked_packages": [],
                "scripts": [],
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )
    (root / "metrics" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "perforation": {
                    "marker": "candidate_perforation",
                    "residual_velocity_m_per_s": 75.0,
                },
                "energy_audit": {
                    "status": "closed_aggregate",
                    "energy_balance_error_pct": 8.0,
                },
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )
    (root / "convergence" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "combined_verdict": convergence_verdict,
                "mesh_sweep": {"runs": [], "candidate_stability": convergence_verdict},
                "dt_sweep": {"runs": [], "candidate_stability": convergence_verdict},
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# /api/v1/snapshot-narrative?locale=
# ---------------------------------------------------------------------


def test_narrative_endpoint_defaults_to_en_us(client: _SyncASGIClient, fake_repo: Path) -> None:
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=70)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=90)
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == SNAPSHOT_NARRATIVE_SCHEMA_VERSION
    assert payload["locale"] == "en-US"


def test_narrative_endpoint_renders_zh_cn(client: _SyncASGIClient, fake_repo: Path) -> None:
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=70)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=90)
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={
            "a": "2026-05-16T100000Z",
            "b": "2026-05-16T200000Z",
            "locale": "zh-CN",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["locale"] == "zh-CN"
    # at least one zh-CN translated string surfaces in the *parsed*
    # narrative lines (response.text is ASCII-escaped via Python's
    # json.dumps default; the parsed text fields carry the real glyphs).
    all_texts = " ".join(line["text"] for case in payload["narratives"] for line in case["lines"])
    assert "提升" in all_texts or "回退" in all_texts or "保持" in all_texts


def test_narrative_endpoint_rejects_unknown_locale(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(fake_repo, "2026-05-16T100000Z")
    _seed_snapshot(fake_repo, "2026-05-16T200000Z")
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={
            "a": "2026-05-16T100000Z",
            "b": "2026-05-16T200000Z",
            "locale": "fr-FR",
        },
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------
# /api/v1/trust-score-alerts/<case-id>?threshold_delta=
# ---------------------------------------------------------------------


def test_alerts_endpoint_returns_stamped_payload(client: _SyncASGIClient, fake_repo: Path) -> None:
    res = client.get("/api/v1/trust-score-alerts/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == TRUST_SCORE_ALERTS_SCHEMA_VERSION
    assert payload["case_id"] == "GS-A-candidate"
    assert payload["threshold_delta"] == 10
    assert payload["alert_count"] == 0
    # Tier 1 + Tier-2-not-authorized in body
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body
    assert "not authorize tier 2" in body


def test_alerts_endpoint_rejects_invalid_case_id(client: _SyncASGIClient, fake_repo: Path) -> None:
    # Phase 13 B — tightened from `in {400, 404, 422}` to exact 404.
    # ``..%2Fescape`` is URL-decoded to ``../escape`` and the Starlette
    # path matcher rejects the traversal at the routing layer with 404
    # ``Not Found`` BEFORE the route handler's case_id regex runs.
    # Permissive ranges hid which layer is authoritative.
    res = client.get("/api/v1/trust-score-alerts/..%2Fescape")
    assert res.status_code == 404


def test_alerts_endpoint_clamps_threshold_below_min(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": -5},
    )
    # fastapi Query(ge=1) -> 422 for out-of-range
    assert res.status_code == 422


def test_alerts_endpoint_clamps_threshold_above_max(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": 500},
    )
    assert res.status_code == 422


def test_alerts_endpoint_returns_severity_buckets(client: _SyncASGIClient, fake_repo: Path) -> None:
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=100)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=20)
    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": 1},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["alert_count"] >= 1
    severity = payload["alerts"][0]["severity"]
    assert severity in {"info", "warn", "danger"}


# ---------------------------------------------------------------------
# /api/v1/cohort-snapshot-diff after Phase 7 A convergence capture
# ---------------------------------------------------------------------


def test_diff_endpoint_recovers_convergence_verdict_from_captured_file(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 7 A integration: the diff endpoint must surface the
    convergence verdict pair from the captured convergence/<case>.json
    when the metrics file has no inline summary."""
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        convergence_verdict="candidate_observed_stable",
    )
    _seed_snapshot(
        fake_repo,
        "2026-05-16T200000Z",
        convergence_verdict="candidate_observed_unstable",
    )
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    numerical = payload["numerical_deltas"][0]
    verdict_pair = numerical["convergence_combined_verdict"]
    assert verdict_pair["a"] == "candidate_observed_stable"
    assert verdict_pair["b"] == "candidate_observed_unstable"


# ---------------------------------------------------------------------
# Slice-G TAA fixup batch — close the ≥14 integration floor (was 9).
# Per TAA report .planning/phase7_audit_reports/G.md, the named gaps:
#   - narrative envelope disclaimer round-trip
#   - cross-locale forbidden-claim audit at HTTP boundary
#   - stable-cohort no-alarms positive
#   - 3 severity boundary pins (info_min=10, warn_min=25, danger_min=40)
# ---------------------------------------------------------------------


def test_narrative_endpoint_envelope_carries_tier1_disclaimer_trio(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Slice-G TAA fixup — the narrative envelope round-trips the Tier 1
    disclaimer trio through both locales (envelope strings stay English
    even when locale=zh-CN per Phase 7 B claim_impact policy)."""
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=70)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=90)
    for locale in ("en-US", "zh-CN"):
        res = client.get(
            "/api/v1/snapshot-narrative",
            params={
                "a": "2026-05-16T100000Z",
                "b": "2026-05-16T200000Z",
                "locale": locale,
            },
        )
        payload = res.json()
        assert payload["claim_tier"] == "Tier 1 engineering candidate"
        assert "not signed validation" in payload["claim_impact"]
        assert "not benchmark agreement" in payload["claim_impact"]


def test_narrative_endpoint_no_forbidden_claim_in_zh_cn_body(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Slice-G TAA fixup — at the HTTP boundary, the zh-CN narrative
    must not surface any of the forbidden positive claims even in
    translated form. Cross-locale forbidden-claim audit."""
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=60)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=95)
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={
            "a": "2026-05-16T100000Z",
            "b": "2026-05-16T200000Z",
            "locale": "zh-CN",
        },
    )
    body_lower = res.text.lower()
    # All four envelope-forbidden tokens must be absent (the disclaimer
    # form "not <claim>" only legitimately surfaces "signed validation"
    # and "benchmark agreement" — those are EXCLUDED from this audit
    # per the slice-B post-fix two-list design)
    for token in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert token not in body_lower


def test_alerts_endpoint_no_alarms_when_cohort_stable(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Slice-G TAA fixup — stable-cohort positive: 3 snapshots with
    identical scores produce alert_count=0 and the Tier 1 disclaimer
    is still present on the empty payload."""
    for label in (
        "2026-05-16T100000Z",
        "2026-05-16T200000Z",
        "2026-05-16T300000Z",
    ):
        _seed_snapshot(fake_repo, label, completeness=80)
    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": 1},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["alert_count"] == 0
    assert payload["alerts"] == []
    body_lower = res.text.lower()
    assert "tier 1 engineering candidate" in body_lower
    assert "not authorize tier 2" in body_lower


def test_alerts_endpoint_severity_info_at_boundary(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Slice-G TAA fixup — severity boundary pin at info_min=10.

    Trust-score arithmetic: completeness 100 → 80 with all other axes
    held constant produces a delta of exactly 10 weighted points
    (50 - 40 = 10). The severity must be 'info'.
    """
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=100)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=80)
    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": 1},
    )
    payload = res.json()
    assert payload["alert_count"] == 1
    alert = payload["alerts"][0]
    assert alert["delta"] == 10
    assert alert["severity"] == "info"
    assert alert["primary_axis_shift"] == "completeness"


def test_alerts_endpoint_severity_warn_at_boundary(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Slice-G TAA fixup — severity boundary pin at warn_min=25.

    completeness 100 → 50 produces a delta of exactly 25 weighted
    points (50 - 25 = 25). The severity must be 'warn'.
    """
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=100)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=50)
    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": 1},
    )
    payload = res.json()
    assert payload["alert_count"] == 1
    alert = payload["alerts"][0]
    assert alert["delta"] == 25
    assert alert["severity"] == "warn"
    assert alert["primary_axis_shift"] == "completeness"


def test_alerts_endpoint_severity_danger_at_boundary(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Slice-G TAA fixup — severity boundary pin at danger_min=40.

    completeness 100 → 20 produces a delta of exactly 40 weighted
    points (50 - 10 = 40). The severity must be 'danger'.
    """
    _seed_snapshot(fake_repo, "2026-05-16T100000Z", completeness=100)
    _seed_snapshot(fake_repo, "2026-05-16T200000Z", completeness=20)
    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": 1},
    )
    payload = res.json()
    assert payload["alert_count"] == 1
    alert = payload["alerts"][0]
    assert alert["delta"] == 40
    assert alert["severity"] == "danger"
    assert alert["primary_axis_shift"] == "completeness"
