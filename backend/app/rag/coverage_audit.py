"""RAG corpus coverage audit — verify every expected disk file is ingested (P1-04b).

Walks the repo for files the registered sources are *supposed* to ingest,
runs `ALL_SOURCES`, and cross-references. Reports missing-coverage and
extra-coverage so silent corpus rot (a 5th source landing without
catching all its files, or a renamed file that no longer matches the
ingest filter) shows up loudly.

Pure-additive script — no agent rewiring, no HF1 zones touched. Useful
both as a CI gate (exit 1 on missing coverage) and as an interactive
report (print summary).

Usage:
    python3 -m backend.app.rag.coverage_audit
    python3 -m backend.app.rag.coverage_audit --root /path/to/repo
    python3 -m backend.app.rag.coverage_audit --json     # machine-readable
    python3 -m backend.app.rag.coverage_audit --strict   # missing → exit 1

Exit codes:
    0 — every expected file is covered (and --strict satisfied if used)
    1 — missing coverage (or --strict + extras)
    2 — usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from backend.app.rag.sources import ALL_SOURCES


class _UsageError(SystemExit):
    """Mirrors the pattern in `backend.app.rag.cli`, `query_cli`,
    `advise_cli`: exit code 2 for usage / fatal errors with a
    user-facing message attribute. Plain `SystemExit("msg")` exits
    with code 1, conflicting with the docstring's
    `2 = usage error` contract.
    """

    def __init__(self, message: str) -> None:
        super().__init__(2)
        self.message = message


# ---------------------------------------------------------------------------
# Disk discovery — what the registry SHOULD have ingested
# ---------------------------------------------------------------------------


def _discover_adr_files(repo_root: Path) -> list[Path]:
    adr_dir = repo_root / "docs" / "adr"
    if not adr_dir.is_dir():
        return []
    return sorted(p for p in adr_dir.glob("ADR-*.md") if p.is_file())


def _discover_fp_files(repo_root: Path) -> list[Path]:
    fp_dir = repo_root / "docs" / "failure_patterns"
    if not fp_dir.is_dir():
        return []
    return sorted(p for p in fp_dir.glob("FP-*.md") if p.is_file())


def _discover_gs_readmes(repo_root: Path) -> list[Path]:
    gs_dir = repo_root / "golden_samples"
    if not gs_dir.is_dir():
        return []
    out: list[Path] = []
    for sample in sorted(gs_dir.glob("GS-*")):
        if not sample.is_dir():
            continue
        readme = sample / "README.md"
        if readme.is_file():
            out.append(readme)
    return out


def _discover_gs_theory_scripts(repo_root: Path) -> list[Path]:
    """Mirrors gs_theory._is_theory_script: *.py whose lowercase name
    contains one of theory / theoretical / analytical."""
    gs_dir = repo_root / "golden_samples"
    if not gs_dir.is_dir():
        return []
    out: list[Path] = []
    for sample in sorted(gs_dir.glob("GS-*")):
        if not sample.is_dir():
            continue
        for py in sorted(sample.glob("*.py")):
            name = py.name.lower()
            if any(tok in name for tok in ("theory", "theoretical", "analytical")):
                out.append(py)
    return out


# ---------------------------------------------------------------------------
# Audit data shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoverageBucket:
    """Per-bucket coverage report."""

    name: str
    expected_files: tuple[str, ...]
    covered_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    extra_files: tuple[str, ...]

    def is_clean(self) -> bool:
        return not self.missing_files and not self.extra_files

    def has_missing(self) -> bool:
        return len(self.missing_files) > 0


@dataclass(frozen=True)
class CoverageReport:
    """Whole-repo coverage report."""

    repo_root: str
    buckets: tuple[CoverageBucket, ...] = field(default_factory=tuple)

    def total_expected(self) -> int:
        return sum(len(b.expected_files) for b in self.buckets)

    def total_covered(self) -> int:
        return sum(len(b.covered_files) for b in self.buckets)

    def total_missing(self) -> int:
        return sum(len(b.missing_files) for b in self.buckets)

    def total_extra(self) -> int:
        return sum(len(b.extra_files) for b in self.buckets)

    def all_clean(self) -> bool:
        return all(b.is_clean() for b in self.buckets)

    def any_missing(self) -> bool:
        return any(b.has_missing() for b in self.buckets)


# ---------------------------------------------------------------------------
# Core audit
# ---------------------------------------------------------------------------


def _doc_paths_for_source(source_label: str, repo_root: Path) -> set[str]:
    """Run the registry's iter fn for `source_label` and collect doc.metadata['path']
    values, normalised to repo-relative POSIX paths."""
    paths: set[str] = set()
    matched = [(lbl, fn) for (lbl, fn) in ALL_SOURCES if lbl == source_label]
    if not matched:
        return paths
    _, iter_fn = matched[0]
    for d in iter_fn(repo_root):
        meta = d.metadata or {}
        raw = meta.get("path")
        if isinstance(raw, str) and raw:
            paths.add(_normalise_to_relpath(raw, repo_root))
    return paths


def _normalise_to_relpath(raw: str, repo_root: Path) -> str:
    """Turn doc metadata 'path' into a repo-relative POSIX path."""
    p = Path(raw)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()  # outside repo root — keep verbatim
    return p.as_posix()


def _expected_relpaths(files: list[Path], repo_root: Path) -> list[str]:
    return [
        f.resolve().relative_to(repo_root.resolve()).as_posix() if f.is_absolute() else f.as_posix()
        for f in files
    ]


def audit_coverage(repo_root: Path) -> CoverageReport:
    """Walk disk + registry; produce a structured CoverageReport.

    Raises `ValueError` / `OSError` only if a registered source iterator
    raises one of those (e.g. duplicate doc_id, symlink escape from
    `iter_governance_documents`). Callers (the CLI) translate those
    into rc=2 to honor the documented exit-code contract.
    """
    repo_root = Path(repo_root)

    project_adr_fp_paths = _doc_paths_for_source("project-adr-fp", repo_root)
    gs_theory_paths = _doc_paths_for_source("gs-theory", repo_root)

    adr_expected = _expected_relpaths(_discover_adr_files(repo_root), repo_root)
    fp_expected = _expected_relpaths(_discover_fp_files(repo_root), repo_root)
    gs_readme_expected = _expected_relpaths(_discover_gs_readmes(repo_root), repo_root)
    gs_theory_expected = _expected_relpaths(_discover_gs_theory_scripts(repo_root), repo_root)

    # Per-source extras: paths the source emitted that are not in
    # ANY of its bucket's expected sets.
    project_adr_fp_expected_all = set(adr_expected) | set(fp_expected)
    gs_theory_expected_all = set(gs_readme_expected) | set(gs_theory_expected)

    project_extras = sorted(project_adr_fp_paths - project_adr_fp_expected_all)
    gs_extras = sorted(gs_theory_paths - gs_theory_expected_all)

    # Distribute extras to the bucket whose name matches the file's parent
    # heuristically: ADR files live in docs/adr/, FP in docs/failure_patterns/,
    # GS readmes are README.md, theory scripts end in .py.
    def _is_adr_path(p: str) -> bool:
        return p.startswith("docs/adr/")

    def _is_fp_path(p: str) -> bool:
        return p.startswith("docs/failure_patterns/")

    def _is_gs_readme_path(p: str) -> bool:
        return p.startswith("golden_samples/") and p.endswith("README.md")

    def _is_gs_theory_path(p: str) -> bool:
        return p.startswith("golden_samples/") and p.endswith(".py")

    adr_extras = tuple(sorted(p for p in project_extras if _is_adr_path(p)))
    fp_extras = tuple(sorted(p for p in project_extras if _is_fp_path(p)))
    gs_readme_extras = tuple(sorted(p for p in gs_extras if _is_gs_readme_path(p)))
    gs_theory_extras = tuple(sorted(p for p in gs_extras if _is_gs_theory_path(p)))

    adr_bucket = CoverageBucket(
        name="adr",
        expected_files=tuple(sorted(adr_expected)),
        covered_files=tuple(sorted(set(adr_expected) & project_adr_fp_paths)),
        missing_files=tuple(sorted(set(adr_expected) - project_adr_fp_paths)),
        extra_files=adr_extras,
    )
    fp_bucket = CoverageBucket(
        name="fp",
        expected_files=tuple(sorted(fp_expected)),
        covered_files=tuple(sorted(set(fp_expected) & project_adr_fp_paths)),
        missing_files=tuple(sorted(set(fp_expected) - project_adr_fp_paths)),
        extra_files=fp_extras,
    )
    gs_readme_bucket = CoverageBucket(
        name="gs-readme",
        expected_files=tuple(sorted(gs_readme_expected)),
        covered_files=tuple(sorted(set(gs_readme_expected) & gs_theory_paths)),
        missing_files=tuple(sorted(set(gs_readme_expected) - gs_theory_paths)),
        extra_files=gs_readme_extras,
    )
    gs_theory_bucket = CoverageBucket(
        name="gs-theory",
        expected_files=tuple(sorted(gs_theory_expected)),
        covered_files=tuple(sorted(set(gs_theory_expected) & gs_theory_paths)),
        missing_files=tuple(sorted(set(gs_theory_expected) - gs_theory_paths)),
        extra_files=gs_theory_extras,
    )

    return CoverageReport(
        repo_root=str(repo_root),
        buckets=(adr_bucket, fp_bucket, gs_readme_bucket, gs_theory_bucket),
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def report_to_dict(report: CoverageReport) -> dict:
    """JSON-serialisable rendering."""
    return {
        "repo_root": report.repo_root,
        "summary": {
            "expected": report.total_expected(),
            "covered": report.total_covered(),
            "missing": report.total_missing(),
            "extra": report.total_extra(),
            "all_clean": report.all_clean(),
        },
        "buckets": [
            {
                "name": b.name,
                "expected": list(b.expected_files),
                "covered": list(b.covered_files),
                "missing": list(b.missing_files),
                "extra": list(b.extra_files),
            }
            for b in report.buckets
        ],
    }


def _render_text(report: CoverageReport) -> str:
    lines: list[str] = []
    lines.append(f"[coverage-audit] root: {report.repo_root}")
    lines.append("")
    for b in report.buckets:
        status = "clean" if b.is_clean() else ("MISSING" if b.has_missing() else "extras")
        lines.append(
            f"  [{b.name:10s}] expected={len(b.expected_files):3d}  "
            f"covered={len(b.covered_files):3d}  "
            f"missing={len(b.missing_files):3d}  "
            f"extra={len(b.extra_files):3d}  [{status}]"
        )
        for m in b.missing_files:
            lines.append(f"      - MISSING: {m}")
        for x in b.extra_files:
            lines.append(f"      - EXTRA  : {x}")
    lines.append("")
    lines.append(
        f"[coverage-audit] TOTAL: expected={report.total_expected()} "
        f"covered={report.total_covered()} "
        f"missing={report.total_missing()} "
        f"extra={report.total_extra()}"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="RAG corpus coverage audit.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repo root (default: this repo)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable text",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat 'extras' as failures too (default: only missing fails)",
    )
    args = parser.parse_args(argv[1:])

    if not args.root.is_dir():
        print(f"[coverage-audit] root is not a directory: {args.root}", file=sys.stderr)
        return 2

    # Translate corpus-integrity failures (duplicate doc_id, symlink
    # escape, malformed frontmatter) from the registered iter functions
    # into rc=2 + single stderr line. Mirrors backend.app.rag.cli and
    # advise_cli; without it, audit_coverage would leak a traceback and
    # exit 1, contradicting the documented exit-code contract.
    try:
        report = audit_coverage(args.root)
    except (ValueError, OSError) as e:
        print(
            f"[coverage-audit] corpus iteration failed against --root {args.root}: {e}",
            file=sys.stderr,
        )
        return 2

    if args.json:
        print(json.dumps(report_to_dict(report), indent=2))
    else:
        print(_render_text(report))

    if report.any_missing():
        return 1
    if args.strict and report.total_extra() > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
