"""Tests for tools/calculix_driver.py — subprocess wrapper and convergence logic."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.calculix_driver import _check_convergence, _find_ccx, run_solve


class TestFindCcx:
    def test_found(self):
        with patch("tools.calculix_driver.shutil.which", return_value="/usr/bin/ccx"):
            assert _find_ccx() == "/usr/bin/ccx"

    def test_not_found(self):
        with patch("tools.calculix_driver.shutil.which", return_value=None):
            assert _find_ccx() is None


class TestCheckConvergence:
    def test_missing_sta(self, tmp_path):
        assert _check_convergence(tmp_path, "job") is False

    def test_sta_with_error(self, tmp_path):
        (tmp_path / "job.sta").write_text("STEP 1\n*ERROR in solver\n")
        assert _check_convergence(tmp_path, "job") is False

    def test_dat_with_error(self, tmp_path):
        (tmp_path / "job.sta").write_text("STEP 1 converged\n")
        (tmp_path / "job.dat").write_text("*ERROR in element 42\n")
        assert _check_convergence(tmp_path, "job") is False

    def test_clean_run(self, tmp_path):
        (tmp_path / "job.sta").write_text("STEP 1  INC 1  ATT 1  ITCNT 3  CONT ELEM      0\n")
        assert _check_convergence(tmp_path, "job") is True


class TestRunSolve:
    def test_ccx_not_on_path(self, tmp_path):
        inp = tmp_path / "deck.inp"
        inp.touch()
        with patch("tools.calculix_driver._find_ccx", return_value=None):
            with pytest.raises(FileNotFoundError, match="ccx"):
                run_solve(inp, tmp_path)

    def test_successful_solve(self, tmp_path):
        inp = tmp_path / "deck.inp"
        inp.touch()

        # Pre-create the output files that ccx would produce.
        (tmp_path / "deck.frd").write_text("FRD DATA")
        (tmp_path / "deck.dat").write_text("DAT DATA")
        (tmp_path / "deck.sta").write_text("STEP 1 converged\n")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with (
            patch("tools.calculix_driver._find_ccx", return_value="/usr/bin/ccx"),
            patch("tools.calculix_driver.subprocess.run", return_value=mock_result),
        ):
            res = run_solve(inp, tmp_path)

        assert res["converged"] is True
        assert res["frd_path"] is not None
        assert res["returncode"] == 0
        assert res["wall_time_s"] >= 0

    def test_failed_solve(self, tmp_path):
        inp = tmp_path / "deck.inp"
        inp.touch()

        (tmp_path / "deck.sta").write_text("*ERROR in solver\n")

        mock_result = MagicMock()
        mock_result.returncode = 1

        with (
            patch("tools.calculix_driver._find_ccx", return_value="/usr/bin/ccx"),
            patch("tools.calculix_driver.subprocess.run", return_value=mock_result),
        ):
            res = run_solve(inp, tmp_path)

        assert res["converged"] is False
        assert res["returncode"] == 1

    def test_timeout(self, tmp_path):
        import subprocess as _sp

        inp = tmp_path / "deck.inp"
        inp.touch()

        with (
            patch("tools.calculix_driver._find_ccx", return_value="/usr/bin/ccx"),
            patch(
                "tools.calculix_driver.subprocess.run",
                side_effect=_sp.TimeoutExpired(cmd="ccx", timeout=5),
            ),
        ):
            res = run_solve(inp, tmp_path, timeout_s=5)

        assert res["converged"] is False
        assert res["returncode"] == -1
