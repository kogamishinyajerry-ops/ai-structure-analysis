"""Tests for tools/calculix_driver.py."""

from __future__ import annotations

import subprocess as _sp
from unittest.mock import MagicMock, patch

import pytest

from schemas.sim_state import FaultClass
from tools.calculix_driver import (
    _check_convergence,
    _ensure_supported_ccx_version,
    _find_ccx,
    _parse_ccx_version,
    classify_solver_failure,
    run_solve,
)

# A REAL converged ccx ``.sta`` (copied from golden_samples/GS-003/gs003.sta): the
# SUMMARY-OF-JOB-INFORMATION header + ONE increment-completion data row. The leading-integer
# data row is the positive convergence marker `_check_convergence` now requires.
_REAL_CONVERGED_STA = (
    "SUMMARY OF JOB INFORMATION\n"
    "  STEP      INC     ATT  ITRS     TOT TIME     STEP TIME      INC TIME\n"
    "     1          1     1     1  0.100000E+01  0.100000E+01  0.100000E+01\n"
)
# Header but NO data row (an aborted/empty solve) — the false-positive the fix closes.
_HEADER_ONLY_STA = (
    "SUMMARY OF JOB INFORMATION\n"
    "  STEP      INC     ATT  ITRS     TOT TIME     STEP TIME      INC TIME\n"
)


class TestFindCcx:
    def test_found(self):
        with patch("tools.calculix_driver.shutil.which", return_value="/usr/bin/ccx"):
            assert _find_ccx() == "/usr/bin/ccx"

    def test_not_found(self):
        with patch("tools.calculix_driver.shutil.which", return_value=None):
            assert _find_ccx() is None


