"""M4 — real CalculiX solve of the NAFEMS LE10 benchmark for the workflow runtime.

Flag-gated by ``settings.workflow_real_solver``. When enabled, the Workflow
Monitor's solver_run / post_processing / result_analysis stages run a **real
ccx solve** of the validated NAFEMS LE10 "thick plate pressure" deck and
extract σ_yy at point D, cross-checking the published −5.38 MPa reference —
instead of emitting synthetic mock numbers.

Honesty / tier: this is a **Tier 1 engineering candidate** path (real solver,
real .frd, real extracted stress) that *cross-checks a Tier-2 public benchmark*
(NAFEMS LE10). It is NOT signed validation (no independent signoff per ADR-023 /
ADR-027 G-2). The deck and the extraction (``parse_inp`` / ``node_D`` /
``parse_frd_syy``) are the **canonical** ones from
``golden_samples/nafems-le10-thick-plate-candidate/data/generator.py`` so the
workflow reproduces the exact validated quantity (σ_yy@D = −5.4379 MPa, +1.08%).

The validated deck is re-solved in a fresh work dir (never writing into the
sealed candidate artifacts). The case id is ``nafems-le10-…`` (not a
``^GS-\\d{3}$`` signed-registry id), so re-running ccx on it is permitted.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any

# Repo root: backend/app/services/workflow/real_le10.py -> parents[4] = repo.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_LE10_CASE_DIR = _REPO_ROOT / "golden_samples" / "nafems-le10-thick-plate-candidate"
_LE10_GENERATOR = _LE10_CASE_DIR / "data" / "generator.py"
# The validated 40×20×6 C3D20 deck (4800 elements) — re-solved live per run.
LE10_DECK = _LE10_CASE_DIR / "data" / "run_40_20_6_C3D20" / "solve.inp"

# Published NAFEMS LE10 reference (signed, ccx tension-positive convention) and
# the project's accepted agreement tolerance. Mirrors generator.TARGET_PA / the
# cross_check_verdict.yaml (tolerance_pct: 3.0).
LE10_TARGET_PA = -5.38e6
LE10_TOLERANCE_PCT = 3.0
# Authoritative counts from cross_check_verdict.yaml (parse_inp does not parse the
# two-line C3D20 element block, so these are sourced from the verdict record).
LE10_NODE_COUNT = 22815
LE10_ELEMENT_COUNT = 4800
LE10_ELEMENT_TYPE = "C3D20"
LE10_POINT_D = (2.0, 0.0, 0.3)


def _load_generator() -> Any:
    """Lazily import the canonical LE10 generator module by file path.

    Imported lazily (only on the real-solver path) so the backend does not
    hard-depend on golden_samples at module-load time. Only the pure extraction
    helpers (parse_inp / node_D / parse_frd_syy) are used — never ``solve_one``
    (which shells out to gmsh).
    """
    spec = importlib.util.spec_from_file_location("le10_generator", _LE10_GENERATOR)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"LE10 generator not importable: {_LE10_GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def le10_available() -> bool:
    """True iff a real LE10 solve is possible (ccx on PATH + deck present)."""
    from tools.calculix_driver import _find_ccx

    return _find_ccx() is not None and LE10_DECK.exists()


def run_le10_solve(work_dir: Path, *, timeout_s: int = 900) -> dict[str, Any]:
    """Re-solve the validated LE10 deck with real ccx in ``work_dir``.

    Copies the deck out of the sealed candidate dir first, so the validated
    artifacts are never overwritten. Returns the driver payload augmented with
    the deck path and authoritative mesh counts.

    Raises:
        FileNotFoundError: the LE10 deck is missing.
    """
    if not LE10_DECK.exists():
        raise FileNotFoundError(f"LE10 deck not found: {LE10_DECK}")
    from tools.calculix_driver import run_solve

    work_dir.mkdir(parents=True, exist_ok=True)
    deck = work_dir / "solve.inp"
    shutil.copy2(LE10_DECK, deck)
    result = run_solve(deck, work_dir, timeout_s=timeout_s)
    return {
        **result,
        "deck_path": str(deck),
        "node_count": LE10_NODE_COUNT,
        "element_count": LE10_ELEMENT_COUNT,
        "element_type": LE10_ELEMENT_TYPE,
    }


def extract_le10_benchmark(deck_path: Path, frd_path: Path) -> dict[str, Any]:
    """Extract σ_yy at point D from a solved LE10 ``.frd`` and grade it.

    Reuses the canonical generator extraction so the result is byte-identical to
    the validated path. Returns a benchmark verdict dict (SI Pa + MPa + percent).

    Raises:
        ValueError: σ_yy could not be read at point D (e.g. an incomplete solve).
    """
    gen = _load_generator()
    nodes, _elements = gen.parse_inp(Path(deck_path))
    node_d = gen.node_D(nodes)
    sigma_yy_pa = gen.parse_frd_syy(Path(frd_path), node_d)
    if sigma_yy_pa is None:
        raise ValueError("σ_yy not found at point D in the .frd (solve incomplete?)")
    residual_pct = (sigma_yy_pa - LE10_TARGET_PA) / LE10_TARGET_PA * 100.0
    verdict = "PASS" if abs(residual_pct) <= LE10_TOLERANCE_PCT else "FAIL"
    return {
        "node_d": node_d,
        "point_d_m": list(nodes[node_d]),
        "sigma_yy_pa": sigma_yy_pa,
        "target_pa": LE10_TARGET_PA,
        "residual_pct": residual_pct,
        "tolerance_pct": LE10_TOLERANCE_PCT,
        "verdict": verdict,
    }
