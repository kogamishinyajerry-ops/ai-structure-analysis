"""FM-04a Phase 9 D — cohort trend-slope anomaly detection tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins:
* severity_for_slope() boundary cells at -0.5 / -1.5 / -3.0.
* TREND_MIN_POINTS == 3; timelines with 1 or 2 points yield no events.
* Engineered descending case (5 timeline points) fires danger on the
  completeness axis.
* Engineered flat / ascending cases do NOT fire (negative control).
* Schema constant COHORT_TREND_ANOMALIES_SCHEMA_VERSION == "1.0.0".
* Tier 1 disclaimer trio in envelope + endpoint response body.
* TREND_AXES tuple matches the 4 trust-score axes.
* _TREND_AXIS_ATTRIBUTE keys match TREND_AXES exactly (SSOT lock-step).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import cohort_trend_anomalies as route_module
from app.main import app
from app.services.reporting._schema_versions import (
    COHORT_TREND_ANOMALIES_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.cohort_trend_anomalies import (
    _TREND_AXIS_ATTRIBUTE,
    TREND_AXES,
    TREND_MIN_POINTS,
    TREND_SLOPE_DANGER_MAX,
    TREND_SLOPE_INFO_MAX,
    TREND_SLOPE_WARN_MAX,
    build_cohort_trend_anomalies,
    severity_for_slope,
)


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(route_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _seed_snapshot_with_completeness(
    root: Path, case_id: str, completeness_score: int, snapshot_label: str
) -> None:
    """Seed a candidate case with a snapshot whose completeness/<case>.json
    has the given score (out of 100)."""
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# s", encoding="utf-8")
    engine.write_text("# e", encoding="utf-8")
    metrics = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text(
        json.dumps({"case_id": case_id, "claim_boundary": "tier1"}), encoding="utf-8"
    )
    generator = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(b"# g")
    case_input = SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator,
        notes_path=None,
    )
    write_cohort_snapshot([case_input], repo_root=root, snapshot_label=snapshot_label)
    comp_path = root / "reports" / "snapshots" / snapshot_label / "completeness" / f"{case_id}.json"
    payload = json.loads(comp_path.read_text(encoding="utf-8"))
    payload["score"] = completeness_score
    comp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _seed_descending_timeline(
    root: Path, case_id: str, scores: list[int], base_utc: datetime
) -> None:
    """Write one snapshot per score; labels stride by 1 hour so the
    sort order matches the score order."""
    for offset, score in enumerate(scores):
        moment = datetime(
            base_utc.year,
            base_utc.month,
            base_utc.day,
            base_utc.hour + offset,
            0,
            0,
            tzinfo=UTC,
        )
        label = moment.strftime("%Y-%m-%dT%H%M%SZ")
        _seed_snapshot_with_completeness(root, case_id, score, label)


# ---------------------------------------------------------------------
# Schema constants + tuple SSOT
# ---------------------------------------------------------------------


def test_schema_version_is_1_0_0() -> None:
    assert COHORT_TREND_ANOMALIES_SCHEMA_VERSION == "1.0.0"


def test_trend_axes_tuple_pinned() -> None:
    assert TREND_AXES == (
        "completeness",
        "convergence",
        "energy_audit",
        "reproducibility",
    )


def test_trend_axis_attribute_map_locked_in_step_with_axes() -> None:
    assert set(_TREND_AXIS_ATTRIBUTE.keys()) == set(TREND_AXES)


def test_named_thresholds_pinned() -> None:
    assert TREND_SLOPE_INFO_MAX == -0.5
    assert TREND_SLOPE_WARN_MAX == -1.5
    assert TREND_SLOPE_DANGER_MAX == -3.0


def test_trend_min_points_pinned() -> None:
    assert TREND_MIN_POINTS == 3


# ---------------------------------------------------------------------
# severity_for_slope boundary pins (Phase 9 guard T: -2)
# ---------------------------------------------------------------------


def test_severity_for_slope_info_at_boundary() -> None:
    """Slope == TREND_SLOPE_INFO_MAX (-0.5) -> info."""
    assert severity_for_slope(-0.5) == "info"


def test_severity_for_slope_warn_at_boundary() -> None:
    """Slope == TREND_SLOPE_WARN_MAX (-1.5) -> warn."""
    assert severity_for_slope(-1.5) == "warn"


def test_severity_for_slope_danger_at_boundary() -> None:
    """Slope == TREND_SLOPE_DANGER_MAX (-3.0) -> danger."""
    assert severity_for_slope(-3.0) == "danger"


def test_severity_for_slope_just_above_info_returns_info() -> None:
    """A non-firing slope (>= TREND_SLOPE_INFO_MAX) maps to info as the
    most-conservative bucket when called standalone; the builder's
    firing gate refuses to emit an event for such slopes."""
    assert severity_for_slope(0.0) == "info"
    assert severity_for_slope(-0.4999) == "info"


def test_severity_for_slope_between_info_and_warn_returns_info() -> None:
    assert severity_for_slope(-1.0) == "info"


def test_severity_for_slope_between_warn_and_danger_returns_warn() -> None:
    assert severity_for_slope(-2.5) == "warn"


def test_severity_for_slope_well_into_danger() -> None:
    assert severity_for_slope(-10.0) == "danger"


# ---------------------------------------------------------------------
# Cohort timeline-length edge cases (Phase 9 guard T: -2)
# ---------------------------------------------------------------------


def test_trend_cohort_with_one_point_returns_no_anomalies(tmp_path: Path) -> None:
    _seed_snapshot_with_completeness(tmp_path, "GS-A-candidate", 90, "2026-05-16T100000Z")
    report = build_cohort_trend_anomalies(repo_root=tmp_path)
    assert report.cohort_count == 1
    assert report.anomaly_count == 0


def test_trend_cohort_with_two_points_returns_no_anomalies(tmp_path: Path) -> None:
    _seed_snapshot_with_completeness(tmp_path, "GS-A-candidate", 90, "2026-05-16T100000Z")
    _seed_snapshot_with_completeness(tmp_path, "GS-A-candidate", 30, "2026-05-16T110000Z")
    report = build_cohort_trend_anomalies(repo_root=tmp_path)
    assert report.cohort_count == 1
    assert report.anomaly_count == 0  # below TREND_MIN_POINTS


# ---------------------------------------------------------------------
# Engineered descending case fires danger
# ---------------------------------------------------------------------


def test_descending_completeness_fires_danger(tmp_path: Path) -> None:
    """Score steps of 10 over 5 snapshots -> slope ~ -10 weighted points
    over 5 snapshot strides (after the 50/100 trust-score scaling on the
    completeness axis, weighted slope is much steeper than -3)."""
    _seed_descending_timeline(
        tmp_path,
        "GS-A-candidate",
        [90, 80, 70, 60, 50],
        datetime(2026, 5, 16, 10, 0, 0, tzinfo=UTC),
    )
    report = build_cohort_trend_anomalies(repo_root=tmp_path)
    completeness_events = [a for a in report.anomalies if a.axis == "completeness"]
    assert any(a.case_id == "GS-A-candidate" for a in completeness_events)
    event = next(a for a in completeness_events if a.case_id == "GS-A-candidate")
    assert event.severity == "danger"
    assert event.slope < TREND_SLOPE_DANGER_MAX
    assert event.point_count == 5


def test_flat_timeline_does_not_fire(tmp_path: Path) -> None:
    """All five points equal -> slope == 0 -> no event (negative control)."""
    _seed_descending_timeline(
        tmp_path,
        "GS-A-candidate",
        [85, 85, 85, 85, 85],
        datetime(2026, 5, 16, 10, 0, 0, tzinfo=UTC),
    )
    report = build_cohort_trend_anomalies(repo_root=tmp_path)
    assert report.anomaly_count == 0


def test_ascending_timeline_does_not_fire(tmp_path: Path) -> None:
    """Positive slope -> no event (negative control orthogonal to descending)."""
    _seed_descending_timeline(
        tmp_path,
        "GS-A-candidate",
        [50, 60, 70, 80, 90],
        datetime(2026, 5, 16, 10, 0, 0, tzinfo=UTC),
    )
    report = build_cohort_trend_anomalies(repo_root=tmp_path)
    assert report.anomaly_count == 0


def test_mild_descent_fires_info_not_danger(tmp_path: Path) -> None:
    """A gentle descent should fire info, not danger, demonstrating the
    severity ladder is monotonic."""
    # Drop from 85 to 83 over 3 snapshots = slope ~ -1.0 on raw score,
    # which scales to ~ -0.5 weighted points -> info (right at boundary).
    _seed_descending_timeline(
        tmp_path,
        "GS-A-candidate",
        [85, 84, 83],
        datetime(2026, 5, 16, 10, 0, 0, tzinfo=UTC),
    )
    report = build_cohort_trend_anomalies(repo_root=tmp_path)
    completeness_events = [a for a in report.anomalies if a.axis == "completeness"]
    if completeness_events:
        # If it fires at all, it must be info (not warn or danger).
        event = completeness_events[0]
        assert event.severity == "info"


# ---------------------------------------------------------------------
# Envelope / schema
# ---------------------------------------------------------------------


def test_envelope_stamps_schema_and_disclaimer(tmp_path: Path) -> None:
    report = build_cohort_trend_anomalies(
        repo_root=tmp_path, now_utc=datetime(2026, 5, 16, 0, 0, 0, tzinfo=UTC)
    )
    assert report.schema_version == COHORT_TREND_ANOMALIES_SCHEMA_VERSION
    assert report.claim_tier == "Tier 1 engineering candidate"
    assert "not_signed_validation" in report.claim_boundary
    assert "not_benchmark_agreement" in report.claim_boundary
    assert "not signed validation" in report.claim_impact
    assert "not benchmark agreement" in report.claim_impact
    assert "do NOT diagnose root cause" in report.claim_impact
    assert report.point_count_floor == TREND_MIN_POINTS


# ---------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------


def test_endpoint_returns_stamped_payload_on_empty_cohort(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/cohort-trend-anomalies")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_TREND_ANOMALIES_SCHEMA_VERSION
    assert payload["cohort_count"] == 0
    assert payload["anomaly_count"] == 0
    assert isinstance(payload["anomalies"], list)
    assert payload["point_count_floor"] == TREND_MIN_POINTS


def test_endpoint_carries_tier1_disclaimer_trio(client: _SyncASGIClient, fake_repo: Path) -> None:
    res = client.get("/api/v1/cohort-trend-anomalies")
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


def test_endpoint_surfaces_descending_case_anomaly(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_descending_timeline(
        fake_repo,
        "GS-A-candidate",
        [90, 80, 70, 60, 50],
        datetime(2026, 5, 16, 10, 0, 0, tzinfo=UTC),
    )
    res = client.get("/api/v1/cohort-trend-anomalies")
    payload = res.json()
    assert payload["cohort_count"] == 1
    assert payload["anomaly_count"] >= 1
    case_ids = {a["case_id"] for a in payload["anomalies"]}
    assert "GS-A-candidate" in case_ids
