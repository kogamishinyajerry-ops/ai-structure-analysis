"""CLI entrypoint for the structure-analysis well-harness.

Supports two calling conventions:
  Legacy (positional):  run-well-harness GS-001 GS-002 --executor replay
  Contract (subcommand): python -m well_harness.cli run --case GS-001 --pr-url https://...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .executors import CalculixExecutor, ReplayExecutor
from .notion_sync import NotionRunRegistrar
from .task_runner import WellHarnessRunner


# ---------------------------------------------------------------------------
# Shared arg helpers
# ---------------------------------------------------------------------------

def _add_shared_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments shared by legacy and 'run' sub-command."""
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
    parser.add_argument(
        "--github-pr-link",
        "--pr-url",           # Notion §3.5 contract alias
        dest="github_pr_link",
        default=None,
        help="GitHub PR URL to bind to the Notion records (alias: --pr-url).",
    )
    parser.add_argument(
        "--github-issue-link",
        default=None,
        help="Optional GitHub Issue URL to bind to the Notion records.",
    )


# ---------------------------------------------------------------------------
# Parser factory
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the structure-analysis well-harness on one or more golden samples.",
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    # ---- 'run' subcommand (Notion §3.5 contract) ---------------------------
    run_parser = subparsers.add_parser(
        "run",
        help="Run well-harness for a single case (Notion/GHA contract mode).",
    )
    run_parser.add_argument(
        "--case",
        required=True,
        dest="case_id",
        metavar="CASE_ID",
        help="Single Case ID to run, e.g. GS-001 or AI-FEA-P1-03.",
    )
    _add_shared_args(run_parser)

    # ---- Legacy positional (backwards compat) ------------------------------
    # When no subcommand is given, fall through to legacy positional mode.
    parser.add_argument(
        "case_ids",
        nargs="*",
        help="(Legacy) Golden sample case ids, e.g. GS-001 GS-002",
    )
    _add_shared_args(parser)

    return parser


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

def _run(case_ids: list[str], args: argparse.Namespace) -> None:
    executor = ReplayExecutor() if args.executor == "replay" else CalculixExecutor()
    runner = WellHarnessRunner(executor=executor)
    run_records = runner.run_cases(case_ids)

    if not args.no_notion_sync:
        registrar = NotionRunRegistrar.from_default_path(Path(args.control_plane_config))
        sync_result = registrar.register_batch(
            run_records=run_records,
            invoked_command=_build_invoked_command(case_ids, args.executor),
            executor_mode=args.executor,
            github_pr_link=args.github_pr_link,
            github_issue_link=args.github_issue_link,
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand == "run":
        # Notion §3.5 contract mode: single --case
        _run([args.case_id], args)
    elif args.case_ids:
        # Legacy positional mode
        _run(args.case_ids, args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
