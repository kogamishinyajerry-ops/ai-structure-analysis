"""V2-0 residual floor — every committed cross-check verdict must hold its gate.

ADR-027 §D2 G-1(ii) names the invariant: "the [cohort] cross_check_verdict.yaml
residuals stay within their declared tolerances" — and §D3 V2-0 orders it wired
into CI: "On every PR, assert the … committed cross_check_verdict.yaml residuals
against their declared tolerances."  Until this file existed the invariant was
documentation-only (no CI job read the verdicts); the companion half of V2-0,
the live re-solve of one representative case under real ccx, is the separate
``real-le10-e2e`` job (backend/tests/test_workflow_real_le10.py).

This test is the pure, ccx-free floor.  It lives in root ``tests/`` ON PURPOSE:
the required ``lint-and-test`` CI job runs ``pytest tests/`` on every PR, so the
floor gates main without new dependencies or solver installs.

Per verdict file (discovered by glob — never a hand-maintained list, so new
cases are admitted automatically) it asserts:

1. the recorded ``residual_pct`` is reproducible from the file's own
   observed/analytical values via the magnitude formula
   ``(|observed| - |analytical|) / |analytical| * 100`` — the one formula
   consistent across the whole cohort (plate-ss-shell records observed and
   analytical with OPPOSITE sign conventions; a naive signed formula flips
   sign on cantilever-beam / plate-simply-supported and explodes on the shell
   case);
2. ``|residual_pct| <= tolerance_pct`` (the floor itself);
3. ``verdict == "PASS"`` — a committed FAIL verdict must block, loudly;
4. the case is registered in the claim-tier SSOT
   (``app.services.reporting._claim_tier``) and carries ``tier_2_validated``
   there.  Tier is read from the registry ONLY — verdict-file prose like
   ``claim_tier`` / ``claim_boundary`` is deliberately not asserted (the
   hertz-contact file honestly carries a *boundary* of
   ``tier1_engineering_candidate`` while the registry overlay promotes it).

Cohort level: the globbed verdict set and the registry's tier_2_validated set
must match exactly (an admission gate in both directions: a verdict file
without a registry entry, or a tier-2 registry entry without a verdict file,
both fail) and may never shrink below the V2-0-era floor of 14
(13 analytical cross-checks + the NAFEMS LE10 public-benchmark agreement).

Honesty note: passing this floor means the *committed evidence* is internally
consistent and within tolerance.  It is NOT signed validation (ADR-027 G-2)
and it does not re-run any solver.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml
from app.services.reporting._claim_tier import CLAIM_TIER_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[1]

# Recompute-vs-recorded agreement: verdict files round residual_pct as coarsely
# as 3 decimals (hertz-contact records -6.823 vs a recomputed -6.82342…), so
# the comparison tolerance must absorb that rounding.  0.05 pct-points matches
# the precedent in backend/tests for the LE10 recompute.
RESIDUAL_RECOMPUTE_ABS_PCT = 0.05

# Lower bound on the validated cohort (regression floor, ADR-027 G-1).  The
# exact membership is asserted against the registry, not this number; the
# number only stops silent shrinkage below the V2-0-era cohort.
MIN_VALIDATED_COHORT = 14


def _verdict_paths() -> list[Path]:
    return sorted(REPO_ROOT.glob("golden_samples/*-candidate/cross_check_verdict.yaml"))


def _load(path: Path) -> dict:
    """Verdict files are JSON-formatted or YAML (hertz-contact); try JSON first."""
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        loaded = yaml.safe_load(text)
        assert isinstance(loaded, dict), f"{path} did not parse to a mapping"
        return loaded


def _scalar(payload: dict, key: str):
    """Top-level first, then the nested ``verdict_outcome`` block (hertz)."""
    if key in payload:
        return payload[key]
    nested = payload.get("verdict_outcome")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return None


def _observed_analytical_pair(payload: dict, case_id: str) -> tuple[float, float]:
    """Extract the (observed, analytical) pair the residual was computed from.

    Flat schema: numeric top-level ``observed_<suffix>`` paired with
    ``analytical_<suffix>`` by suffix (cantilever-dynamic also records an
    unpaired ``analytical_f1_hz`` — suffix pairing skips it).  Nested schema
    (hertz-contact): ``observed.indentation_m`` vs
    ``analytical_reference.indentation_m``.
    """
    observed = {
        k[len("observed_") :]: v
        for k, v in payload.items()
        if k.startswith("observed_") and isinstance(v, (int, float))
    }
    analytical = {
        k[len("analytical_") :]: v
        for k, v in payload.items()
        if k.startswith("analytical_") and isinstance(v, (int, float))
    }
    paired = sorted(set(observed) & set(analytical))
    if paired:
        assert len(paired) == 1, (
            f"{case_id}: ambiguous observed/analytical suffix pairs {paired}; "
            "extend the extractor deliberately instead of guessing"
        )
        suffix = paired[0]
        return float(observed[suffix]), float(analytical[suffix])

    # Nested (hertz-contact) shape.
    obs_block = payload.get("observed")
    ana_block = payload.get("analytical_reference")
    if isinstance(obs_block, dict) and isinstance(ana_block, dict):
        shared = sorted(
            k
            for k in set(obs_block) & set(ana_block)
            if isinstance(obs_block[k], (int, float)) and isinstance(ana_block[k], (int, float))
        )
        assert len(shared) == 1, (
            f"{case_id}: nested observed/analytical_reference share keys {shared}"
        )
        return float(obs_block[shared[0]]), float(ana_block[shared[0]])

    pytest.fail(f"{case_id}: no observed/analytical pair found in verdict schema")


_PATHS = _verdict_paths()


def test_verdict_census_is_nonempty_and_at_floor() -> None:
    assert len(_PATHS) >= MIN_VALIDATED_COHORT, (
        f"validated cohort shrank: {len(_PATHS)} verdict files < floor "
        f"{MIN_VALIDATED_COHORT} (ADR-027 G-1 regression floor)"
    )


def test_verdict_set_matches_registry_tier2_set() -> None:
    """Admission gate, both directions (mirrors the Phase-29D cohort pin)."""
    globbed = {p.parent.name for p in _PATHS}
    registry_tier2 = {
        case for case, tier in CLAIM_TIER_REGISTRY.items() if tier == "tier_2_validated"
    }
    missing_registry = sorted(globbed - registry_tier2)
    missing_verdict = sorted(registry_tier2 - globbed)
    assert not missing_registry, (
        f"verdict files without a tier_2_validated registry entry: {missing_registry}"
    )
    assert not missing_verdict, (
        f"tier_2_validated registry entries without a verdict file: {missing_verdict}"
    )


@pytest.mark.parametrize("path", _PATHS, ids=lambda p: p.parent.name)
def test_residual_floor(path: Path) -> None:
    case_id = path.parent.name
    payload = _load(path)

    verdict = _scalar(payload, "verdict")
    residual = _scalar(payload, "residual_pct")
    tolerance = _scalar(payload, "tolerance_pct")
    assert verdict == "PASS", f"{case_id}: committed verdict is {verdict!r}, not PASS"
    assert isinstance(residual, (int, float)), f"{case_id}: residual_pct missing"
    assert isinstance(tolerance, (int, float)) and tolerance > 0, (
        f"{case_id}: tolerance_pct missing or non-positive"
    )

    # (2) the floor itself.
    assert abs(residual) <= tolerance, (
        f"{case_id}: |residual| {abs(residual):.4f}% exceeds declared tolerance {tolerance}%"
    )

    # (1) recorded residual is reproducible from the file's own values.
    observed, analytical = _observed_analytical_pair(payload, case_id)
    assert analytical != 0 and math.isfinite(observed) and math.isfinite(analytical)
    recomputed = (abs(observed) - abs(analytical)) / abs(analytical) * 100.0
    assert recomputed == pytest.approx(residual, abs=RESIDUAL_RECOMPUTE_ABS_PCT), (
        f"{case_id}: recorded residual_pct {residual} not reproducible from "
        f"observed={observed} analytical={analytical} (recomputed {recomputed:.4f})"
    )

    # (4) tier comes from the registry SSOT only.
    assert CLAIM_TIER_REGISTRY.get(case_id) == "tier_2_validated", (
        f"{case_id}: has a committed verdict but is not tier_2_validated in the claim-tier registry"
    )
