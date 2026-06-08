#!/usr/bin/env python
"""FM-04a Phase 5 C — Tier 1 cohort snapshot writer CLI.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Usage::

    python scripts/write_cohort_snapshot.py [--case GS-102-candidate ...]
                                            [--label 2026-05-16T180000Z]
                                            [--repo-root /path/to/repo]

The CLI re-renders the reviewer surface set for the requested cases
and freezes their bytes under ``reports/snapshots/<UTC>/``. If no
``--case`` arguments are supplied it scans ``golden_samples/`` and
picks every ``*-candidate`` directory. The CLI NEVER writes inside
``golden_samples/**`` (the writer asserts this), NEVER invokes a
solver, and NEVER touches signed-registry directories.

Each snapshot is a Tier 1 candidate capture only; the wording
``not signed validation`` / ``not benchmark agreement`` is preserved
in the SNAPSHOT_MANIFEST.json and every nested artifact.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _candidate_default_root() -> Path:
    return Path(__file__).resolve().parents[1]


_CANDIDATE_RE = re.compile(r"^GS-([A-Za-z0-9_-]+)-candidate$")


def _autodetect_cases(repo_root: Path) -> list[str]:
    golden = repo_root / "golden_samples"
    if not golden.is_dir():
        return []
    out: list[str] = []
    for entry in sorted(golden.iterdir()):
        if not entry.is_dir():
            continue
        if not _CANDIDATE_RE.fullmatch(entry.name):
            continue
        out.append(entry.name)
    return out


def _case_paths(repo_root: Path, case_id: str):
    from app.services.reporting.cohort_snapshot import SnapshotCaseInput

    case_dir = repo_root / "golden_samples" / case_id
    starter_deck = case_dir / "data" / "model_00_0000.rad"
    engine_deck = case_dir / "data" / "model_00_0001.rad"
    notes = case_dir / "NOTES.md"
    metrics = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    convergence = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    animation_manifest = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    result_mesh = (
        repo_root / "project_state" / "visualizations" / case_id / "result_mesh.json"
    )

    slug = (
        case_id.lower()
        .replace("gs-", "gs")
        .replace("-candidate", "")
        .replace("-", "_")
    )
    generator = repo_root / "scripts" / f"gen_{slug}_deck.py"

    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter_deck,
        engine_deck_path=engine_deck,
        ballistic_metrics_path=metrics,
        convergence_study_path=convergence,
        animation_manifest_path=animation_manifest,
        result_mesh_path=result_mesh,
        generator_script_path=generator,
        notes_path=notes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write a Tier 1 candidate cohort snapshot under "
            "reports/snapshots/<UTC>/. Tier 1 engineering candidate; "
            "not signed validation; not benchmark agreement."
        )
    )
    parser.add_argument(
        "--case",
        dest="cases",
        action="append",
        default=None,
        help=(
            "Case id to include (repeat for multiple). If omitted, "
            "auto-detects every *-candidate dir under golden_samples/."
        ),
    )
    parser.add_argument(
        "--label",
        dest="label",
        default=None,
        help="Override the UTC label (format YYYY-MM-DDTHHMMSSZ).",
    )
    parser.add_argument(
        "--repo-root",
        dest="repo_root",
        default=None,
        help="Override the repository root (defaults to this script's parent).",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else _candidate_default_root()
    backend_pkg = repo_root / "backend"
    if str(backend_pkg) not in sys.path:
        sys.path.insert(0, str(backend_pkg))

    from app.services.reporting.cohort_snapshot import write_cohort_snapshot

    case_ids = args.cases or _autodetect_cases(repo_root)
    if not case_ids:
        print(
            "no candidate cases found under golden_samples/*-candidate/; "
            "pass --case explicitly",
            file=sys.stderr,
        )
        return 2

    cases = [_case_paths(repo_root, cid) for cid in case_ids]
    result = write_cohort_snapshot(cases, repo_root=repo_root, snapshot_label=args.label)

    print(f"snapshot written: {result.snapshot_dir}")
    print(f"  label:   {result.snapshot_label}")
    print(f"  cases:   {len(case_ids)}")
    for member in result.members:
        print(f"  member:  {member}")
    print(
        "Tier 1 engineering candidate; not signed validation; "
        "not benchmark agreement"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
