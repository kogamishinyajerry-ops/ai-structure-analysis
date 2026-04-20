"""CLI entrypoint for standalone Notion sync from control_plane_sync.json."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .notion_sync import NotionRunRegistrar

logger = logging.getLogger(__name__)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync a local control_plane_sync.json to the Notion task.",
    )
    parser.add_argument(
        "run_dir",
        type=Path,
        help="Path to a run directory containing control_plane_sync.json",
    )
    parser.add_argument(
        "--control-plane-config",
        default=str(Path(__file__).resolve().parents[3] / "config" / "well_harness_control_plane.yaml"),
        help="Path to the project-scoped control plane config file.",
    )
    return parser

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = build_parser().parse_args()

    sync_json_path = args.run_dir / "control_plane_sync.json"
    if not sync_json_path.exists():
        logger.error(f"Missing {sync_json_path}")
        sys.exit(1)

    try:
        sync_plan = json.loads(sync_json_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse {sync_json_path}: {e}")
        sys.exit(1)

    # run_id is typically the name of the run_dir
    run_id = args.run_dir.name
    
    registrar = NotionRunRegistrar.from_default_path(Path(args.control_plane_config))
    result = registrar.update_task_from_sync_plan(run_id, sync_plan)
    
    if result.attempted and result.success:
        logger.info(f"Successfully updated task for Run ID {run_id}")
    elif result.attempted and not result.success:
        logger.error(f"Failed to sync Notion: {result.error_message}")
        sys.exit(1)
    else:
        logger.warning(f"Notion sync skipped: {result.skipped_reason}")

if __name__ == "__main__":
    main()
