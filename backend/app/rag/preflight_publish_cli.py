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
from typing import Any, Optional

from backend.app.rag import KnowledgeBase, MemoryVectorStore, MockEmbedder
from backend.app.rag.preflight_publish import publish_preflight
from backend.app.rag.preflight_summary import combine
from backend.app.rag.reviewer_advisor import FAULT_QUERY_SEEDS, advise
from backend.app.rag.sources import ALL_SOURCES


# Minimal hint duck-type. Matches preflight_summary.combine's contract.
@dataclass(frozen=True)
class _CliQuantity:
    name: str
    value: float
    unit: str
    confidence: str = "low"
    location: Optional[str] = None


@dataclass(frozen=True)
class _CliHint:
    case_id: str
    provider: str
    quantities: list
    notes: str = ""


def _load_hint_from_json(path: Path) -> _CliHint:
    """Load a hint JSON into a _CliHint object. Raises SystemExit on shape errors."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"[publish-rag] failed to read --hint-json {path}: {e}") from e
    if not isinstance(data, dict):
        raise SystemExit(f"[publish-rag] --hint-json {path}: expected JSON object")

    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise SystemExit("[publish-rag] --hint-json: 'case_id' (non-empty str) required")
    provider = data.get("provider", "manual@v0")
    notes = data.get("notes", "") or ""
    raw_qs = data.get("quantities", []) or []
    if not isinstance(raw_qs, list):
        raise SystemExit("[publish-rag] --hint-json: 'quantities' must be a list")

    quantities: list[_CliQuantity] = []
    for i, q in enumerate(raw_qs):
        if not isinstance(q, dict):
            raise SystemExit(f"[publish-rag] --hint-json: quantities[{i}] must be an object")
        name = q.get("name")
        value = q.get("value")
        unit = q.get("unit")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"[publish-rag] --hint-json: quantities[{i}].name required")
        if not isinstance(value, (int, float)):
            raise SystemExit(
                f"[publish-rag] --hint-json: quantities[{i}].value must be a number"
            )
        if not isinstance(unit, str):
            raise SystemExit(f"[publish-rag] --hint-json: quantities[{i}].unit required")
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
    parser.add_argument("--pr", type=int, default=None, help="PR/Issue number (required for --post)")
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

    args = parser.parse_args(argv[1:])

    # --post + --dry-run is contradictory
    if args.post and args.dry_run:
        print("[publish-rag] --post and --dry-run are mutually exclusive", file=sys.stderr)
        return 2

    if args.k <= 0:
        print("[publish-rag] --k must be a positive integer", file=sys.stderr)
        return 2

    if args.fault not in FAULT_QUERY_SEEDS:
        print(
            f"[publish-rag] note: fault '{args.fault}' not in FAULT_QUERY_SEEDS; "
            f"falling back to generic query.",
            file=sys.stderr,
        )

    # Build hint
    if args.hint_json is not None:
        hint = _load_hint_from_json(args.hint_json)
    else:
        hint = _CliHint(case_id=args.case_id, provider="advisor-only@v0", quantities=[])

    # Build KB + advice
    kb = _build_kb(args.root)
    advice = advise(
        kb,
        verdict=args.verdict,
        fault_class=args.fault,
        k=args.k,
        source_filter=args.source_filter,
    )

    # Combine
    summary = combine(hint, advice, max_advice_lines=args.max_advice_lines)

    # Dry-run path (default unless --post)
    is_dry = args.dry_run or not args.post
    if is_dry:
        print(f"[publish-rag] mode: DRY-RUN ({'forced' if args.dry_run else '--post not set'})")
        print(f"[publish-rag] verdict: {args.verdict!r}  fault: {args.fault!r}")
        print(f"[publish-rag] case_id: {summary.case_id}  confidence: {summary.confidence_indicator}")
        print(f"[publish-rag] advice hits: {len(summary.advice_lines)}")
        print()
        print("--- markdown ---")
        print(summary.markdown)
        print("--- end markdown ---")
        return 0

    # Real publish
    if not args.repo or not args.pr:
        print("[publish-rag] --post requires --repo and --pr", file=sys.stderr)
        return 2

    result = publish_preflight(
        summary,
        repo=args.repo,
        pr_number=args.pr,
        mode=args.mode,
        header_marker=args.header_marker,
    )

    print(f"[publish-rag] verdict: {args.verdict!r}  fault: {args.fault!r}")
    print(f"[publish-rag] target: {args.repo}#{args.pr}  mode: {args.mode}")
    if result.summary_was_empty:
        print(f"[publish-rag] skipped: {result.error}")
        return 0
    if result.posted:
        print(f"[publish-rag] {result.action}: {result.comment_url}")
        return 0
    print(f"[publish-rag] failed: status={result.status_code} error={result.error}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
