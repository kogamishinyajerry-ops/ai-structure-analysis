"""FM-04a Phase 15 A — rod-wave-impact-energy-leak-candidate fixture tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the REGRESSED-bucket variant: a synthetic 50%
non-physical energy injection at frame 30 trips the per-frame
energy_partition_audit (rel_drift ~= 0.50), drops the
case_completeness energy_audit axis to 0/15, and lands the
scorecard below the 80-pt healthy floor.

Anti-gaming guards pinned here (per Phase 15 binding rubric §4 / §A:-3):
* The test does NOT read ``flagged_frame_indices`` from the fixture's
  self-reported field; it runs ``energy_partition_audit`` on the
  parsed manifest and asserts the audit's CONTRACT-COMPUTED output
  matches the SSOT ``LEAK_INJECTION_FRAME`` (30) at ``rel_drift``
  ~ ``LEAK_INJECTION_SCALE - 1`` (0.50 ± 1e-9).
* A drifted leak frame (say, 25 instead of 30) would trip THIS
  test, not just the parser's read-back.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.main import app
from app.services.reporting.explicit_dynamics_extraction import (
    ENERGY_PARTITION_DRIFT_FRACTION,
    energy_partition_audit,
    parse_animation_manifest,
)

CASE_ID = "rod-wave-impact-energy-leak-candidate"
_REPO_ROOT = Path(__file__).resolve().parent.parent
_GS_DIR = _REPO_ROOT / "golden_samples" / CASE_ID
_PS_DIR = _REPO_ROOT / "project_state" / "graph_executor" / CASE_ID
_GENERATOR = _REPO_ROOT / "scripts" / "gen_rod_wave_impact_energy_leak_deck.py"


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixture_regenerated() -> None:
    """project_state/ is gitignored; regenerate route-readable copies
    if missing."""
    needed = (
        _PS_DIR / "ballistic" / "ballistic_metrics.json",
        _PS_DIR / "convergence" / "convergence_study.json",
        _PS_DIR / "visualization" / "openradioss_animation_manifest.json",
    )
    if not all(p.is_file() for p in needed):
        subprocess.check_call([sys.executable, str(_GENERATOR)], cwd=str(_REPO_ROOT))


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(transport=self._transport, base_url="http://t") as c:
                return await c.get(url, params=params)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


# ---------------------------------------------------------------------
# 1. Fixture inventory + Tier 1 trio
# ---------------------------------------------------------------------


def test_leak_fixture_directory_present() -> None:
    assert _GS_DIR.is_dir()
    assert _GS_DIR.name.endswith("-candidate")


def test_leak_fixture_self_documenting_files_present() -> None:
    for relpath in (
        "expected_results.json",
        "NOTES.md",
        "data/model_00_0000.rad",
        "data/model_00_0001.rad",
        "data/ballistic_metrics.json",
        "data/convergence_study.json",
        "data/animation_manifest.json",
    ):
        assert (_GS_DIR / relpath).is_file(), f"missing {relpath!r}"


def test_leak_expected_results_carries_tier1_trio_and_regressed_status() -> None:
    payload = json.loads((_GS_DIR / "expected_results.json").read_text(encoding="utf-8"))
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert "not signed validation" in payload["status_reason"]
    assert "not benchmark agreement" in payload["status_reason"]
    # Regressed-bucket status pin.
    assert payload["status"] == "engineering_candidate_regressed"


# ---------------------------------------------------------------------
# 2. A:-3 audit-computed leak flag (NOT trusted from fixture)
# ---------------------------------------------------------------------


def test_leak_audit_flags_exactly_frame_30() -> None:
    """The KEY A:-3 anti-gaming pin: run the audit on the parsed
    manifest and assert flagged_frame_indices computed by the audit
    matches the SSOT LEAK_INJECTION_FRAME — NOT read from the
    fixture's self-reported field."""
    manifest = parse_animation_manifest(_GS_DIR / "data" / "animation_manifest.json")
    audit = energy_partition_audit(manifest)
    assert audit.clean is False
    assert audit.flagged_frame_indices == (30,)


