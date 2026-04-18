"""CalculiX (ccx) driver with version gating and fault classification."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from schemas.sim_state import FaultClass

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 600
# ADR-002 specifies CalculiX 2.21 as the target. Debian bookworm main
# ships calculix-ccx 2.20 (see Dockerfile comment + P1-01 PR #10).
# Per ADR-008 N-3 we pin the floor at the Debian-shipped 2.20 and record
# the actual version in manifest.yaml.tool_versions. Upgrading the shipped
# binary to 2.21 via source-build is a follow-up task, not a P1-01/02 gate.
REQUIRED_CCX_VERSION = (2, 20)
VERSION_FLAGS = ("-v", "-version", "--version")

SYNTAX_PATTERNS = (
    "unknown keyword",
    "input error",
    "cannot open input file",
    "missing include file",
    "parameter not recognized",
    "not a valid keyword",
    "syntax error",
    "*error in input",
)

TIMESTEP_PATTERNS = (
    "time increment required is less than the minimum",
    "too many cutbacks",
    "increment size smaller than minimum",
    "divergence; trying a smaller increment",
    "reduce the time increment",
    "maximum number of cutbacks reached",
    "step size too small",
)

CONVERGENCE_PATTERNS = (
    "no convergence",
    "convergence not reached",
    "maximum number of iterations",
    "equilibrium not reached",
    "residual",
    "divergence",
    "solution seems to diverge",
)


def _find_ccx() -> str | None:
    """Return the absolute path to ``ccx`` if available on PATH."""
    return shutil.which("ccx")


def _parse_ccx_version(text: str) -> str | None:
    """Extract a semantic version like ``2.21`` from ccx output."""
    match = re.search(r"(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        return None

    major, minor, patch = match.groups()
    if patch is None:
        return f"{major}.{minor}"
    return f"{major}.{minor}.{patch}"


def _version_tuple(version: str) -> tuple[int, int, int]:
    """Convert a semantic version string to a comparable tuple."""
    parts = [int(part) for part in version.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _probe_ccx_version(ccx_bin: str) -> str | None:
    """Ask the binary for its version using common CLI flags."""
    for flag in VERSION_FLAGS:
        try:
            result = subprocess.run(
                [ccx_bin, flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue

        version = _parse_ccx_version(f"{result.stdout}\n{result.stderr}")
        if version:
            return version

    return None


def _ensure_supported_ccx_version(ccx_bin: str) -> str:
    """Verify that the installed CalculiX binary satisfies ADR-002."""
    version = _probe_ccx_version(ccx_bin)
    if version is None:
        raise RuntimeError("Unable to determine CalculiX version from ccx output.")

    if _version_tuple(version) < (*REQUIRED_CCX_VERSION, 0):
        raise RuntimeError(
            f"CalculiX {version} is unsupported; AI-FEA requires >= "
            f"{REQUIRED_CCX_VERSION[0]}.{REQUIRED_CCX_VERSION[1]}."
        )

    return version


def _collect_solver_text(
    work_dir: Path,
    jobname: str,
    *,
    stdout: str = "",
    stderr: str = "",
) -> str:
    """Aggregate stdout/stderr and output files for failure analysis."""
    chunks = [stdout, stderr]
    for suffix in ("dat", "sta", "cvg"):
        path = work_dir / f"{jobname}.{suffix}"
        if path.exists():
            chunks.append(path.read_text(errors="replace"))
    return "\n".join(chunk for chunk in chunks if chunk)


def classify_solver_failure(
    log_text: str,
    *,
    returncode: int,
    timed_out: bool = False,
) -> FaultClass:
    """Map solver text into ADR-004 fault classes."""
    if timed_out:
        return FaultClass.SOLVER_TIMESTEP

    normalized = log_text.lower()
    if any(pattern in normalized for pattern in SYNTAX_PATTERNS):
        return FaultClass.SOLVER_SYNTAX
    if any(pattern in normalized for pattern in TIMESTEP_PATTERNS):
        return FaultClass.SOLVER_TIMESTEP
    if any(pattern in normalized for pattern in CONVERGENCE_PATTERNS):
        return FaultClass.SOLVER_CONVERGENCE
    if returncode != 0:
        return FaultClass.SOLVER_CONVERGENCE
    return FaultClass.NONE


def _check_convergence(work_dir: Path, jobname: str) -> bool:
    """Inspect output files to determine whether the solve converged cleanly."""
    sta_path = work_dir / f"{jobname}.sta"
    if not sta_path.exists():
        return False

    log_text = _collect_solver_text(work_dir, jobname)
    return classify_solver_failure(log_text, returncode=0) == FaultClass.NONE


def run_solve(
    inp_path: Path,
    work_dir: Path,
    *,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Run a CalculiX solve and return result metadata."""
    ccx_bin = _find_ccx()
    if ccx_bin is None:
        raise FileNotFoundError(
            "CalculiX executable 'ccx' not found on PATH. "
            "Install CalculiX 2.21 or add it to your system PATH."
        )

    ccx_version = _ensure_supported_ccx_version(ccx_bin)
    work_dir.mkdir(parents=True, exist_ok=True)

    jobname = inp_path.stem
    cmd = [ccx_bin, "-i", jobname]
    logger.info("Running CalculiX: %s (cwd=%s, timeout=%ds)", cmd, work_dir, timeout_s)

    timed_out = False
    stdout = ""
    stderr = ""
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
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        logger.error("CalculiX solve timed out after %ds", timeout_s)
        timed_out = True
        returncode = -1
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

    wall_time = time.monotonic() - t0
    frd_path = work_dir / f"{jobname}.frd"
    dat_path = work_dir / f"{jobname}.dat"
    sta_path = work_dir / f"{jobname}.sta"
    log_text = _collect_solver_text(work_dir, jobname, stdout=stdout, stderr=stderr)

    converged = returncode == 0 and _check_convergence(work_dir, jobname)
    fault_class = FaultClass.NONE
    failure_reason = None
    if not converged:
        fault_class = classify_solver_failure(
            log_text,
            returncode=returncode,
            timed_out=timed_out,
        )
        failure_reason = (
            "CalculiX solve timed out."
            if timed_out
            else next(
                (line.strip() for line in log_text.splitlines() if line.strip()),
                "CalculiX solve failed.",
            )
        )

    return {
        "frd_path": str(frd_path) if frd_path.exists() else None,
        "dat_path": str(dat_path) if dat_path.exists() else None,
        "sta_path": str(sta_path) if sta_path.exists() else None,
        "converged": converged,
        "wall_time_s": round(wall_time, 2),
        "returncode": returncode,
        "ccx_version": ccx_version,
        "fault_class": fault_class,
        "failure_reason": failure_reason,
    }
