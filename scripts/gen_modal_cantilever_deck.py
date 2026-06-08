"""Re-generate the modal-cantilever-candidate fixture artefacts.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Reviewer entrypoint to reproduce the modal-cantilever-candidate fixture
from a clean checkout. Wraps the demo orchestrator with a fixed seed
so a re-run yields byte-identical evidence files (modulo the CalculiX
solver's machine-precision output, which the cross-check tolerates at
the 5% engineering bound).

Usage:
    .venv/bin/python scripts/gen_modal_cantilever_deck.py

The script is referenced from the cohort snapshot manifest's
``generator/<case>.py`` slot (Phase 9 B schema 1.3.0) so the trust-score
provenance trace can surface a SHA over the generator source.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-solver",
        action="store_true",
        help="skip gmsh + CalculiX execution; only re-write the fixture "
             "JSON from pre-existing solve.dat",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable,
        str(repo_root / "demo_modal_cantilever_pv" / "run_modal_e2e_demo.py"),
    ]
    if args.skip_solver:
        cmd.append("--skip-solver")
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(repo_root))


if __name__ == "__main__":
    sys.exit(main())