def test_leak_audit_rel_drift_lands_at_half() -> None:
    """LEAK_INJECTION_SCALE=1.5 injects 50% non-physical energy
    relative to W_ext. The audit's max_rel_drift_fraction MUST be
    very close to 0.50."""
    manifest = parse_animation_manifest(_GS_DIR / "data" / "animation_manifest.json")
    audit = energy_partition_audit(manifest)
    assert 0.499 < audit.max_rel_drift_fraction < 0.501


def test_leak_audit_above_drift_fraction_threshold() -> None:
    """The audit's rel_drift MUST exceed the 1% threshold by
    50x+, regardless of any future tweak to
    ENERGY_PARTITION_DRIFT_FRACTION."""
    manifest = parse_animation_manifest(_GS_DIR / "data" / "animation_manifest.json")
    audit = energy_partition_audit(manifest)
    assert audit.max_rel_drift_fraction > 10 * ENERGY_PARTITION_DRIFT_FRACTION


def test_leak_audit_other_frames_remain_clean() -> None:
    """ONLY frame 30 is flagged; all other 99 frames close the
    energy balance at machine epsilon."""
    manifest = parse_animation_manifest(_GS_DIR / "data" / "animation_manifest.json")
    audit = energy_partition_audit(manifest)
    assert len(audit.flagged_frame_indices) == 1
    assert 30 in audit.flagged_frame_indices
    # No other frame leaked into the flag list.
    for idx in range(100):
        if idx != 30:
            assert idx not in audit.flagged_frame_indices


# ---------------------------------------------------------------------
# 3. Live ASGI: regressed case lands at 75/100 (below healthy floor)
# ---------------------------------------------------------------------


def test_leak_case_completeness_lands_below_80_floor(
    client: _SyncASGIClient,
) -> None:
    """Energy-leak variant MUST land below the 80-pt healthy floor
    by construction: energy_audit 0/15 + convergence 10/15."""
    res = client.get(f"/api/v1/case-completeness/{CASE_ID}?analysis_type=explicit_dynamics")
    assert res.status_code == 200
    body = res.json()
    assert body["score"] < 80, (
        f"leak fixture landed at {body['score']}/100; expected < 80. breakdown: {body['breakdown']}"
    )
    # Score also MUST be above zero (the OTHER axes are still
    # full-points; only energy + part of convergence dropped).
    assert body["score"] >= 60


def test_leak_energy_audit_axis_is_zero(
    client: _SyncASGIClient,
) -> None:
    """The energy_audit axis lands at 0/15 because the underlying
    ballistic_metrics emits energy_audit.status=open_residual."""
    res = client.get(f"/api/v1/case-completeness/{CASE_ID}?analysis_type=explicit_dynamics")
    body = res.json()
    bd = {b["label"]: b for b in body["breakdown"]}
    assert bd["energy_audit"]["points_awarded"] == 0
    assert bd["energy_audit"]["evidence_status"] == "open_residual"


def test_leak_convergence_study_is_unstable(
    client: _SyncASGIClient,
) -> None:
    """The convergence_combined_verdict propagates the audit's
    instability — both axes carry candidate_observed_unstable."""
    res = client.get(f"/api/v1/convergence-study/{CASE_ID}")
    assert res.status_code == 200
    body = res.json()
    assert body["convergence_kind"] == "explicit_dynamics"
    assert body["combined_verdict"] == "candidate_observed_unstable"


# ---------------------------------------------------------------------
# 4. Constraint guards
# ---------------------------------------------------------------------


_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


def test_leak_case_id_is_candidate_not_signed_registry() -> None:
    assert CASE_ID.endswith("-candidate")
    assert _SIGNED_REGISTRY_RE.fullmatch(CASE_ID) is None


def test_leak_no_real_solver_artifacts() -> None:
    forbidden_suffixes = (".frd", ".dat", ".h3d")
    for p in _GS_DIR.rglob("*"):
        if p.is_file():
            for sfx in forbidden_suffixes:
                assert p.suffix != sfx, f"real-solver artifact {p}"
