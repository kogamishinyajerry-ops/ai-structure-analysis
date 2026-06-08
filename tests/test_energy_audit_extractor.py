"""Tests for the Tier 1 energy audit extractor.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

# Test fixtures preserve OpenRadioss wide-column row formatting; line-length
# would otherwise force unreadable splits.
# ruff: noqa: E501

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from app.services.ballistics.energy_audit_extractor import (
    CLAIM_IMPACT_CLOSED_AGGREGATE,
    CLAIM_IMPACT_PARTIAL_KE_ONLY,
    CLAIM_IMPACT_UNAVAILABLE,
    assess_energy_audit,
    build_energy_audit_from_engine_out,
)
from app.services.ballistics.engine_energy_history import (
    parse_engine_out_energy_history,
)
from app.services.ballistics.metric_extraction import BallisticEnergyAudit

_HEADER = (
    "   CYCLE    TIME      TIME-STEP  ELEMENT          ERROR  "
    "I-ENERGY    K-ENERGY T  K-ENERGY R  EXT-WORK     MAS.ERR     "
    "TOTAL MASS  MASS ADDED"
)


def _write_engine_out(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "model_00_0001.out"
    path.write_text(body, encoding="utf-8")
    return path


def _closed_engine_out(tmp_path: Path) -> Path:
    body = textwrap.dedent(f"""
        {_HEADER}
               0   0.000      1.0E-04   INTER          1   0.0%   0.0   1.0E+03   0.0   0.0   0.0   1.0E+04   0.0
            1000  1.0E-02    1.0E-05   NODE           1   1.0%   2.0E+02 8.0E+02   0.0   0.0   0.0   1.0E+04   0.0
    """).strip()
    return _write_engine_out(tmp_path, body)


def test_build_audit_extracts_kinetic_terms_from_real_progress_table(
    tmp_path: Path,
) -> None:
    audit = build_energy_audit_from_engine_out(_closed_engine_out(tmp_path))
    assert audit.initial_kinetic_energy_j == pytest.approx(1.0e3)
    assert audit.residual_kinetic_energy_j == pytest.approx(8.0e2)
    # Per-term breakdown stays None — engine .out cannot split plastic / contact / hourglass.
    assert audit.plastic_dissipation_j is None
    assert audit.contact_friction_j is None
    assert audit.hourglass_energy_j is None


def test_assess_closed_aggregate_status_when_engine_out_has_full_table(
    tmp_path: Path,
) -> None:
    out_path = _closed_engine_out(tmp_path)
    history = parse_engine_out_energy_history(out_path)
    audit = build_energy_audit_from_engine_out(out_path, history=history)
    block = assess_energy_audit(audit, history=history)
    assert block["status"] == "closed_aggregate"
    assert block["aggregate_internal_energy_j"] == pytest.approx(2.0e2)
    assert block["external_work_j"] == pytest.approx(0.0)
    assert block["energy_balance_error_pct"] == pytest.approx(0.0, abs=1e-9)
    assert block["breakdown_status"] == "aggregated_into_internal_energy"
    assert block["claim_impact"] == CLAIM_IMPACT_CLOSED_AGGREGATE
    # Legacy missing_terms list reports per-term keys that remain None — the
    # 33 existing GS-102 reports still see plastic / contact / hourglass in
    # missing_terms when they read this block.
    assert set(block["missing_terms"]) == {
        "plastic_dissipation_j",
        "contact_friction_j",
        "hourglass_energy_j",
    }


def test_assess_partial_candidate_when_engine_out_missing_but_ke_known(
    tmp_path: Path,
) -> None:
    block = assess_energy_audit(
        BallisticEnergyAudit(
            initial_kinetic_energy_j=1731.0,
            residual_kinetic_energy_j=125.0,
        ),
        history=None,
    )
    assert block["status"] == "partial_candidate"
    assert block["initial_kinetic_energy_j"] == pytest.approx(1731.0)
    assert block["residual_kinetic_energy_j"] == pytest.approx(125.0)
    assert block["aggregate_internal_energy_j"] is None
    assert block["external_work_j"] is None
    assert block["claim_impact"] == CLAIM_IMPACT_PARTIAL_KE_ONLY


def test_assess_unavailable_when_neither_engine_out_nor_ke_present() -> None:
    block = assess_energy_audit(BallisticEnergyAudit(), history=None)
    assert block["status"] == "unavailable"
    assert block["initial_kinetic_energy_j"] is None
    assert block["residual_kinetic_energy_j"] is None
    assert block["aggregate_internal_energy_j"] is None
    assert block["claim_impact"] == CLAIM_IMPACT_UNAVAILABLE


def test_build_audit_returns_all_none_when_engine_out_missing(tmp_path: Path) -> None:
    audit = build_energy_audit_from_engine_out(tmp_path / "absent.out")
    assert audit.initial_kinetic_energy_j is None
    assert audit.residual_kinetic_energy_j is None
    assert audit.plastic_dissipation_j is None


def test_audit_status_block_preserves_unit_system_note(tmp_path: Path) -> None:
    out_path = _closed_engine_out(tmp_path)
    history = parse_engine_out_energy_history(out_path)
    block = assess_energy_audit(
        build_energy_audit_from_engine_out(out_path, history=history),
        history=history,
    )
    assert "OpenRadioss deck unit system" in block["unit_system_note"]
    assert "kg/mm/ms" in block["unit_system_note"]


def test_audit_block_preserves_tier1_boundary_wording(tmp_path: Path) -> None:
    out_path = _closed_engine_out(tmp_path)
    history = parse_engine_out_energy_history(out_path)
    block = assess_energy_audit(
        build_energy_audit_from_engine_out(out_path, history=history),
        history=history,
    )
    text = block["claim_impact"].lower()
    # The Tier 1 boundary must be the disclaimer form, never the positive claim.
    assert "tier 1" in text
    assert "not signed validation" in text
    assert "not benchmark agreement" in text
    # Forbidden positive claims (each must not appear except as part of the
    # explicit ``not ...`` disclaimer phrasing).
    for positive_claim in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert positive_claim not in text, f"positive claim leaked: {positive_claim}"
    # Sanity: stripping the disclaimer prefix must leave no other "benchmark
    # agreement" or "signed validation" tokens.
    stripped = text.replace("not signed validation", "").replace("not benchmark agreement", "")
    assert "signed validation" not in stripped
    assert "benchmark agreement" not in stripped


def test_explicit_history_argument_overrides_path_parse(tmp_path: Path) -> None:
    # If the caller supplies an already-parsed history, the path may not exist.
    out_path = _closed_engine_out(tmp_path)
    history = parse_engine_out_energy_history(out_path)
    audit = build_energy_audit_from_engine_out(
        tmp_path / "does_not_matter.out",
        history=history,
    )
    assert audit.initial_kinetic_energy_j == pytest.approx(1.0e3)
