"""Extended PV cylinder candidate E2E orchestrator.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Thin variation of ``demo_cylinder_pv/run_e2e_demo.py``: same 8-stage
orchestrator but on the L=400mm + P=20MPa geometry, writing to the
``cylinder-pv-extended-candidate`` fixture directory.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parent
CASE_ID = "cylinder-pv-extended-candidate"
FIXTURE_DIR = REPO_ROOT / "golden_samples" / CASE_ID


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-solver", action="store_true")
    args = parser.parse_args(argv)
    # Defer to the baseline PV orchestrator with overridden case_id +
    # pressure + geometry path. This avoids duplicating the 500-line
    # orchestrator state machine.
    sys.path.insert(0, str(REPO_ROOT))
    from demo_cylinder_pv.run_e2e_demo import run_pipeline  # type: ignore[import-not-found]
    run_pipeline(
        case_id=CASE_ID,
        geo_path=DEMO_DIR / "cylinder_extended.geo",
        fixture_dir=FIXTURE_DIR,
        internal_pressure_mpa=20.0,
        skip_solver=args.skip_solver,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
