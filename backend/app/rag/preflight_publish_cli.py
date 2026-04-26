"""RAG preflight publish CLI — verdict-driven preflight comment to a PR (P1-08).

Fourth sibling of the RAG operator CLIs:

    1. backend.app.rag.cli              — ingest
    2. backend.app.rag.query_cli        — query
    3. backend.app.rag.advise_cli       — advise
    4. backend.app.rag.preflight_publish_cli   — publish (this module)

Wraps:
    advise(...) → ReviewerAdvice
        → combine(hint, advice) → PreflightSummary
            → publish_preflight(...) → PublishResult

Usage:
    # Dry-run (default; prints markdown, never touches GitHub)
    python3 -m backend.app.rag.preflight_publish_cli \\
        --verdict Reject --fault solver_convergence

    # Actually post a comment (requires GH_TOKEN / gh auth)
    python3 -m backend.app.rag.preflight_publish_cli \\
        --verdict Reject --fault solver_convergence \\
        --repo owner/name --pr 42 --post

    # Upsert (PATCH prior preflight comment if found)
    python3 -m backend.app.rag.preflight_publish_cli \\
        --verdict Reject --fault solver_convergence \\
        --repo owner/name --pr 42 --post --mode upsert

Hint sourcing:
    This CLI does NOT call predict_for_simplan() — that requires a full
    SimPlan, which is heavy for ad-hoc preflight checks. Instead:

      * Default: empty hint (advisor-only preflight; no surrogate quantities)
      * --hint-json <path>: load a JSON file with the hint shape:
          {
            "case_id": "GS-001",
            "provider": "manual@v0",
            "quantities": [
              {"name": "max_displacement", "value": 1.234, "unit": "mm",
               "confidence": "low", "location": "free_end"}
            ],
            "notes": "manual sketch"
          }

Exit codes:
    0 — preflight built; POST/upsert succeeded, or --dry-run completed
    1 — preflight built but POST/upsert failed (transport / auth / 4xx)
    2 — usage error (missing args, invalid JSON, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
from backend.app.rag.preflight_publish import _REPO_RE, publish_preflight
from backend.app.rag.preflight_summary import combine
from backend.app.rag.reviewer_advisor import FAULT_QUERY_SEEDS, advise
from backend.app.rag.sources import ALL_SOURCES


class _UsageError(SystemExit):
    """Pre-emptive R2 (mirrors query_cli / advise_cli): exit code 2 for
    usage / fatal CLI errors. Plain `SystemExit("msg")` exits with code
    1, conflicting with the docstring's `2 = usage error` contract.
    """

    def __init__(self, message: str) -> None:
        super().__init__(2)
        self.message = message


# Pre-emptive R2: cap --hint-json read size. A maliciously large JSON
# would otherwise OOM the CLI before json.loads gets a chance to fail.
# 1 MiB is far above any realistic preflight hint payload (~hundreds
# of bytes typical).
_HINT_JSON_MAX_BYTES = 1 * 1024 * 1024


# Minimal hint duck-type. Matches preflight_summary.combine's contract.
@dataclass(frozen=True)
class _CliQuantity:
    name: str
    value: float
    unit: str
    confidence: str = "low"
    location: str | None = None


@dataclass(frozen=True)
class _CliHint:
    case_id: str
    provider: str
    quantities: list
    notes: str = ""


def _load_hint_from_json(path: Path) -> _CliHint:
    """Load a hint JSON into a _CliHint object.

    Raises `_UsageError` (rc=2) on missing file / invalid JSON / shape
    errors. Pre-emptive R2: bool-vs-int discrimination on `value`,
    file-size cap before read, plain SystemExit replaced with
    _UsageError so the documented `2 = usage error` rc contract holds.
    """
    try:
        # Pre-emptive R2: stat-then-read to fail fast on oversize hints
        # without buffering them into memory first.
        size = path.stat().st_size
        if size > _HINT_JSON_MAX_BYTES:
            raise _UsageError(f"--hint-json {path}: file is {size} bytes (>{_HINT_JSON_MAX_BYTES})")
        data = json.loads(path.read_text())
    except _UsageError:
        raise
    except (OSError, json.JSONDecodeError) as e:
        raise _UsageError(f"failed to read --hint-json {path}: {e}") from e
    if not isinstance(data, dict):
        raise _UsageError(f"--hint-json {path}: expected JSON object")

    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise _UsageError("--hint-json: 'case_id' (non-empty str) required")
    provider = data.get("provider", "manual@v0")
    # R2 (post Codex R2 LOW on PR #66): mirror the `quantities`
    # pattern — only missing / null is silently empty; any other
    # non-str type raises rather than silently dropping the value.
    if "notes" not in data or data.get("notes") is None:
        notes = ""
    elif isinstance(data["notes"], str):
        notes = data["notes"]
    else:
        raise _UsageError(
            f"--hint-json: 'notes' must be a string, got {type(data['notes']).__name__}"
        )
    # R2 (post Codex R1 MEDIUM-1 on PR #66): the prior code did
    # `data.get("quantities", []) or []` which coerced "", 0, False,
    # {} and None all into [] silently — invalid hint payloads were
    # accepted as "no quantities". Treat only missing/None as empty;
    # everything else must pass the type check below.
    if "quantities" not in data or data.get("quantities") is None:
        raw_qs = []
    else:
        raw_qs = data["quantities"]
    if not isinstance(raw_qs, list):
        raise _UsageError(f"--hint-json: 'quantities' must be a list, got {type(raw_qs).__name__}")

    quantities: list[_CliQuantity] = []
    for i, q in enumerate(raw_qs):
        if not isinstance(q, dict):
            raise _UsageError(f"--hint-json: quantities[{i}] must be an object")
        name = q.get("name")
        value = q.get("value")
        unit = q.get("unit")
        if not isinstance(name, str) or not name:
            raise _UsageError(f"--hint-json: quantities[{i}].name required")
        # Pre-emptive R2 (mirrors PR #65 _is_positive_int pattern): bool
        # is a subclass of int, but `value=True` here is almost certainly
        # a JSON typo. Reject explicitly.
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise _UsageError(f"--hint-json: quantities[{i}].value must be a number")
        if not isinstance(unit, str):
            raise _UsageError(f"--hint-json: quantities[{i}].unit required")
        quantities.append(
            _CliQuantity(
                name=name,
                value=float(value),
                unit=unit,
                confidence=q.get("confidence", "low") or "low",
                location=q.get("location"),
            )
        )

    return _CliHint(case_id=case_id, provider=provider, quantities=quantities, notes=notes)


def _build_kb(root: Path) -> KnowledgeBase:
    kb = KnowledgeBase(MockEmbedder(dim=32), MemoryVectorStore())
    for _label, iter_fn in ALL_SOURCES:
        docs = list(iter_fn(root))
        if docs:
            kb.ingest(docs)
    return kb


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Publish a preflight comment on a GitHub PR.")
    parser.add_argument("--verdict", required=True, help="Reviewer verdict (e.g. Reject)")
    parser.add_argument(
        "--fault",
        default="unknown",
        help="FaultClass value (e.g. solver_convergence); default: unknown",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Top-k corpus chunks pulled by the advisor (default: 5)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repo root for in-memory mock ingest",
    )
    parser.add_argument(
        "--source-filter",
        default=None,
        help="Restrict advisor to one source label (e.g. project-adr-fp)",
    )
    parser.add_argument(
        "--hint-json",
        type=Path,
        default=None,
        help="JSON file with a hint shape (case_id, provider, quantities, notes); "
        "default: empty hint (advisor-only)",
    )
    parser.add_argument(
        "--case-id",
        default="<unknown-case>",
        help="Fallback case_id if --hint-json not provided (default: <unknown-case>)",
    )
    parser.add_argument("--repo", default=None, help="GitHub owner/repo (required for --post)")
    parser.add_argument(
        "--pr", type=int, default=None, help="PR/Issue number (required for --post)"
    )
    parser.add_argument(
        "--mode",
        choices=["post", "upsert"],
        default="post",
        help="Publish mode (default: post; upsert PATCHes prior preflight comment)",
    )
    parser.add_argument(
        "--header-marker",
        default="<!-- ai-fea-preflight -->",
        help="Marker prepended to body for upsert detection",
    )
    parser.add_argument(
        "--max-advice-lines",
        type=int,
        default=3,
        help="Cap advice lines in the rendered preflight (default: 3, 0 = no cap)",
    )
    parser.add_argument(
        "--post",
        action="store_true",
        help="Actually post to GitHub. Without this flag, --dry-run is implied.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered markdown to stdout; do not POST. (default if --post not set)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one JSON record on stdout (suitable for piping). "
        "Compatible with both dry-run and --post.",
    )

    args = parser.parse_args(argv[1:])

    # --post + --dry-run is contradictory
    if args.post and args.dry_run:
        print("[publish-rag] --post and --dry-run are mutually exclusive", file=sys.stderr)
        return 2

    if args.k <= 0:
        print("[publish-rag] --k must be a positive integer", file=sys.stderr)
        return 2

    # Pre-emptive R2: --max-advice-lines < 0 raises ValueError inside
    # combine(). Pre-validate to surface as rc=2 (usage error) instead
    # of a leaked traceback / rc=1.
    if args.max_advice_lines < 0:
        print(
            "[publish-rag] --max-advice-lines must be >= 0 (0 = no cap)",
            file=sys.stderr,
        )
        return 2

    if args.fault not in FAULT_QUERY_SEEDS:
        print(
            f"[publish-rag] note: fault '{args.fault}' not in FAULT_QUERY_SEEDS; "
            f"falling back to generic query.",
            file=sys.stderr,
        )

    # Build hint
    # Pre-emptive R2: catch _UsageError so main() honors the
    # documented `2 = usage error` rc contract whether main() is
    # invoked via __main__ (which also wraps) or via tests.
    if args.hint_json is not None:
        try:
            hint = _load_hint_from_json(args.hint_json)
        except _UsageError as e:
            print(f"[publish-rag] {e.message}", file=sys.stderr)
            return 2
    else:
        hint = _CliHint(case_id=args.case_id, provider="advisor-only@v0", quantities=[])

    # Build KB + advice
    # R2 (post Codex R1 HIGH on PR #66): wrap _build_kb so a malformed
    # corpus under --root (duplicate doc_ids, symlink-escape, OSError)
    # surfaces as rc=2 instead of leaking a traceback / rc=1. Mirrors
    # advise_cli's mock-path translator.
    try:
        kb = _build_kb(args.root)
    except (ValueError, OSError) as e:
        print(
            f"[publish-rag] corpus ingest failed against --root {args.root}: {e}", file=sys.stderr
        )
        return 2
    # Pre-emptive R2 (mirrors advise_cli pattern, post Codex R1 on PR
    # #62): advise() re-validates verdict / k / source_filter and raises
    # ValueError on any mismatch. Translate to rc=2 instead of leaking
    # a traceback.
    try:
        advice = advise(
            kb,
            verdict=args.verdict,
            fault_class=args.fault,
            k=args.k,
            source_filter=args.source_filter,
        )
    except ValueError as e:
        print(f"[publish-rag] {e}", file=sys.stderr)
        return 2

    # Combine
    summary = combine(hint, advice, max_advice_lines=args.max_advice_lines)

    # Dry-run path (default unless --post)
    is_dry = args.dry_run or not args.post
    if is_dry:
        if args.json:
            print(
                json.dumps(
                    {
                        "mode": "dry-run",
                        "dry_run_reason": "forced" if args.dry_run else "--post not set",
                        "verdict": args.verdict,
                        "fault": args.fault,
                        "case_id": summary.case_id,
                        "confidence_indicator": summary.confidence_indicator,
                        "quantity_count": len(summary.quantity_lines),
                        "advice_hit_count": len(summary.advice_lines),
                        "markdown": summary.markdown,
                    }
                )
            )
            return 0
        print(f"[publish-rag] mode: DRY-RUN ({'forced' if args.dry_run else '--post not set'})")
        print(f"[publish-rag] verdict: {args.verdict!r}  fault: {args.fault!r}")
        print(
            f"[publish-rag] case_id: {summary.case_id}  confidence: {summary.confidence_indicator}"
        )
        print(f"[publish-rag] advice hits: {len(summary.advice_lines)}")
        print()
        print("--- markdown ---")
        print(summary.markdown)
        print("--- end markdown ---")
        return 0

    # Real publish — distinguish missing-arg (rc=2) from malformed-arg (rc=2).
    # R2 (post Codex R1 MEDIUM-2 on PR #66): pre-fix used `not args.pr`
    # which conflated `--pr 0` (invalid) and `--pr` missing into the
    # same generic message. Also missing repo-shape and empty
    # header-marker for upsert pre-validation — both fell through to
    # publish_preflight as rc=1.
    if args.repo is None or args.pr is None:
        print("[publish-rag] --post requires --repo and --pr", file=sys.stderr)
        return 2

    # Pre-validate repo shape with the same _REPO_RE that
    # publish_preflight uses, so a malformed repo (whitespace,
    # "owneronly", path-traversal) surfaces as rc=2 instead of rc=1.
    if not args.repo.strip() or not _REPO_RE.match(args.repo):
        print(
            f"[publish-rag] --repo malformed: {args.repo!r} (expected owner/name)",
            file=sys.stderr,
        )
        return 2

    # Mirrors PR #65 _is_positive_int: --pr 0 / negative is now distinct
    # from "missing" above.
    if args.pr <= 0:
        print(f"[publish-rag] --pr must be a positive integer, got {args.pr}", file=sys.stderr)
        return 2

    # Upsert mode requires a non-empty header_marker (publish_preflight
    # also enforces this; pull-forward to rc=2).
    if args.mode == "upsert" and not args.header_marker:
        print(
            "[publish-rag] --mode upsert requires a non-empty --header-marker",
            file=sys.stderr,
        )
        return 2

    result = publish_preflight(
        summary,
        repo=args.repo,
        pr_number=args.pr,
        mode=args.mode,
        header_marker=args.header_marker,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "mode": "post",
                    "verdict": args.verdict,
                    "fault": args.fault,
                    "case_id": summary.case_id,
                    "target": f"{args.repo}#{args.pr}",
                    "publish_mode": args.mode,
                    "posted": result.posted,
                    "action": result.action,
                    "comment_url": result.comment_url,
                    "status_code": result.status_code,
                    "error": result.error,
                    "summary_was_empty": result.summary_was_empty,
                }
            )
        )
        if result.summary_was_empty:
            return 0
        if result.posted:
            return 0
        return 1

    print(f"[publish-rag] verdict: {args.verdict!r}  fault: {args.fault!r}")
    print(f"[publish-rag] target: {args.repo}#{args.pr}  mode: {args.mode}")
    if result.summary_was_empty:
        print(f"[publish-rag] skipped: {result.error}")
        return 0
    if result.posted:
        print(f"[publish-rag] {result.action}: {result.comment_url}")
        return 0
    # R2 (post Codex R1 LOW on PR #66): publish failures go to stderr
    # to keep the stdout/stderr split clean for piping / monitoring.
    print(
        f"[publish-rag] failed: status={result.status_code} error={result.error}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except _UsageError as e:
        print(f"[publish-rag] {e.message}", file=sys.stderr)
        sys.exit(2)
