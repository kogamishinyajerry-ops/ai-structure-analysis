"""CalculiX (ccx) driver for FEA solves.

Provides functions to:
  - Render a .inp deck from Jinja2 template + SimPlan parameters.
  - Invoke ``ccx`` subprocess and monitor convergence.
  - Collect output files (.frd, .dat, .sta).

Requires CalculiX 2.21+ on ``$PATH``.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-07.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def run_solve(inp_path: Path, work_dir: Path) -> dict[str, Any]:
    """Run a CalculiX solve and return result metadata.

    Parameters
    ----------
    inp_path : Path
        Path to the .inp input deck.
    work_dir : Path
        Working directory for the solve (output files written here).

    Returns
    -------
    dict
        Keys: ``frd_path``, ``dat_path``, ``sta_path``, ``converged``, ``wall_time_s``.
    """
    raise NotImplementedError("CalculiX driver not yet implemented — see AI-FEA-P0-07")
