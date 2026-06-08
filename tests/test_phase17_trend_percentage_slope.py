"""FM-04a Phase 17 C — per-axis percentage_delta_slope on cohort-trend-anomalies.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the additive ``percentage_delta_slope`` field on every
``TrendEvent`` (MINOR bump ``COHORT_TREND_ANOMALIES_SCHEMA_VERSION``
1.0.0 → 1.1.0). The new field normalizes the raw weighted-axis-point
slope to ``percent of axis ceiling per snapshot`` so reviewer
comparisons across axes (completeness=50 vs energy_audit=15) are
weight-neutral.

Anti-gaming guards pinned here (per Phase 17 binding rubric §3.C):
* **M:-1** — schema MINOR bump 1.0.0 → 1.1.0 with bump-history
  docstring citing Phase 17 C + the additive field.
* **M:-2** — ``_percentage_delta_slope`` IMPORTS ``TRUST_AXIS_WEIGHTS``
  from the Phase 15 C SSOT (``trust_score_drift_attribution``); NO
  inline weight constants. ``ast`` audit on the source file forbids
  inline-numeric weight literals.
* **T:-3** — boundary pins for the worked example in the methodology
  doc: completeness 50→42→34 (raw slope -8.0 weighted-pts/snap,
  percentage slope -16.0 %/snap exactly); energy_audit 15→10→5 (raw
  slope -5.0 weighted-pts/snap, percentage slope -33.333333 %/snap to
  6 decimals).
* **T:-4** — sign convention: positive raw slope (recovery) →
  positive percentage_delta_slope; negative raw slope (regression) →
  negative percentage_delta_slope. Flat → 0.0. No sign-flip artifacts.
* **T:-5** — axis-coverage pin: ``_percentage_delta_slope`` produces
  coherent normalized values for all 4 TREND_AXES; an unknown axis
  raises ``KeyError`` (defended by A:-2).
* **A:-2** — defensive: ``_percentage_delta_slope`` raises ``KeyError``
  on an unknown axis label (e.g., the placeholder "stiffness" name).
* **C:-1** — Tier 1 disclaimer trio preserved on the
  cohort-trend-anomalies envelope at 1.1.0 (live ASGI).
* **C:-8** — forbidden-positive-claim grep absent from the methodology
  doc (SSOT 9-tuple) outside ``not <claim>`` / ``no <claim>`` form.
* **V:-3** — all snapshot writes under tmp_path; the real
  ``reports/snapshots/`` tree is never touched.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import json
import re
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
    TREND_AXES,
    TrendEvent,
    _percentage_delta_slope,
    build_cohort_trend_anomalies,
    render_cohort_trend_anomalies_json,
)
from app.services.reporting.trust_score_drift_attribution import (
    TRUST_AXIS_WEIGHTS,
)

from tests._test_utils import (
    FORBIDDEN_POSITIVE_CLAIM_TOKENS_9,
    assert_no_forbidden_positive_claims,
    assert_tier1_trio,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"

SNAP_LABELS = (
    "2026-05-17T100000Z",
    "2026-05-17T120000Z",
    "2026-05-17T140000Z",
)


# ---------------------------------------------------------------------
# Sync ASGI client (local to this file — Phase 17 D consolidates)
# ---------------------------------------------------------------------


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


# ---------------------------------------------------------------------
# Snapshot seed helpers (tmp_path only; V:-3 pin)
# ---------------------------------------------------------------------


def _seed_axis_snapshot(
    root: Path,
    case_id: str,
    *,
    snapshot_label: str,
    completeness: int,
    convergence: int,
    energy_audit: int,
    reproducibility: int,
) -> None:
    """Seed a candidate case with one snapshot and override all 4
    per-axis scores on disk. Mirrors the Phase 9 D seed pattern but
    extended to all 4 axes for T:-5 coverage."""
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
        json.dumps({"case_id": case_id, "claim_boundary": "tier1"}),
        encoding="utf-8",
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

    snap_root = root / "reports" / "snapshots" / snapshot_label
    for axis_label, score in (
        ("completeness", completeness),
        ("convergence", convergence),
        ("energy_audit", energy_audit),
        ("reproducibility", reproducibility),
    ):
        axis_path = snap_root / axis_label / f"{case_id}.json"
        if not axis_path.exists():
            axis_path.parent.mkdir(parents=True, exist_ok=True)
            axis_path.write_text(
                json.dumps({"case_id": case_id, "score": score}, sort_keys=True),
                encoding="utf-8",
            )
            continue
        payload = json.loads(axis_path.read_text(encoding="utf-8"))
        payload["score"] = score
        axis_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------
# M:-1 schema version pin
# ---------------------------------------------------------------------


def test_cohort_trend_anomalies_schema_at_1_1_0() -> None:
    """Phase 17 C MINOR bump 1.0.0 → 1.1.0 with bump-history docstring."""
    assert COHORT_TREND_ANOMALIES_SCHEMA_VERSION == "1.1.0"


def test_schema_versions_module_carries_phase17c_bump_history() -> None:
    """The SSOT docstring must cite Phase 17 C and explain the
    ``percentage_delta_slope`` additive field."""
    src = (
        REPO_ROOT / "backend" / "app" / "services" / "reporting" / "_schema_versions.py"
    ).read_text(encoding="utf-8")
    assert "Phase 17 C" in src
    assert "percentage_delta_slope" in src
    assert "1.1.0" in src
    # bump-history block must be in the COHORT_TREND_ANOMALIES_SCHEMA_VERSION docstring
    block_marker = "COHORT_TREND_ANOMALIES_SCHEMA_VERSION"
    block_start = src.index(block_marker)
    # Find the assignment + docstring (terminates at the closing `"""`
    # of the docstring; the docstring opens immediately after the
    # constant assignment on the next line).
    docstring_open = src.index('"""', block_start)
    docstring_close = src.index('"""', docstring_open + 3) + 3
    block = src[block_start:docstring_close]
    assert "Phase 17 C" in block, block[:600]
    assert "Bump history" in block, block[:600]
    assert "percentage_delta_slope" in block, block[:600]


# ---------------------------------------------------------------------
# M:-2 anti-gaming: SSOT import (no inline weight constants)
# ---------------------------------------------------------------------


def test_percentage_delta_slope_imports_trust_axis_weights_ssot() -> None:
    """The helper must IMPORT ``TRUST_AXIS_WEIGHTS``, not redefine it.

    AST audit: inspect the helper's function body (NOT the docstring,
    which may legitimately mention "Phase 15 C" etc) and forbid any
    literal integer constant equal to one of the four canonical axis
    weights (50, 20, 15). The helper must read weights from
    TRUST_AXIS_WEIGHTS at runtime.
    """
    src = inspect.getsource(_percentage_delta_slope)
    assert "TRUST_AXIS_WEIGHTS" in src, src

    func_def = ast.parse(src).body[0]
    assert isinstance(func_def, ast.FunctionDef)
    forbidden_weight_literals = {50, 20, 15}
    statements = (
        func_def.body[1:]
        if isinstance(func_def.body[0], ast.Expr)
        and isinstance(func_def.body[0].value, ast.Constant)
        and isinstance(func_def.body[0].value.value, str)
        else func_def.body
    )
    for node in ast.walk(ast.Module(body=statements, type_ignores=[])):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            assert node.value not in forbidden_weight_literals, (
                f"helper body unexpectedly contains literal weight {node.value} "
                f"(would shadow TRUST_AXIS_WEIGHTS SSOT)"
            )


def test_cohort_trend_anomalies_module_imports_trust_axis_weights() -> None:
    """The module-level import line for TRUST_AXIS_WEIGHTS must be
    present (AST audit, not text grep — back-doors via local imports
    inside the helper would still be flagged below)."""
    src = (
        REPO_ROOT / "backend" / "app" / "services" / "reporting" / "cohort_trend_anomalies.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (
            node.module and node.module.endswith("trust_score_drift_attribution")
        ):
            names = {alias.name for alias in node.names}
            if "TRUST_AXIS_WEIGHTS" in names:
                found = True
                break
    assert found, (
        "expected module-level `from .trust_score_drift_attribution import TRUST_AXIS_WEIGHTS`"
    )


def test_cohort_trend_anomalies_module_does_not_inline_axis_weights() -> None:
    """The module source must NOT re-declare any of the 4 axis weights
    (anti-gaming guard against a future maintainer inlining a stale copy)."""
    src = (
        REPO_ROOT / "backend" / "app" / "services" / "reporting" / "cohort_trend_anomalies.py"
    ).read_text(encoding="utf-8")
    # Match a top-level constant assignment like `COMPLETENESS_WEIGHT = 50`
    forbidden_patterns = (
        re.compile(r"^\s*COMPLETENESS_WEIGHT\s*=", re.MULTILINE),
        re.compile(r"^\s*CONVERGENCE_WEIGHT\s*=", re.MULTILINE),
        re.compile(r"^\s*ENERGY_AUDIT_WEIGHT\s*=", re.MULTILINE),
        re.compile(r"^\s*REPRODUCIBILITY_WEIGHT\s*=", re.MULTILINE),
        re.compile(r"^\s*TRUST_AXIS_WEIGHTS\s*=", re.MULTILINE),
    )
    for pat in forbidden_patterns:
        assert pat.search(src) is None, (
            f"cohort_trend_anomalies.py unexpectedly inlines a constant "
            f"matched by {pat.pattern!r}; weights must come from the "
            f"Phase 15 C SSOT"
        )


# ---------------------------------------------------------------------
# T:-3 worked-example boundary pins
# ---------------------------------------------------------------------


def test_completeness_5042_34_arc_lands_pct_slope_negative_16_0() -> None:
    raw_slope = -8.0
    pct = _percentage_delta_slope(raw_slope, "completeness")
    # 50-weight completeness: -8/50 * 100 = -16.0 exactly.
    assert pct == -16.0, pct


def test_energy_15_10_5_arc_lands_pct_slope_negative_33_333333() -> None:
    raw_slope = -5.0
    pct = _percentage_delta_slope(raw_slope, "energy_audit")
    # 15-weight energy_audit: -5/15 * 100 = -33.333333... → 6 decimals.
    assert pct == -33.333333, pct


def test_completeness_event_carries_expected_raw_and_pct_slope(
    fake_repo: Path,
) -> None:
    """Synthesize the worked-example arc end-to-end via
    ``build_cohort_trend_anomalies``.

    Note on seed values: the underlying timeline computes
    ``completeness_weighted = round(score / score_max * 100) * 50 / 100``
    so to land weighted points at 50/42/34 (the methodology doc's
    worked example), the on-disk score must be 100/84/68.
    """
    # Seed scores chosen so completeness_weighted lands at 50, 42, 34.
    completeness_scores = (100, 84, 68)
    for snap_label, score in zip(SNAP_LABELS, completeness_scores, strict=False):
        _seed_axis_snapshot(
            fake_repo,
            LEAK_CASE_ID,
            snapshot_label=snap_label,
            completeness=score,
            convergence=20,
            energy_audit=15,
            reproducibility=15,
        )

    report = build_cohort_trend_anomalies(
        repo_root=fake_repo, now_utc=datetime(2026, 5, 17, tzinfo=UTC)
    )
    events_by_axis = {e.axis: e for e in report.anomalies if e.case_id == LEAK_CASE_ID}
    assert "completeness" in events_by_axis, list(events_by_axis)

    comp_event = events_by_axis["completeness"]
    # Raw slope semantics preserved (Phase 9 D unchanged); weighted arc
    # 50 → 42 → 34 yields least-squares slope -8.0.
    assert comp_event.slope == pytest.approx(-8.0, abs=1e-6)
    # Phase 17 C additive field: -8.0 / 50 * 100 = -16.0 exactly.
    assert comp_event.percentage_delta_slope == -16.0


# ---------------------------------------------------------------------
# T:-4 sign convention (no sign-flip from normalization)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_slope, axis, expected_sign",
    [
        (-8.0, "completeness", -1),
        (-5.0, "energy_audit", -1),
        (-0.6, "convergence", -1),
        (8.0, "completeness", 1),
        (5.0, "energy_audit", 1),
        (0.0, "reproducibility", 0),
    ],
)
def test_percentage_delta_slope_preserves_sign(
    raw_slope: float, axis: str, expected_sign: int
) -> None:
    pct = _percentage_delta_slope(raw_slope, axis)
    if expected_sign == 0:
        assert pct == 0.0
    elif expected_sign > 0:
        assert pct > 0.0
    else:
        assert pct < 0.0


# ---------------------------------------------------------------------
# T:-5 axis-coverage pin
# ---------------------------------------------------------------------


def test_all_four_trend_axes_produce_coherent_percentage_values() -> None:
    """For each of the 4 TREND_AXES, the helper produces a real number
    matching the canonical TRUST_AXIS_WEIGHTS-based formula."""
    raw_slope = -1.5
    for axis in TREND_AXES:
        weight = TRUST_AXIS_WEIGHTS[axis]
        expected = round((raw_slope / weight) * 100.0, 6)
        actual = _percentage_delta_slope(raw_slope, axis)
        assert actual == expected, (axis, weight, expected, actual)


def test_trend_axes_tuple_matches_trust_axis_weights_keys() -> None:
    """The cohort-trend-anomalies axis tuple must be a subset of the
    SSOT axis-weights mapping (a future axis must land in BOTH)."""
    for axis in TREND_AXES:
        assert axis in TRUST_AXIS_WEIGHTS, axis


# ---------------------------------------------------------------------
# A:-2 defensive: unknown axis raises
# ---------------------------------------------------------------------


def test_unknown_axis_raises_key_error() -> None:
    with pytest.raises(KeyError) as excinfo:
        _percentage_delta_slope(-1.0, "stiffness")
    # KeyError repr includes the offending label.
    assert "stiffness" in str(excinfo.value)


def test_unknown_axis_error_lists_expected_axes() -> None:
    with pytest.raises(KeyError) as excinfo:
        _percentage_delta_slope(-1.0, "unknown_axis_label_xyz")
    msg = str(excinfo.value)
    for axis in TREND_AXES:
        assert axis in msg, (axis, msg)


# ---------------------------------------------------------------------
# C:-1 Tier 1 trio preserved on the envelope at 1.1.0
# ---------------------------------------------------------------------


def test_endpoint_envelope_carries_tier1_trio_at_1_1_0(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Live ASGI: GET /cohort-trend-anomalies at the new schema 1.1.0
    still carries the Tier 1 disclaimer trio (claim_tier /
    claim_boundary / claim_impact)."""
    res = client.get("/api/v1/cohort-trend-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["schema_version"] == "1.1.0", body
    assert_tier1_trio(body)


def test_endpoint_envelope_serializes_pct_slope_on_anomalies(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Live ASGI: GET /cohort-trend-anomalies with seeded arc carries
    the new ``percentage_delta_slope`` field on every anomaly."""
    completeness_scores = (100, 84, 68)
    for snap_label, score in zip(SNAP_LABELS, completeness_scores, strict=False):
        _seed_axis_snapshot(
            fake_repo,
            LEAK_CASE_ID,
            snapshot_label=snap_label,
            completeness=score,
            convergence=20,
            energy_audit=15,
            reproducibility=15,
        )

    res = client.get("/api/v1/cohort-trend-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["schema_version"] == "1.1.0"
    assert body["anomaly_count"] >= 1, body
    for anomaly in body["anomalies"]:
        assert "percentage_delta_slope" in anomaly, anomaly
        assert isinstance(anomaly["percentage_delta_slope"], (int, float)), anomaly
        # Sign must agree with raw slope.
        if anomaly["slope"] < 0:
            assert anomaly["percentage_delta_slope"] < 0.0, anomaly
        elif anomaly["slope"] > 0:
            assert anomaly["percentage_delta_slope"] > 0.0, anomaly


# ---------------------------------------------------------------------
# Round-trip + render audit
# ---------------------------------------------------------------------


def test_render_cohort_trend_anomalies_json_includes_pct_slope(
    fake_repo: Path,
) -> None:
    completeness_scores = (100, 84, 68)
    for snap_label, score in zip(SNAP_LABELS, completeness_scores, strict=False):
        _seed_axis_snapshot(
            fake_repo,
            LEAK_CASE_ID,
            snapshot_label=snap_label,
            completeness=score,
            convergence=20,
            energy_audit=15,
            reproducibility=15,
        )

    report = build_cohort_trend_anomalies(repo_root=fake_repo)
    rendered = render_cohort_trend_anomalies_json(report)
    payload = json.loads(rendered)
    assert payload["schema_version"] == "1.1.0"
    for anomaly in payload["anomalies"]:
        assert "percentage_delta_slope" in anomaly
        assert "slope" in anomaly
        # Both fields parallel (raw + normalized); raw preserved.
    # Round-trip stability: re-dump and re-parse equals original.
    re_rendered = json.dumps(payload, sort_keys=True)
    re_parsed = json.loads(re_rendered)
    assert re_parsed["anomalies"] == payload["anomalies"]


def test_trend_event_dataclass_carries_percentage_delta_slope_field() -> None:
    """``TrendEvent`` is frozen; constructing one with the new field
    succeeds; omitting it fails."""
    evt = TrendEvent(
        case_id="x-candidate",
        axis="energy_audit",
        slope=-5.0,
        point_count=3,
        severity="danger",
        percentage_delta_slope=-33.333333,
    )
    assert evt.percentage_delta_slope == -33.333333


def test_trend_event_construction_without_pct_slope_raises() -> None:
    with pytest.raises(TypeError):
        # Intentionally omit percentage_delta_slope; the dataclass is
        # required to enforce the new field via TypeError.
        TrendEvent(  # type: ignore[call-arg]
            case_id="x-candidate",
            axis="energy_audit",
            slope=-5.0,
            point_count=3,
            severity="danger",
        )


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep on methodology doc + test file
# ---------------------------------------------------------------------


def test_methodology_doc_carries_no_forbidden_positive_claims() -> None:
    """The new methodology doc must not contain any of the 9 forbidden
    positive-claim tokens outside ``not <claim>`` / ``no <claim>`` form."""
    methodology_path = REPO_ROOT / ".planning" / "methodology" / "cohort_trend_anomalies.md"
    assert methodology_path.exists(), methodology_path
    text = methodology_path.read_text(encoding="utf-8")
    assert_no_forbidden_positive_claims(text, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_9)


def test_methodology_doc_documents_cross_axis_comparison() -> None:
    """Per Phase 17 C blueprint, the methodology doc must explicitly
    explain why both raw and percentage slope views are surfaced."""
    text = (REPO_ROOT / ".planning" / "methodology" / "cohort_trend_anomalies.md").read_text(
        encoding="utf-8"
    )
    lowered = text.lower()
    assert "cross-axis" in lowered or "cross axis" in lowered
    assert "percentage_delta_slope" in text
    assert "raw" in lowered
    assert "phase 17 c" in lowered
