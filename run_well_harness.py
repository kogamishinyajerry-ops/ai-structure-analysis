#!/usr/bin/env python3
"""Local convenience entrypoint for the structure-analysis well-harness."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.well_harness.cli import main


if __name__ == "__main__":
    main()
