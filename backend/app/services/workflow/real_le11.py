"""FM-05 — real CalculiX re-solve of the NAFEMS LE11 thermal-stress benchmark.

The project's SECOND public-benchmark agreement (after LE10) and its first
THERMAL-STRESS / solid-of-revolution one: an imposed steady temperature field
``T = sqrt(x^2+y^2)+z`` drives a thermo-elastic ``*STATIC`` step (no mechanical
load), and σ_zz at point A = (1, 0, 0) is cross-checked against the published
NAFEMS LE11 reference −105 MPa.

This module mirrors :mod:`real_le10` exactly: it re-solves the **sealed,
self-contained canonical deck** (``run_r4_C3D20/solve.inp``, in the case's
``artifact_manifest.json``) with real ccx — it never re-meshes via gmsh (the
generator's ``solve_one`` does, and gmsh re-meshing is version-sensitive). Only
the generator's pure extraction helpers (``parse_inp`` / ``node_A`` /
``parse_frd_szz``) are imported, never ``solve_one``.

Honesty / tier: this is a **Tier 1 engineering candidate** re-derivation path
(real solver, real .frd, real extracted stress) of a Tier-2 public-benchmark
agreement. It is NOT signed validation (no independent signoff per ADR-023 /
ADR-027 G-2). The case id is ``nafems-le11-…`` (not a ``^GS-\\d{3}$`` signed
id), so re-running ccx on it is permitted.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any

# Repo root: backend/app/services/workflow/real_le11.py -> parents[4] = repo.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_LE11_CASE_DIR = _REPO_ROOT / "golden_samples" / "nafems-le11-solid-cyl-temperature-candidate"
_LE11_GENERATOR = _LE11_CASE_DIR / "data" / "generator.py"
# The canonical r4 (5632-element C3D20) thermo-elastic deck — sealed in the
# case's artifact_manifest.json, re-solved live per run.
LE11_DECK = _LE11_CASE_DIR / "data" / "run_r4_C3D20" / "solve.inp"

# Published NAFEMS LE11 reference (ccx tension-positive convention) and the
# project's accepted agreement tolerance. Mirrors generator.TARGET_PA / the
# cross_check_verdict.yaml (tolerance_pct: 3.0).
LE11_TARGET_PA = -105.0e6
LE11_TOLERANCE_PCT = 3.0
# ADR-027 V2-0 drift watchdog: the frozen observation from the canonical
# validated run (cross_check_verdict.yaml observed_pa, ccx 2.23). Same deck +
# same ccx version re-solves deterministically (direct sparse solve, no parallel
# nondeterminism); across ccx versions O(0.1–0.5%) drift is physically expected.
# Layered gate: verdict PASS within LE11_TOLERANCE_PCT of the published target is
# the hard, never-relaxed claim; this pin is a tight regression watchdog on the
# live re-solve, NOT a new truth claim (Tier 1, not signed validation).
LE11_OBSERVED_PA_PINNED = -105_398_000.0
LE11_DRIFT_REL = 5e-3
# Authoritative counts from cross_check_verdict.yaml (parse_inp does not parse the
# two-line C3D20 element block, so these are sourced from the verdict record).
LE11_NODE_COUNT = 26221
LE11_ELEMENT_COUNT = 5632
LE11_ELEMENT_TYPE = "C3D20"
LE11_POINT_A = (1.0, 0.0, 0.0)


def _load_generator() -> Any:
    """Lazily import the canonical LE11 generator module by file path.

    Imported lazily (only on the real-solver path) so the backend does not
    hard-depend on golden_samples at module-load time. Only the pure extraction
    helpers (parse_inp / node_A / parse_frd_szz) are used — never ``solve_one``
    (which shells out to gmsh).
    """
    spec = importlib.util.spec_from_file_location("le11_generator", _LE11_GENERATOR)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"LE11 generator not importable: {_LE11_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def le11_available() -> bool:
    """True iff a real LE11 solve is possible (ccx on PATH + deck present)."""
    from tools.calculix_driver import _find_ccx

    return _find_ccx() is not None and LE11_DECK.exists()


def run_le11_solve(work_dir: Path, *, timeout_s: int = 900) -> dict[str, Any]:
    """Re-solve the sealed LE11 deck with real ccx in ``work_dir``.

    Copies the deck out of the sealed candidate dir first, so the validated
    artifacts are never overwritten. Returns the driver payload augmented with
    the deck path and authoritative mesh counts.

    Raises:
        FileNotFoundError: the LE11 deck is missing.
    """
    if not LE11_DECK.exists():
        raise FileNotFoundError(f"LE11 deck not found: {LE11_DECK}")
    from tools.calculix_driver import run_solve

    work_dir.mkdir(parents=True, exist_ok=True)
    deck = work_dir / "solve.inp"
    shutil.copy2(LE11_DECK, deck)
    result = run_solve(deck, work_dir, timeout_s=timeout_s)
    return {
        **result,
        "deck_path": str(deck),
        "node_count": LE11_NODE_COUNT,
        "element_count": LE11_ELEMENT_COUNT,
        "element_type": LE11_ELEMENT_TYPE,
    }


def extract_le11_benchmark(deck_path: Path, frd_path: Path) -> dict[str, Any]:
    """Extract σ_zz at point A from a solved LE11 ``.frd`` and grade it.

    Reuses the canonical generator extraction so the result is byte-identical to
    the validated path. Returns a benchmark verdict dict (SI Pa + percent).

    Raises:
        ValueError: σ_zz could not be read at point A (e.g. an incomplete solve).
    """
    gen = _load_generator()
    nodes, _elements = gen.parse_inp(Path(deck_path))
    node_a = gen.node_A(nodes)
    sigma_zz_pa = gen.parse_frd_szz(Path(frd_path), node_a)
    if sigma_zz_pa is None:
        raise ValueError("σ_zz not found at point A in the .frd (solve incomplete?)")
    residual_pct = (sigma_zz_pa - LE11_TARGET_PA) / LE11_TARGET_PA * 100.0
    verdict = "PASS" if abs(residual_pct) <= LE11_TOLERANCE_PCT else "FAIL"
    return {
        "node_a": node_a,
        "point_a_m": list(nodes[node_a]),
        "sigma_zz_pa": sigma_zz_pa,
        "target_pa": LE11_TARGET_PA,
        "residual_pct": residual_pct,
        "tolerance_pct": LE11_TOLERANCE_PCT,
        "verdict": verdict,
    }
