#!/usr/bin/env python3
"""Export a Tier 1 reviewer bundle zip for N candidate cases (FM-04a Phase 4 C).

Tier 1 engineering candidate. Not signed validation. Not benchmark
agreement. Not a sealed FM-04b P8 packet.

Builds an in-memory zip from on-disk evidence and writes it to
``reports/<filename>``. Refuses output paths under ``golden_samples/**``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]


def _ensure_backend_path(repo_root: Path) -> None:
    backend = (repo_root / "backend").resolve()
    if backend.is_dir() and str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export a Tier 1 reviewer bundle zip for one or more candidate cases. "
            "Pull evidence from project_state/<case>/ and write the bundle under reports/."
        )
    )
    parser.add_argument(
        "--case-ids",
        required=True,
        help="Comma-separated list of candidate case ids.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output dir (defaults to reports/). Refuses golden_samples/** paths.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT_DEFAULT,
        help="Repository root.",
    )
    args = parser.parse_args(argv)

    case_ids = [tok.strip() for tok in args.case_ids.split(",") if tok.strip()]
    if not case_ids:
        print("error: --case-ids must include at least one case_id", file=sys.stderr)
        return 1

    _ensure_backend_path(args.repo_root)
    from app.api.routes.reviewer_bundle import (  # noqa: E402
        _build_inputs_for,
    )
    from app.services.reporting.reviewer_bundle import (  # noqa: E402
        build_reviewer_bundle,
        reviewer_bundle_filename,
    )

    inputs = []
    for case_id in case_ids:
        per_case = _build_inputs_for(case_id)
        if per_case.ballistic_metrics_path is None or not per_case.ballistic_metrics_path.is_file():
            print(
                f"error: ballistic_metrics.json not found for case {case_id!r} at "
                f"{per_case.ballistic_metrics_path}",
                file=sys.stderr,
            )
            return 1
        inputs.append(per_case)

    output_dir = args.output_dir or (args.repo_root / "reports")
    resolved = output_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "golden_samples":
            print(
                "error: reviewer bundle refuses writes under golden_samples/**; "
                "use reports/ or project_state/<...>/ instead",
                file=sys.stderr,
            )
            return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_bytes = build_reviewer_bundle(inputs, repo_root=args.repo_root)
    out_path = output_dir / reviewer_bundle_filename(len(case_ids))
    out_path.write_bytes(zip_bytes)
    print(f"reviewer bundle: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
