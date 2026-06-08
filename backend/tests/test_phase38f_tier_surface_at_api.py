"""FM-04a Phase 38 F — tier-2 promotion surfaces at the API boundary.

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
agreement. 绝对诚实客观.

Eval-fleet finding #1 (Phase 38 E audit): `candidate_cases.py` and
`cohort_overview.py` hard-coded "Tier 1 engineering candidate" for every case
and never called the `_claim_tier` SSOT, so every real-solver promotion
(`tier_2_validated`, earned by a PASS `cross_check_verdict.yaml`) was invisible
to the picker + cohort leaderboard — the whole tier-2 system was a dead letter
to users.

These tests pin the fix's invariant: **the endpoints surface exactly what the
`_claim_tier` SSOT resolves, per case** — never a blanket hard-coded tier. The
invariant is environment-robust (it compares endpoint output to the SSOT, not to
a frozen case count), plus one concrete check that a committed PASS verdict
(cylinder-pv) actually surfaces as Tier 2.

`candidate_cases.py` lives under `app.api.routes`; importing it normally would
trigger `app.api.__init__` → `nl.py` → `NLParser()` → a pre-existing
openai/httpx `proxies` crash under the conftest test key. We load it directly
via importlib (same pattern as `test_phase18e_materials_route.py`). The cohort
overview + `_claim_tier` live under `app.services` and import cleanly.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

from app.services.reporting._claim_tier import (
    claim_boundary_for,
    claim_tier_label_for,
    get_claim_tier,
)
from app.services.reporting.cohort_overview import (
    _overview_to_dict,
    build_cohort_overview,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN = REPO_ROOT / "golden_samples"

_TIER2_LABEL = "Tier 2 real-solver validated"
_TIER1_LABEL = "Tier 1 engineering candidate"


def _load_candidate_cases_module():
    """Load ``backend/app/api/routes/candidate_cases.py`` directly without
    triggering ``app.api.__init__`` (mirrors test_phase18e_materials_route)."""
    target = REPO_ROOT / "backend" / "app" / "api" / "routes" / "candidate_cases.py"
    spec = importlib.util.spec_from_file_location("phase38f_candidate_cases", target)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def picker_mod():
    return _load_candidate_cases_module()


def _picker_by_id(picker_mod) -> dict[str, dict[str, object]]:
    return {c["case_id"]: c for c in picker_mod._scan_candidate_cases(REPO_ROOT)}


def _cohort_by_id() -> dict[str, dict[str, object]]:
    overview = _overview_to_dict(build_cohort_overview(REPO_ROOT))
    return {e["case_id"]: e for e in overview["entries"]}


# --------------------------------------------------------------------------
# Core invariant: endpoint == _claim_tier SSOT, per case (env-robust)
# --------------------------------------------------------------------------


def test_picker_per_case_tier_matches_claim_tier_ssot(picker_mod) -> None:
    """Every picker row's claim_tier == claim_tier_label_for(case_id).

    This is the fix's contract: the picker resolves per-case tier from the
    SSOT, never a blanket hard-coded string. Robust to which cases exist.
    """
    picker = _picker_by_id(picker_mod)
    assert picker, "no candidate cases scanned — fixture/env problem"
    for case_id, row in picker.items():
        assert row["claim_tier"] == claim_tier_label_for(case_id), case_id
        assert row["claim_boundary"] == claim_boundary_for(case_id), case_id


def test_cohort_entries_per_case_tier_matches_claim_tier_ssot() -> None:
    """Every cohort entry's claim_tier == claim_tier_label_for(case_id)."""
    cohort = _cohort_by_id()
    assert cohort, "no cohort entries built — fixture/env problem"
    for case_id, entry in cohort.items():
        assert entry["claim_tier"] == claim_tier_label_for(case_id), case_id


def test_picker_and_cohort_agree_per_case(picker_mod) -> None:
    """The two endpoints never disagree on a shared case's tier (single SSOT)."""
    picker = _picker_by_id(picker_mod)
    cohort = _cohort_by_id()
    shared = set(picker) & set(cohort)
    assert shared, "picker and cohort share no cases — fixture/env problem"
    for case_id in shared:
        assert picker[case_id]["claim_tier"] == cohort[case_id]["claim_tier"], case_id


# --------------------------------------------------------------------------
# The fix actually surfaces a real promotion (not a blanket tier)
# --------------------------------------------------------------------------


def test_a_validated_case_surfaces_tier2_not_hardcoded_tier1(picker_mod) -> None:
    """A case with a committed PASS cross_check_verdict.yaml surfaces Tier 2.

    cylinder-pv-candidate is the canonical promoted case (Phase 18 A live ccx
    hoop-stress cross-check). If its verdict artifact is absent in this env,
    skip rather than fail (the invariant tests above still hold).
    """
    case_id = "cylinder-pv-candidate"
    verdict = GOLDEN / case_id / "cross_check_verdict.yaml"
    if get_claim_tier(case_id) != "tier_2_validated":
        pytest.skip(f"{case_id} not promoted in this env (verdict={verdict.exists()})")

    picker = _picker_by_id(picker_mod)
    assert case_id in picker, f"{case_id} missing from picker"
    assert picker[case_id]["claim_tier"] == _TIER2_LABEL
    # boundary must carry the real-solver substantiation, not the tier-1 copy
    assert "cross_check_against_analytical" in str(picker[case_id]["claim_boundary"])

    cohort = _cohort_by_id()
    assert cohort.get(case_id, {}).get("claim_tier") == _TIER2_LABEL


