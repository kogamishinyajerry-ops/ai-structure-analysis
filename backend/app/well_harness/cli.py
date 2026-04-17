"""CLI entrypoint for the structure-analysis well-harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .executors import CalculixExecutor, ReplayExecutor
from .notion_sync import NotionRunRegistrar
from .task_runner import WellHarnessRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the structure-analysis well-harness on one or more golden samples.",
    )
    parser.add_argument("case_ids", nargs="+", help="Golden sample case ids, for example GS-001 GS-002")
    parser.add_argument(
        "--executor",
        choices=("replay", "calculix"),
        default="replay",
        help="Executor surface to use for the run",
    )
    parser.add_argument(
        "--control-plane-config",
        default=str(Path(__file__).resolve().parents[3] / "config" / "well_harness_control_plane.yaml"),
        help="Path to the project-scoped control plane config file.",
    )
    parser.add_argument(
        "--no-notion-sync",
        action="store_true",
        help="Skip automatic Notion registration for this batch.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    executor = ReplayExecutor() if args.executor == "replay" else CalculixExecutor()
    runner = WellHarnessRunner(executor=executor)
    run_records = runner.run_cases(args.case_ids)

    if not args.no_notion_sync:
        registrar = NotionRunRegistrar.from_default_path(Path(args.control_plane_config))
        sync_result = registrar.register_batch(
            run_records=run_records,
            invoked_command=_build_invoked_command(args.case_ids, args.executor),
            executor_mode=args.executor,
        )
        if sync_result.attempted and not sync_result.success:
            print(
                f"[well_harness] Notion sync failed: {sync_result.error_message}",
                file=sys.stderr,
            )
        elif not sync_result.attempted and sync_result.skipped_reason:
            print(
                f"[well_harness] Notion sync skipped: {sync_result.skipped_reason}",
                file=sys.stderr,
            )

    results = [record.to_dict() for record in run_records]
    print(json.dumps(results, ensure_ascii=False, indent=2))


def _build_invoked_command(case_ids: list[str], executor_mode: str) -> str:
    joined = " ".join(case_ids)
    return f"python3 run_well_harness.py {joined} --executor {executor_mode}"


if __name__ == "__main__":
    main()
