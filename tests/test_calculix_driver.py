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
        # Anything below the floor (currently 2.20 per ADR-008 N-3) must raise.
        mock_result = MagicMock(stdout="CalculiX version 2.19", stderr="")
        with (
            patch("tools.calculix_driver.subprocess.run", return_value=mock_result),
            pytest.raises(RuntimeError, match="unsupported"),
        ):
            _ensure_supported_ccx_version("/usr/bin/ccx")

    def test_accepts_debian_shipped_2_20(self):
        # ADR-008 N-3: P1-01 baseline ships 2.20 from Debian bookworm.
        mock_result = MagicMock(stdout="CalculiX version 2.20", stderr="")
        with patch("tools.calculix_driver.subprocess.run", return_value=mock_result):
            assert _ensure_supported_ccx_version("/usr/bin/ccx") == "2.20"


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


class TestCheckConvergence:
    def test_missing_sta(self, tmp_path):
        assert _check_convergence(tmp_path, "job") is False

    def test_sta_with_error(self, tmp_path):
        (tmp_path / "job.sta").write_text("STEP 1\n*ERROR in input syntax\n", encoding="utf-8")
        assert _check_convergence(tmp_path, "job") is False

    def test_clean_run(self, tmp_path):
        (tmp_path / "job.sta").write_text(
            "STEP 1  INC 1  ATT 1  ITCNT 3  CONT ELEM      0\n",
            encoding="utf-8",
        )
        assert _check_convergence(tmp_path, "job") is True


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
        (tmp_path / "solve.sta").write_text("STEP 1 converged\n", encoding="utf-8")

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
