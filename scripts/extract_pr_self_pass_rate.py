"""Extract the claimed Self-pass-rate from a PR body.

The PR template (per ADR-013) reserves a section labeled
"Self-pass-rate (mechanically derived)" whose first line contains the
claimed ceiling as `**N%**` (or just `N%`). This helper extracts that
integer so CI can pass it to compute_calibration_cap.py --check.

R2 hardening (post Codex R1, 2026-04-26): hidden-marker bypass closed.
The previous regex matched the FIRST `N%` within 600 chars of the
heading without distinguishing visible markdown from hidden constructs.
A PR body like:

    ## Self-pass-rate

    <!-- 30% -->

    **95%**

would parse as `30` while a human reviewer sees `95`. Codex reproduced
this exact case. Fix: strip HTML comments AND fenced code blocks
(triple-backtick OR triple-tilde) BEFORE searching, so only visible
markdown contributes a candidate.

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

# R2 hidden-content strippers — order matters (HTML comments may
# legitimately appear inside fenced code, and we want both gone).
# All use re.DOTALL so multi-line constructs are scrubbed.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCED_BACKTICK_RE = re.compile(r"```.*?```", re.DOTALL)
_FENCED_TILDE_RE = re.compile(r"~~~.*?~~~", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")

# Match the Self-pass-rate section heading then the first \d+% within
# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
# `### Self-pass-rate`, with-or-without trailing parenthetical.
_HEADING_RE = re.compile(
    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
)
_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")


def _strip_hidden_constructs(body: str) -> str:
    """Remove HTML comments + fenced code blocks + inline-code spans.

    Pinned by adversarial tests in tests/test_extract_pr_self_pass_rate.py.
    """
    body = _HTML_COMMENT_RE.sub("", body)
    body = _FENCED_BACKTICK_RE.sub("", body)
    body = _FENCED_TILDE_RE.sub("", body)
    body = _INLINE_CODE_RE.sub("", body)
    return body


def extract_claim(body: str) -> int | None:
    """Return the integer claim (0-100) or None if not found.

    Strips hidden markdown constructs (HTML comments, fenced and inline
    code) before matching, so the parsed claim must equal what a human
    reviewer sees.
    """
    body = _strip_hidden_constructs(body)
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