def test_not_every_case_is_the_same_tier(picker_mod) -> None:
    """Regression guard against re-introducing a blanket hard-coded tier.

    The whole bug was "every case is Tier 1". With committed verdicts the
    cohort is genuinely mixed; assert the picker mirrors the mixed SSOT IF the
    SSOT itself is mixed (skip on the degenerate all-tier-1 env).
    """
    picker = _picker_by_id(picker_mod)
    ssot_tiers = {claim_tier_label_for(cid) for cid in picker}
    if len(ssot_tiers) < 2:
        pytest.skip("SSOT resolves a single tier in this env (no verdicts present)")
    surfaced = {str(row["claim_tier"]) for row in picker.values()}
    assert surfaced == ssot_tiers, "picker collapsed the mixed SSOT to fewer tiers"
    assert _TIER1_LABEL in surfaced and _TIER2_LABEL in surfaced


# --------------------------------------------------------------------------
# Honesty floor preserved: cohort-LEVEL claim stays conservative Tier 1
# --------------------------------------------------------------------------


def test_cohort_level_claim_tier_stays_conservative_floor(picker_mod) -> None:
    """Per-case promotion must NOT escalate the cohort-LEVEL claim.

    The picker's top-level + the cohort overview's top-level claim_tier stay
    the conservative "Tier 1 engineering candidate" floor — surfacing a single
    case's real-solver validation must never imply the whole cohort is
    validated (anti-overclaim, ADR-023).
    """
    assert picker_mod.CLAIM_TIER == _TIER1_LABEL
    overview = _overview_to_dict(build_cohort_overview(REPO_ROOT))
    assert overview["claim_tier"] == _TIER1_LABEL


def test_cohort_overview_overclaim_guard_still_passes() -> None:
    """build_cohort_overview runs _assert_no_overclaim; adding per-case tier_2
    labels must not trip it (the forbidden tokens are physics-claim phrases,
    not the tier label)."""
    # Raises ValueError if any forbidden claim token leaked in.
    build_cohort_overview(REPO_ROOT)


# --------------------------------------------------------------------------
# Codex R1 regression locks
# --------------------------------------------------------------------------


def test_tier_resolution_is_scoped_to_supplied_repo_root() -> None:
    """Codex R1 P2-a + R2: tier follows the SUPPLIED repo_root's verdict files,
    but still gated on registry membership (the registry is the SSOT of cohort
    admission). A registered case is tier_1 under an empty root and tier_2 once
    that root records a PASS; an UNREGISTERED case with a PASS verdict stays
    tier_1 — a stray experimental verdict cannot fabricate a Tier-2 claim."""
    reg_case = "cylinder-pv-candidate"  # a registered cohort case
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        gs = root / "golden_samples"
        # (a) registered case, NO verdict under this root → tier_1 (honors the
        #     supplied tree, NOT the module registry which has it at tier_2).
        (gs / reg_case).mkdir(parents=True)
        assert get_claim_tier(reg_case, root) == "tier_1_candidate"
        # (b) registered case + PASS verdict under this root → tier_2.
        (gs / reg_case / "cross_check_verdict.yaml").write_text(
            json.dumps({"verdict": "PASS", "tolerance_pct": 5.0}), encoding="utf-8"
        )
        assert get_claim_tier(reg_case, root) == "tier_2_validated"
        # (c) UNREGISTERED case + PASS verdict → STILL tier_1 (Codex R2: the
        #     registry SSOT gates promotion; a stray verdict cannot self-promote).
        exp = gs / "experimental-unregistered-candidate"
        exp.mkdir(parents=True)
        (exp / "cross_check_verdict.yaml").write_text(
            json.dumps({"verdict": "PASS", "tolerance_pct": 5.0}), encoding="utf-8"
        )
        assert (
            get_claim_tier("experimental-unregistered-candidate", root)
            == "tier_1_candidate"
        )


def test_hertz_contact_yaml_nested_verdict_surfaces_tier2() -> None:
    """Codex R1 P2-b: hertz-contact is genuinely validated (Phase 34 C real
    ccx PASS) but shipped a YAML verdict with a NESTED verdict_outcome.verdict
    and was absent from the registry — so it stayed hidden. It must now surface
    Tier 2 on both the picker and the cohort overview (json-then-yaml parse +
    nested-verdict handling + registry registration)."""
    case_id = "hertz-contact-candidate"
    verdict = GOLDEN / case_id / "cross_check_verdict.yaml"
    if not verdict.is_file():
        pytest.skip(f"{case_id} verdict artifact absent in this env")
    # Module SSOT (no root) and root-scoped path must agree on Tier 2.
    assert claim_tier_label_for(case_id) == _TIER2_LABEL
    assert claim_tier_label_for(case_id, REPO_ROOT) == _TIER2_LABEL

    picker_mod = _load_candidate_cases_module()
    picker = _picker_by_id(picker_mod)
    assert picker.get(case_id, {}).get("claim_tier") == _TIER2_LABEL
    cohort = _cohort_by_id()
    assert cohort.get(case_id, {}).get("claim_tier") == _TIER2_LABEL
