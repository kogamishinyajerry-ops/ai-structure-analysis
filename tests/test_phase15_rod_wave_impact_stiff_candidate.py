"""FM-04a Phase 15 A — rod-wave-impact-stiff-candidate fixture tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the STIFF variant (E=210 GPa tool steel) of the Phase 14 D
rod-wave-impact-candidate. The stiff variant is HEALTHY by construction:
case_completeness lands at 95/100; the analytical 1D-bar cross-check
matches observed first-reflection within ~1.71% (well below the 5%
WAVE_CROSS_CHECK_TOLERANCE_PCT band).

Anti-gaming guards pinned here (per Phase 15 binding rubric §4 / §A:-3):
* The test RE-DERIVES the analytical wave speed + first-reflection time
  from the fixture's self-reported material constants (NOT trusting
  the ``observed_first_reflection_s`` field) and asserts the
  observed-vs-analytical residual within WAVE_CROSS_CHECK_TOLERANCE_PCT.
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
    WAVE_CROSS_CHECK_TOLERANCE_PCT,
    bar_wave_first_reflection_s,
    bar_wave_speed_m_per_s,
    energy_partition_audit,
    parse_animation_manifest,
    wave_propagation_residuals,
)

CASE_ID = "rod-wave-impact-stiff-candidate"
_REPO_ROOT = Path(__file__).resolve().parent.parent
_GS_DIR = _REPO_ROOT / "golden_samples" / CASE_ID
_PS_DIR = _REPO_ROOT / "project_state" / "graph_executor" / CASE_ID


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixture_regenerated() -> None:
    """project_state/ is gitignored; regenerate route-readable copies
    if missing. Mirrors the Phase 14 D regenerator pattern."""
    needed = (
        _PS_DIR / "ballistic" / "ballistic_metrics.json",
        _PS_DIR / "convergence" / "convergence_study.json",
        _PS_DIR / "visualization" / "openradioss_animation_manifest.json",
    )
    if not all(p.is_file() for p in needed):
        subprocess.check_call(
            [
                sys.executable,
                str(_REPO_ROOT / "scripts" / "gen_rod_wave_impact_stiff_deck.py"),
            ],
            cwd=str(_REPO_ROOT),
        )


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


def test_stiff_fixture_directory_present() -> None:
    assert _GS_DIR.is_dir()
    assert _GS_DIR.name.endswith("-candidate")


def test_stiff_fixture_self_documenting_files_present() -> None:
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


def test_stiff_expected_results_carries_tier1_disclaimer_trio() -> None:
    payload = json.loads((_GS_DIR / "expected_results.json").read_text(encoding="utf-8"))
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert "not signed validation" in payload["status_reason"]
    assert "not benchmark agreement" in payload["status_reason"]


# ---------------------------------------------------------------------
# 2. Analytical cross-check (A:-3 defense-in-depth)
# ---------------------------------------------------------------------


def test_stiff_uses_tool_steel_constants() -> None:
    """STIFF variant MUST use E=210 GPa (not the canonical 200)."""
    metrics = json.loads((_GS_DIR / "data" / "ballistic_metrics.json").read_text(encoding="utf-8"))
    summary = metrics["explicit_dynamics_summary"]
    assert summary["E_Pa"] == 210e9
    assert summary["rho_kg_per_m3"] == 7850.0
    assert summary["rod_length_m"] == 1.0


def test_stiff_analytical_first_reflection_re_derived() -> None:
    """Re-derive analytical from material constants; assert observed
    within 5% tolerance band."""
    metrics = json.loads((_GS_DIR / "data" / "ballistic_metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (_GS_DIR / "data" / "animation_manifest.json").read_text(encoding="utf-8")
    )
    summary = metrics["explicit_dynamics_summary"]
    c = bar_wave_speed_m_per_s(summary["E_Pa"], summary["rho_kg_per_m3"])
    analytical = bar_wave_first_reflection_s(summary["rod_length_m"], c)
    frame_idx = int(manifest["first_reflection_frame_index"])
    frame_dt = float(manifest["frame_dt_s"])
    observed = frame_idx * frame_dt
    res = wave_propagation_residuals(observed, analytical)
    assert res.within_tolerance is True, (
        f"observed {observed * 1e6:.2f}us deviates "
        f"{res.residual_pct:.2f}% from analytical "
        f"{analytical * 1e6:.2f}us (tol {WAVE_CROSS_CHECK_TOLERANCE_PCT}%)"
    )
    # Stiff variant lands at ~1.71% — pin within a tight band so a
    # drifted fixture trips this test.
    assert 1.0 < res.residual_pct < 3.0


def test_stiff_wave_speed_is_faster_than_canonical() -> None:
    """Sanity: stiffer rod (higher E) -> faster wave speed."""
    canonical_c = bar_wave_speed_m_per_s(200e9, 7850.0)
    stiff_c = bar_wave_speed_m_per_s(210e9, 7850.0)
    assert stiff_c > canonical_c
    # delta ~= +2.5%
    delta_pct = (stiff_c - canonical_c) / canonical_c * 100
    assert 2.0 < delta_pct < 3.0


def test_stiff_energy_partition_audit_clean() -> None:
    """Hopkinson-style closed energy balance preserved across all
    100 frames for the healthy stiff variant."""
    manifest = parse_animation_manifest(_GS_DIR / "data" / "animation_manifest.json")
    audit = energy_partition_audit(manifest)
    assert audit.clean is True
    assert audit.flagged_frame_indices == ()


# ---------------------------------------------------------------------
# 3. Live ASGI: stiff variant lands HEALTHY 95/100
# ---------------------------------------------------------------------


def test_stiff_case_completeness_lands_at_95_healthy(
    client: _SyncASGIClient,
) -> None:
    res = client.get(f"/api/v1/case-completeness/{CASE_ID}?analysis_type=explicit_dynamics")
    assert res.status_code == 200
    body = res.json()
    assert body["score"] == 95, (
        f"stiff fixture landed at {body['score']}/100; expected 95. breakdown: {body['breakdown']}"
    )
    assert body["claim_tier"] == "Tier 1 engineering candidate"


def test_stiff_convergence_study_is_stable(
    client: _SyncASGIClient,
) -> None:
    """Stiff variant convergence verdict is candidate_observed_stable
    on both axes (mesh + dt) — the higher E does not break stability."""
    res = client.get(f"/api/v1/convergence-study/{CASE_ID}")
    assert res.status_code == 200
    body = res.json()
    assert body["convergence_kind"] == "explicit_dynamics"
    assert body["combined_verdict"] == "candidate_observed_stable"


# ---------------------------------------------------------------------
# 4. Constraint guards (HF1 carve-out posture)
# ---------------------------------------------------------------------


_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


def test_stiff_case_id_is_candidate_not_signed_registry() -> None:
    assert CASE_ID.endswith("-candidate")
    assert _SIGNED_REGISTRY_RE.fullmatch(CASE_ID) is None


def test_stiff_no_real_solver_artifacts() -> None:
    forbidden_suffixes = (".frd", ".dat", ".h3d")
    for p in _GS_DIR.rglob("*"):
        if p.is_file():
            for sfx in forbidden_suffixes:
                assert p.suffix != sfx, f"real-solver artifact {p}"