class TestVersionGate:
    def test_parse_ccx_version(self):
        assert _parse_ccx_version("CalculiX version 2.21") == "2.21"
        assert _parse_ccx_version("ccx_2.21.1") == "2.21.1"
        assert _parse_ccx_version("no version here") is None

    def test_supported_version(self):
        mock_result = MagicMock(stdout="CalculiX version 2.21", stderr="")
        with patch("tools.calculix_driver.subprocess.run", return_value=mock_result):
            assert _ensure_supported_ccx_version("/usr/bin/ccx") == "2.21"

    def test_rejects_unsupported_version(self):
        mock_result = MagicMock(stdout="CalculiX version 2.20", stderr="")
        with (
            patch("tools.calculix_driver.subprocess.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="unsupported"),
        ):
            _ensure_supported_ccx_version("/usr/bin/ccx")


class TestFailureClassification:
    def test_classifies_syntax(self):
        assert (
            classify_solver_failure("*ERROR in input syntax", returncode=1)
            == FaultClass.SOLVER_SYNTAX
        )

    def test_classifies_timestep(self):
        assert (
            classify_solver_failure(
                "Time increment required is less than the minimum",
                returncode=1,
            )
            == FaultClass.SOLVER_TIMESTEP
        )

    def test_classifies_convergence(self):
        assert (
            classify_solver_failure(
                "Residual divergence after maximum number of iterations", returncode=1
            )
            == FaultClass.SOLVER_CONVERGENCE
        )

    def test_deck_parse_undefined_set_is_not_convergence(self):
        """Regression (ADR-029 P3 OR-1): a ccx deck-parse error from an undefined node/element set
        (rc=201) must be classified SOLVER_SYNTAX, NOT the SOLVER_CONVERGENCE catch-all — it is a
        deck/input error, not a numerical divergence (the solve never entered the equilibrium loop).
        Wording observed from real ccx 2.x output (fed here as a captured string, not a live
        solve); the previous classifier mislabeled it and the aeron mapping reported DIVERGED."""
        real_ccx_text = (
            " *ERROR reading *SOLID SECTION: element set\n"
            " Eall\n"
            " has not yet been defined\n"
            " *ERROR in calinput\n"
        )
        fc = classify_solver_failure(real_ccx_text, returncode=201)
        assert fc is FaultClass.SOLVER_SYNTAX
        assert fc is not FaultClass.SOLVER_CONVERGENCE  # the bug being regressed

    def test_real_numerical_divergence_still_convergence(self):
        """The fix must NOT over-reach: a genuine equilibrium-loop divergence (no deck-parse
        markers) still classifies SOLVER_CONVERGENCE (→ DIVERGED)."""
        assert (
            classify_solver_failure(
                "increment 7: no convergence; solution seems to diverge", returncode=1
            )
            is FaultClass.SOLVER_CONVERGENCE
        )


class TestCheckConvergence:
    def test_missing_sta(self, tmp_path):
        assert _check_convergence(tmp_path, "job") is False

    def test_sta_with_error(self, tmp_path):
        (tmp_path / "job.sta").write_text("STEP 1\n*ERROR in input syntax\n", encoding="utf-8")
        assert _check_convergence(tmp_path, "job") is False

    def test_clean_run(self, tmp_path):
        # Real ccx .sta format with a completed-increment data row → converged.
        (tmp_path / "job.sta").write_text(_REAL_CONVERGED_STA, encoding="utf-8")
        assert _check_convergence(tmp_path, "job") is True

    def test_header_only_sta_is_not_converged(self, tmp_path):
        """Regression (audit Rank 9): a .sta with the SUMMARY header but NO increment data row
        (an empty/aborted solve, no error keyword) must NOT report converged — the old
        absence-of-error-only check falsely returned True here."""
        (tmp_path / "job.sta").write_text(_HEADER_ONLY_STA, encoding="utf-8")
        assert _check_convergence(tmp_path, "job") is False

    def test_empty_sta_is_not_converged(self, tmp_path):
        (tmp_path / "job.sta").write_text("", encoding="utf-8")
        assert _check_convergence(tmp_path, "job") is False

    def test_garbage_sta_without_error_keyword_is_not_converged(self, tmp_path):
        """No failure substring AND no data row → still not converged (the bug being regressed)."""
        (tmp_path / "job.sta").write_text("hello world\nnot a solver file\n", encoding="utf-8")
        assert _check_convergence(tmp_path, "job") is False


class TestRunSolve:
    def test_ccx_not_on_path(self, tmp_path):
        inp = tmp_path / "deck.inp"
        inp.touch()
        with (
            patch("tools.calculix_driver._find_ccx", return_value=None),
            pytest.raises(FileNotFoundError, match="ccx"),
        ):
            run_solve(inp, tmp_path)

    def test_successful_solve(self, tmp_path):
        inp = tmp_path / "solve.inp"
        inp.touch()
        (tmp_path / "solve.frd").write_text("FRD DATA", encoding="utf-8")
        (tmp_path / "solve.dat").write_text("DAT DATA", encoding="utf-8")
        (tmp_path / "solve.sta").write_text(_REAL_CONVERGED_STA, encoding="utf-8")

        mock_result = MagicMock(returncode=0, stdout="CalculiX finished", stderr="")

        with (
            patch("tools.calculix_driver._find_ccx", return_value="/usr/bin/ccx"),
            patch("tools.calculix_driver._ensure_supported_ccx_version", return_value="2.21"),
            patch("tools.calculix_driver.subprocess.run", return_value=mock_result),
        ):
            result = run_solve(inp, tmp_path)

        assert result["converged"] is True
        assert result["fault_class"] == FaultClass.NONE
        assert result["ccx_version"] == "2.21"
        assert result["frd_path"] is not None

    def test_syntax_failure(self, tmp_path):
        inp = tmp_path / "solve.inp"
        inp.touch()
        (tmp_path / "solve.sta").write_text("*ERROR in input syntax\n", encoding="utf-8")
        mock_result = MagicMock(returncode=1, stdout="", stderr="")

        with (
            patch("tools.calculix_driver._find_ccx", return_value="/usr/bin/ccx"),
            patch("tools.calculix_driver._ensure_supported_ccx_version", return_value="2.21"),
            patch("tools.calculix_driver.subprocess.run", return_value=mock_result),
        ):
            result = run_solve(inp, tmp_path)

        assert result["converged"] is False
        assert result["fault_class"] == FaultClass.SOLVER_SYNTAX

    def test_timestep_failure(self, tmp_path):
        inp = tmp_path / "solve.inp"
        inp.touch()
        (tmp_path / "solve.sta").write_text(
            "Time increment required is less than the minimum\n",
            encoding="utf-8",
        )
        mock_result = MagicMock(returncode=1, stdout="", stderr="")

        with (
            patch("tools.calculix_driver._find_ccx", return_value="/usr/bin/ccx"),
            patch("tools.calculix_driver._ensure_supported_ccx_version", return_value="2.21"),
            patch("tools.calculix_driver.subprocess.run", return_value=mock_result),
        ):
            result = run_solve(inp, tmp_path)

        assert result["converged"] is False
        assert result["fault_class"] == FaultClass.SOLVER_TIMESTEP

    def test_timeout(self, tmp_path):
        inp = tmp_path / "solve.inp"
        inp.touch()

        with (
            patch("tools.calculix_driver._find_ccx", return_value="/usr/bin/ccx"),
            patch("tools.calculix_driver._ensure_supported_ccx_version", return_value="2.21"),
            patch(
                "tools.calculix_driver.subprocess.run",
                side_effect=_sp.TimeoutExpired(cmd="ccx", timeout=5),
            ),
        ):
            result = run_solve(inp, tmp_path, timeout_s=5)

        assert result["converged"] is False
        assert result["returncode"] == -1
        assert result["fault_class"] == FaultClass.SOLVER_TIMESTEP
