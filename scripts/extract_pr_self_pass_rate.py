"""Extract the claimed Self-pass-rate from a PR body.

The PR template (per ADR-013) reserves a section labeled
"Self-pass-rate (mechanically derived)" whose first line contains the
claimed ceiling as `**N%**` (or just `N%`). This helper extracts that
integer so CI can pass it to compute_calibration_cap.py --check.

Usage:
    python3 scripts/extract_pr_self_pass_rate.py < pr_body.txt
    cat pr_body.txt | python3 scripts/extract_pr_self_pass_rate.py
    echo "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py

Prints the integer claim on stdout (one line, no `%`). Exits non-zero if
no claim found in the body.
"""

from __future__ import annotations

import re
import sys

# Match the Self-pass-rate section heading then the first \d+% within
# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
# `### Self-pass-rate`, with-or-without trailing parenthetical.
_HEADING_RE = re.compile(
    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
)
_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")


def extract_claim(body: str) -> int | None:
    """Return the integer claim (0-100) or None if not found."""
    heading = _HEADING_RE.search(body)
    if not heading:
        return None
    tail = body[heading.end() : heading.end() + 600]
    m = _PERCENT_RE.search(tail)
    if not m:
        return None
    val = int(m.group(1))
    if not 0 <= val <= 100:
        return None
    return val


def main(argv: list[str]) -> int:
    body = sys.stdin.read()
    claim = extract_claim(body)
    if claim is None:
        print(
            "ERROR: PR body does not contain a 'Self-pass-rate' section "
            "with a `N%` claim. ADR-013 requires this section in every PR.",
            file=sys.stderr,
        )
        return 2
    print(claim)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
