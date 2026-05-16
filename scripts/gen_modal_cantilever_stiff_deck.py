"""Re-generate the modal-cantilever-stiff-candidate fixture artefacts.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Mirrors ``scripts/gen_modal_cantilever_deck.py`` against the stiffer
75 × 75 mm cross-section variant.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-solver", action="store_true")
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parent.parent
    cmd = [
        sys.executable,
        str(repo_root / "demo_modal_cantilever_stiff" / "run_modal_e2e_demo.py"),
    ]
    if args.skip_solver:
        cmd.append("--skip-solver")
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(repo_root))


if __name__ == "__main__":
    sys.exit(main())
