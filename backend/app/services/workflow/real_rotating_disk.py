"""FM-05 — real CalculiX re-solve of the rotating-disk centrifugal benchmark.

The project's THIRD public-benchmark agreement (after NAFEMS LE10 / LE11) and
its first ROTATIONAL-BODY-FORCE one: a thin annular steel disk under a
centrifugal load (ccx ``*DLOAD ... CENTRIF``) whose bore hoop stress σ_θ(a) is
cross-checked against the classical Timoshenko & Goodier plane-stress closed
form (65.312 MPa). The reference is a CONTINUUM-(plane-stress)-elasticity stress
field — a continuum reduction a thin 3-D solid converges to — which is why ccx
reproduces it cleanly (unlike reduced-kinematic plate/shell theory references).

Mirrors :mod:`real_le10` exactly: re-solves the **sealed, self-contained
canonical deck** (``run_nr48_C3D20/solve.inp``, in the case's
``artifact_manifest.json``) with real ccx — it never re-meshes via gmsh (the
generator's ``solve_one`` does, and gmsh re-meshing is version-sensitive). Only
the generator's pure extraction helpers (``read_stress`` / ``_node_at``) are
imported, never ``solve_one``. The hoop stress is SYY at the bore node on the +x
axis (there θ ‖ global y); the node is re-found by COORDINATE from the .frd, so
no node-id stability across re-solve is assumed.

Honesty / tier: a **Tier 1 engineering candidate** re-derivation path (real
solver, real .frd, real extracted stress) of a Tier-2 public-benchmark
agreement. NOT signed validation (no independent signoff per ADR-023 / ADR-027
G-2). The case id is ``rotating-disk-…`` (not a ``^GS-\\d{3}$`` signed id), so
re-running ccx on it is permitted.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any

# Repo root: backend/app/services/workflow/real_rotating_disk.py -> parents[4].
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DISK_CASE_DIR = _REPO_ROOT / "golden_samples" / "rotating-disk-centrifugal-candidate"
_DISK_GENERATOR = _DISK_CASE_DIR / "data" / "generator.py"
# The canonical nr=48 (4608-element C3D20) centrifugal deck — sealed in the
# case's artifact_manifest.json, re-solved live per run.
DISK_DECK = _DISK_CASE_DIR / "data" / "run_nr48_C3D20" / "solve.inp"

# Timoshenko & Goodier plane-stress closed-form target σ_θ(a) and the project's
# accepted agreement tolerance (TIGHTER than LE10/LE11's 3.0% — read from the
# cross_check_verdict.yaml: tolerance_pct 1.0).
DISK_TARGET_PA = 65_312_000.0
DISK_TOLERANCE_PCT = 1.0
# ADR-027 V2-0 drift watchdog: the frozen observation from the canonical
# validated run (cross_check_verdict.yaml observed_pa, ccx 2.23). Same deck +
# same ccx version re-solves deterministically; this pin is a tight regression
# watchdog on the live re-solve, NOT a new truth claim (Tier 1, not signed).
DISK_OBSERVED_PA_PINNED = 65_353_300.0
DISK_DRIFT_REL = 5e-3
# Authoritative counts from cross_check_verdict.yaml. The bore point is
# (A, 0, T_HALF) = (inner radius, 0, mid-plane half-thickness); the bore node is
# re-found by coordinate from the .frd, never by a pinned node id.
DISK_NODE_COUNT = 26117
DISK_ELEMENT_COUNT = 4608
DISK_ELEMENT_TYPE = "C3D20"
DISK_BORE_POINT = (0.2, 0.0, 0.05)


def _load_generator() -> Any:
    """Lazily import the canonical rotating-disk generator module by file path.

    Imported lazily (only on the real-solver path) so the backend does not
    hard-depend on golden_samples at module-load time. Only the pure extraction
    helpers (read_stress / _node_at) are used — never ``solve_one`` (which shells
    out to gmsh and is gmsh-version-sensitive).
    """
    spec = importlib.util.spec_from_file_location("rotating_disk_generator", _DISK_GENERATOR)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"rotating-disk generator not importable: {_DISK_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rotating_disk_available() -> bool:
    """True iff a real rotating-disk solve is possible (ccx on PATH + deck)."""
    from tools.calculix_driver import _find_ccx

    return _find_ccx() is not None and DISK_DECK.exists()


def run_rotating_disk_solve(work_dir: Path, *, timeout_s: int = 900) -> dict[str, Any]:
    """Re-solve the sealed rotating-disk deck with real ccx in ``work_dir``.

    Copies the deck out of the sealed candidate dir first, so the validated
    artifacts are never overwritten. Returns the driver payload augmented with
    the deck path and authoritative mesh counts.

    Raises:
        FileNotFoundError: the rotating-disk deck is missing.
    """
    if not DISK_DECK.exists():
        raise FileNotFoundError(f"rotating-disk deck not found: {DISK_DECK}")
    from tools.calculix_driver import run_solve

    work_dir.mkdir(parents=True, exist_ok=True)
    deck = work_dir / "solve.inp"
    shutil.copy2(DISK_DECK, deck)
    result = run_solve(deck, work_dir, timeout_s=timeout_s)
    return {
        **result,
        "deck_path": str(deck),
        "node_count": DISK_NODE_COUNT,
        "element_count": DISK_ELEMENT_COUNT,
        "element_type": DISK_ELEMENT_TYPE,
    }


def extract_rotating_disk_benchmark(deck_path: Path, frd_path: Path) -> dict[str, Any]:
    """Extract σ_θ (hoop) at the inner bore from a solved disk ``.frd`` and grade.

    Reuses the canonical generator extraction (``read_stress`` parses the .frd's
    2C nodal-coord block + STRESS block; the bore node is re-found by COORDINATE).
    The hoop stress is SYY (index 1) at the bore node on the +x axis. Returns a
    benchmark verdict dict (SI Pa + percent). ``deck_path`` is accepted for a
    uniform extractor signature but unused (coords come from the .frd).

    Raises:
        ValueError: the bore node or σ_θ could not be read (e.g. incomplete solve).
    """
    del deck_path  # disk coords come from the .frd 2C block, not the deck
    gen = _load_generator()
    coords, stress = gen.read_stress(Path(frd_path))
    if not coords or not stress:
        raise ValueError("no nodal coords/stress in the .frd (solve incomplete?)")
    node_id = gen._node_at(coords, DISK_BORE_POINT)
    if node_id not in stress:
        raise ValueError(f"bore node {node_id} has no stress record in the .frd")
    sigma_theta_pa = stress[node_id][1]  # SYY = hoop on the +x axis
    residual_pct = (sigma_theta_pa - DISK_TARGET_PA) / DISK_TARGET_PA * 100.0
    verdict = "PASS" if abs(residual_pct) <= DISK_TOLERANCE_PCT else "FAIL"
    return {
        "node_id": node_id,
        "point_m": list(coords[node_id]),
        "sigma_theta_pa": sigma_theta_pa,
        "target_pa": DISK_TARGET_PA,
        "residual_pct": residual_pct,
        "tolerance_pct": DISK_TOLERANCE_PCT,
        "verdict": verdict,
    }
