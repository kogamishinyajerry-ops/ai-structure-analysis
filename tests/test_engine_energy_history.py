"""Tests for the OpenRadioss engine `.out` energy history parser.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

# Test fixtures preserve OpenRadioss wide-column row formatting; line-length
# would otherwise force unreadable splits.
# ruff: noqa: E501

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from app.services.ballistics.engine_energy_history import (
    EngineEnergyHistory,
    parse_engine_out_energy_history,
    summarize_energy_history,
)

_REAL_HEADER = (
    "   CYCLE    TIME      TIME-STEP  ELEMENT          ERROR  "
    "I-ENERGY    K-ENERGY T  K-ENERGY R  EXT-WORK     MAS.ERR     "
    "TOTAL MASS  MASS ADDED"
)


def _write_engine_out(tmp_path: Path, body: str) -> Path:
    out_path = tmp_path / "model_00_0001.out"
    out_path.write_text(body, encoding="utf-8")
    return out_path


def test_parser_handles_real_three_row_table(tmp_path: Path) -> None:
    body = textwrap.dedent(f"""
        OpenRadioss Engine banner header line
        {_REAL_HEADER}
               0   0.000      0.1084E-03 INTER          1   0.0%   0.000      0.1731E+10   0.000       0.000       0.000      0.2028E+05   0.000
            1000  0.4794E-02  0.3192E-05 NODE          20  23.4%  0.5481E+09  0.1587E+10   0.000       0.000       0.000      0.2028E+05   0.000
            2000  0.1138E-01  0.9292E-05 NODE          50  18.0%  0.7113E+09  0.1330E+10   0.000       0.000       0.000      0.2028E+05   0.000
            3000  0.1538E-01  0.2444E-09 INTER          1  12.5%  0.7442E+09  0.1203E+10   0.000       0.000       0.000      0.2028E+05   0.000
    """).strip()
    history = parse_engine_out_energy_history(_write_engine_out(tmp_path, body))
    assert history.has_history is True
    assert len(history.rows) == 4
    assert history.rows[0].cycle == 0
    assert history.rows[0].element_kind == "INTER"
    assert history.rows[0].element_id == 1
    assert history.rows[0].kinetic_energy_translational == pytest.approx(0.1731e10)
    assert history.rows[-1].cycle == 3000
    assert history.rows[-1].internal_energy == pytest.approx(0.7442e9)


def test_summary_reports_aggregate_terms_and_balance(tmp_path: Path) -> None:
    body = textwrap.dedent(f"""
        {_REAL_HEADER}
               0   0.000      1.0E-04   INTER          1   0.0%   0.000   1.0E+03   0.0   0.0   0.0   0.2028E+05   0.0
            1000  1.0E-02    1.0E-05   NODE           1   1.0%   2.5E+02  7.5E+02   0.0   0.0   0.0   0.2028E+05   0.0
    """).strip()
    summary = summarize_energy_history(
        parse_engine_out_energy_history(_write_engine_out(tmp_path, body))
    )
    assert summary["initial_kinetic_energy_t"] == pytest.approx(1.0e3)
    assert summary["residual_kinetic_energy_t"] == pytest.approx(7.5e2)
    assert summary["final_internal_energy_total"] == pytest.approx(2.5e2)
    assert summary["final_external_work"] == pytest.approx(0.0)
    # KE_initial + EXT_WORK - KE_residual - I_internal = 1000 - 750 - 250 = 0 → 0% error
    assert summary["energy_balance_error_pct"] == pytest.approx(0.0, abs=1e-9)


def test_summary_reports_non_zero_balance_when_terms_dont_match(tmp_path: Path) -> None:
    body = textwrap.dedent(f"""
        {_REAL_HEADER}
               0   0.000      1.0E-04   INTER          1   0.0%   0.000   1.0E+03   0.0   0.0   0.0   1.0E+04   0.0
            1000  1.0E-02    1.0E-05   NODE           1   1.0%   1.0E+02  7.5E+02   0.0   0.0   0.0   1.0E+04   0.0
    """).strip()
    summary = summarize_energy_history(
        parse_engine_out_energy_history(_write_engine_out(tmp_path, body))
    )
    # Conservation residual: 1000 + 0 - 750 - 100 = 150; pct = |150|/1000 * 100 = 15%
    assert summary["energy_balance_error_pct"] == pytest.approx(15.0, abs=1e-9)


def test_parser_returns_empty_history_when_file_missing(tmp_path: Path) -> None:
    history = parse_engine_out_energy_history(tmp_path / "does_not_exist.out")
    assert isinstance(history, EngineEnergyHistory)
    assert history.has_history is False
    assert history.initial_row is None
    assert history.final_row is None
    assert summarize_energy_history(history)["initial_kinetic_energy_t"] is None


def test_parser_skips_garbage_before_and_inside_table(tmp_path: Path) -> None:
    body = textwrap.dedent(f"""
        OpenRadioss banner
        SPECIFIC ENERGY . . . .  0
        HOURGLASS ENERGY . . . . 0
        {_REAL_HEADER}
        ANIMATION FILE: model_00A001 WRITTEN
               0   0.000      1.0E-04   INTER          1   0.0%   0.000   1.0E+03   0.0   0.0   0.0   1.0E+04   0.0
        ELEMENT SOMETHING NOISE LINE
            1000  1.0E-02    1.0E-05   NODE           1   1.0%   1.0E+02  9.0E+02   0.0   0.0   0.0   1.0E+04   0.0
        NORMAL TERMINATION
    """).strip()
    history = parse_engine_out_energy_history(_write_engine_out(tmp_path, body))
    assert [row.cycle for row in history.rows] == [0, 1000]


def test_parser_returns_empty_when_header_never_appears(tmp_path: Path) -> None:
    body = "Engine banner without progress table header at all.\n"
    history = parse_engine_out_energy_history(_write_engine_out(tmp_path, body))
    assert history.has_history is False


def test_summary_balance_error_is_none_when_initial_ke_is_zero(tmp_path: Path) -> None:
    body = textwrap.dedent(f"""
        {_REAL_HEADER}
               0   0.000      1.0E-04   INTER          1   0.0%   0.000   0.000   0.0   0.0   0.0   1.0E+04   0.0
            1000  1.0E-02    1.0E-05   NODE           1   1.0%   1.0E+02  0.000   0.0   0.0   0.0   1.0E+04   0.0
    """).strip()
    summary = summarize_energy_history(
        parse_engine_out_energy_history(_write_engine_out(tmp_path, body))
    )
    assert summary["energy_balance_error_pct"] is None


def test_claim_boundary_stays_tier1(tmp_path: Path) -> None:
    history = parse_engine_out_energy_history(tmp_path / "missing.out")
    forbidden = (
        "validated against",
        "benchmark agreement",
        "signed validation",
        "perforation completed",
        "validated physics",
    )
    text = history.claim_boundary.lower()
    for token in forbidden:
        assert token not in text
    assert "tier1_engineering_candidate" in text
    assert "not_benchmark_agreement" in text
