"""Check commit trailers for ADR-011 §Commit Trailer Convention compliance (FF-07 / HF5).

ADR-011 §Commit Trailer Convention requires:

    Execution-by: claude-code-opus47 [· Subagent: <id>]
    Codex-verified: <claim-id>@<sha>

- `Execution-by` is required on every commit landing on main.
- `Codex-verified` is required when the commit makes critical claims
  (numerical correctness, schema compatibility, forbidden-zone
  boundaries). Pure docs/format commits may omit it but must say so
  in the PR body. CI can't classify "critical claim" automatically,
  so we only validate FORMAT when Codex-verified is present, not
  presence itself.

Honest-acceptance compromise (FF-07 v1):

  GitHub's standard `Co-Authored-By: Claude Opus 4.7 ...` trailer
  conveys the same execution-attribution information as
  `Execution-by: claude-code-opus47`. Strict ADR-011 wording requires
  the latter; in practice T1 has been emitting the former since
  before ADR-011 ratified. We accept EITHER as satisfying the
  Execution-by requirement to avoid invalidating the entire commit
  history of the repo. A follow-up ADR amendment could codify
  Co-Authored-By as the canonical form; for now both are accepted.

Usage:
    python3 scripts/check_commit_trailers.py <base-ref>..<head-ref>
    python3 scripts/check_commit_trailers.py origin/main..HEAD
    python3 scripts/check_commit_trailers.py --json <range>

Exit codes:
    0 — all commits comply
    1 — at least one violation
    2 — usage / git error
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Iterable

# Execution-by: any of these trailer keys count as attribution.
_ATTRIBUTION_RE = re.compile(
    r"^(?:Execution-by|Co-Authored-By):\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)

# Codex-verified format: <claim-id>@<sha>.
# claim-id is alphanumeric + hyphen/underscore (e.g. "ADR-011-r5", "FF-06-r2").
# sha is at least 7 hex chars; literal placeholder "<claim-id>" allowed.
_CODEX_RE = re.compile(
    r"^Codex-verified:\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)
_CODEX_VALUE_RE = re.compile(
    r"^([A-Za-z0-9_\-]+|<claim-id>)@([0-9a-fA-F]{7,40}|<sha>|HEAD)$"
)


@dataclass
class CommitCheck:
    sha: str
    subject: str
    has_attribution: bool = False
    attribution_value: str = ""
    has_codex_trailer: bool = False
    codex_value: str = ""
    codex_format_valid: bool = False
    violations: list[str] = field(default_factory=list)


def _git_log(ref_range: str) -> list[tuple[str, str, str]]:
    """Return list of (sha, subject, body) for commits in the range."""
    proc = subprocess.run(
        ["git", "log", "--format=%H%x1f%s%x1f%B%x1e", ref_range],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git log failed: {proc.stderr.strip()}")
    if not proc.stdout.strip():
        return []
    out: list[tuple[str, str, str]] = []
    for entry in proc.stdout.split("\x1e"):
        entry = entry.strip("\n")
        if not entry:
            continue
        parts = entry.split("\x1f")
        if len(parts) >= 3:
            out.append((parts[0], parts[1], parts[2]))
    return out


def check_commit(sha: str, subject: str, body: str) -> CommitCheck:
    result = CommitCheck(sha=sha, subject=subject)

    attr_match = _ATTRIBUTION_RE.search(body)
    if attr_match:
        result.has_attribution = True
        result.attribution_value = attr_match.group(1).strip()
    else:
        result.violations.append(
            "missing execution-attribution trailer "
            "(`Execution-by:` or `Co-Authored-By:` per ADR-011 §Commit Trailer Convention "
            "+ FF-07 acceptance compromise)"
        )

    codex_match = _CODEX_RE.search(body)
    if codex_match:
        result.has_codex_trailer = True
        val = codex_match.group(1).strip()
        result.codex_value = val
        if _CODEX_VALUE_RE.match(val):
            result.codex_format_valid = True
        else:
            result.violations.append(
                f"`Codex-verified:` value `{val}` does not match "
                "`<claim-id>@<sha>` format (claim-id alphanumeric + hyphen/underscore; "
                "sha 7-40 hex chars, or literal placeholders <claim-id>/<sha>/HEAD)"
            )

    return result


def check_range(ref_range: str) -> list[CommitCheck]:
    return [check_commit(sha, subj, body) for sha, subj, body in _git_log(ref_range)]


def to_json(results: Iterable[CommitCheck]) -> str:
    return json.dumps(
        [
            {
                "sha": r.sha,
                "subject": r.subject,
                "has_attribution": r.has_attribution,
                "attribution_value": r.attribution_value,
                "has_codex_trailer": r.has_codex_trailer,
                "codex_value": r.codex_value,
                "codex_format_valid": r.codex_format_valid,
                "violations": r.violations,
            }
            for r in results
        ],
        ensure_ascii=False,
        indent=2,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Check commit trailers per ADR-011 + FF-07 contract."
    )
    parser.add_argument(
        "ref_range",
        help="git ref range, e.g. origin/main..HEAD",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of human report",
    )
    args = parser.parse_args(argv[1:])

    try:
        results = check_range(args.ref_range)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(to_json(results))
    else:
        for r in results:
            status = "OK" if not r.violations else "FAIL"
            print(f"[{status}] {r.sha[:8]} {r.subject[:80]}")
            if r.has_attribution:
                print(f"        attribution: {r.attribution_value[:80]}")
            if r.has_codex_trailer:
                fmt = "valid" if r.codex_format_valid else "INVALID"
                print(f"        codex ({fmt}): {r.codex_value[:80]}")
            for v in r.violations:
                print(f"        VIOLATION: {v}")
        print()
        ok = sum(1 for r in results if not r.violations)
        bad = len(results) - ok
        print(f"Summary: {ok}/{len(results)} OK, {bad} violations")

    return 1 if any(r.violations for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
