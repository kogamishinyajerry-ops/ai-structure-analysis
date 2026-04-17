#!/usr/bin/env python3
"""Reconcile Notion approval decisions back into well_harness session rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.well_harness.notion_sync import NotionRunRegistrar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile task approval decisions back into project-scoped Notion session rows.",
    )
    parser.add_argument(
        "--control-plane-config",
        default=str(REPO_ROOT / "config" / "well_harness_control_plane.yaml"),
        help="Path to the project-scoped control plane config file.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional batch id to reconcile. Defaults to all non-closed sessions.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    registrar = NotionRunRegistrar.from_default_path(Path(args.control_plane_config))
    result = registrar.reconcile_session_approval_status(batch_id=args.batch_id)
    print(
        json.dumps(
            {
                "attempted": result.attempted,
                "success": result.success,
                "processed_sessions": result.processed_sessions,
                "updated_session_ids": result.updated_session_ids,
                "skipped_reason": result.skipped_reason,
                "error_message": result.error_message,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if result.attempted and not result.success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
