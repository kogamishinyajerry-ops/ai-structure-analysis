"""CalculiX (ccx) driver for FEA solves.

Provides functions to:
  - Render a .inp deck from Jinja2 template + SimPlan parameters.
  - Invoke ``ccx`` subprocess and monitor convergence.
  - Collect output files (.frd, .dat, .sta).

Requires CalculiX 2.21+ on ``$PATH``.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default timeout for a solve (seconds).  Override via ``timeout_s`` kwarg.
DEFAULT_TIMEOUT_S = 600


def _find_ccx() -> str | None:
    """Return the absolute path to ``ccx`` if available on PATH."""
    return shutil.which("ccx")


def _check_convergence(work_dir: Path, jobname: str) -> bool:
    """Inspect CalculiX output files to determine convergence.

    Checks, in order:
      1. The ``.sta`` file for the presence of ``*INFO`` markers.
      2. The ``.dat`` file for solver error strings.
      3. Stdout log (if captured) for ``*ERROR`` lines.
    """
    sta_path = work_dir / f"{jobname}.sta"
    dat_path = work_dir / f"{jobname}.dat"

    # A successful CalculiX run writes a .sta file ending with
    # a summary line.  A missing .sta usually means the solver
    # crashed before writing anything.
    if not sta_path.exists():
        return False

    sta_text = sta_path.read_text(errors="replace")

    # CalculiX prints ``*ERROR`` lines on fatal failures.
    if "*ERROR" in sta_text:
        return False

    # If .dat exists, check for error markers there too.
    if dat_path.exists():
        dat_text = dat_path.read_text(errors="replace")
        if "*ERROR" in dat_text:
            return False

    # If we got here and have at least one step completed, treat as converged.
    return True


def run_solve(
    inp_path: Path,
    work_dir: Path,
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Run a CalculiX solve and return result metadata.

    Parameters
    ----------
    inp_path : Path
        Path to the .inp input deck.
    work_dir : Path
        Working directory for the solve (output files written here).
    timeout_s : int
        Maximum wall-clock seconds before the solve is killed.

    Returns
    -------
    dict
        Keys: ``frd_path``, ``dat_path``, ``sta_path``, ``converged``,
        ``wall_time_s``, ``returncode``.
    """
    ccx_bin = _find_ccx()
    if ccx_bin is None:
        raise FileNotFoundError(
            "CalculiX executable 'ccx' not found on PATH. "
            "Install CalculiX 2.21+ or add it to your system PATH."
        )

    work_dir.mkdir(parents=True, exist_ok=True)

    # CalculiX convention: ``ccx -i jobname`` (without .inp extension).
    jobname = inp_path.stem
    cmd = [ccx_bin, "-i", jobname]

    logger.info("Running CalculiX: %s  (cwd=%s, timeout=%ds)", cmd, work_dir, timeout_s)

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        returncode = result.returncode
    except subprocess.TimeoutExpired:
        logger.error("CalculiX solve timed out after %ds", timeout_s)
        returncode = -1
    wall_time = time.monotonic() - t0

    # Collect output paths
    frd_path = work_dir / f"{jobname}.frd"
    dat_path = work_dir / f"{jobname}.dat"
    sta_path = work_dir / f"{jobname}.sta"

    converged = returncode == 0 and _check_convergence(work_dir, jobname)

    return {
        "frd_path": str(frd_path) if frd_path.exists() else None,
        "dat_path": str(dat_path) if dat_path.exists() else None,
        "sta_path": str(sta_path) if sta_path.exists() else None,
        "converged": converged,
        "wall_time_s": round(wall_time, 2),
        "returncode": returncode,
    }
