"""FM-04a Phase 38 B — single-C3D6 wedge uniaxial Hooke's-law pins.

Phase 38 B adds the **6th element class** (C3D6) to the validated cohort
(prior 5: C3D4 / C3D8 / C3D10 / S4 / B31). The 6-node linear pentahedral
wedge is solved in pure uniaxial stress and cross-checked against the
closed-form Hooke's law sigma = E*epsilon — a GENUINE real-ccx cross-check
(exact agreement, 0.00% residual -> tier_2_validated), NOT an
analytical-only reference (cf. Phase 38 A NAFEMS).

Anti-gaming guards:
  * U:-1 — the adapter must ACTUALLY emit C3D6: `TYPE=C3D6` appears in
           backend/app/adapters/calculix/, and the writer produces a
           well-formed single-C3D6 INP (6 nodes, 1 wedge element).
  * real cross-check — the committed verdict carries a ccx-observed stress
           AND the independent analytical; verdict PASS -> tier_2_validated.

Tier 2 real-solver validated; not signed validation; not benchmark
agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTER_DIR = REPO_ROOT / "backend" / "app" / "adapters" / "calculix"
CASE_ID = "wedge-c3d6-candidate"
VERDICT = REPO_ROOT / "golden_samples" / CASE_ID / "cross_check_verdict.yaml"


def test_u_guard_adapter_emits_c3d6() -> None:
    """U:-1 — TYPE=C3D6 actually appears in the CalculiX adapter source."""
    hits = [
        p.name
        for p in ADAPTER_DIR.rglob("*.py")
        if "TYPE=C3D6" in p.read_text(encoding="utf-8")
    ]
    assert hits, (
        "no TYPE=C3D6 found in backend/app/adapters/calculix/ — the 6th "
        "element class is not actually exhibited by the adapter (U:-1 guard)"
    )


def test_writer_emits_wellformed_single_c3d6(tmp_path: Path) -> None:
    """The adapter writer produces a valid single-C3D6 wedge INP:
    6 nodes, exactly one wedge element with 6-node connectivity."""
    from app.adapters.calculix.inp_writer import (
        write_single_c3d6_wedge_uniaxial_inp,
    )

    inp = write_single_c3d6_wedge_uniaxial_inp(tmp_path, jobname="t")
    lines = inp.read_text(encoding="utf-8").splitlines()
    assert "*ELEMENT, TYPE=C3D6, ELSET=EALL" in lines
    assert "1, 1, 2, 3, 4, 5, 6" in lines  # one wedge, 6-node connectivity
    # *NODE block holds exactly 6 node definitions.
    node_idx = lines.index("*NODE")
    elem_idx = lines.index("*ELEMENT, TYPE=C3D6, ELSET=EALL")
    node_defs = [ln for ln in lines[node_idx + 1 : elem_idx] if ln.strip()]
    assert len(node_defs) == 6


@pytest.fixture(scope="module")
def verdict() -> dict:
    assert VERDICT.is_file(), f"missing verdict at {VERDICT}"
    return json.loads(VERDICT.read_text(encoding="utf-8"))


def test_verdict_real_cross_check_pass(verdict: dict) -> None:
    assert verdict["solver_kind"] == "linear_static"
    assert verdict["cross_check_kind"] == "c3d6_wedge_uniaxial_hookes_law"
    assert verdict["element_class"] == "C3D6"
    assert verdict["verdict"] == "PASS"
    assert verdict["tolerance_pct"] == pytest.approx(1.0)
    # Genuine cross-check: analytical = -E*epsilon (210e9 * 1e-3 = 210 MPa,
    # compressive); observed comes from ccx; they match to <1%.
    assert verdict["analytical_pa"] == pytest.approx(-2.10e8)
    assert verdict["observed_pa"] == pytest.approx(-2.10e8, rel=0.01)
    assert abs(verdict["residual_pct"]) <= 1.0


def test_promoted_to_tier_2() -> None:
    """The case is registered and the verdict overlay promotes it to
    tier_2_validated on the PASS verdict (real solver + analytical)."""
    from app.services.reporting._claim_tier import (
        CLAIM_TIER_REGISTRY,
        _apply_verdict_overlay,
        get_claim_tier,
    )

    assert CASE_ID in CLAIM_TIER_REGISTRY
    _apply_verdict_overlay()
    assert get_claim_tier(CASE_ID) == "tier_2_validated"
