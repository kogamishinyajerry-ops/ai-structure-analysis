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
this exact case. R2 fix: strip HTML comments AND fenced code blocks
(triple-backtick OR triple-tilde) AND inline-code spans BEFORE
searching, so only visible markdown contributes a candidate.

R3 hardening (post Codex R2, 2026-04-26): the R2 strippers closed
the reported repros but the same bypass class still applied to other
non-claim containers. Codex provided a working repro:

    ## Self-pass-rate

    <details><summary>x</summary>30%</details>

    95%

returned `30` instead of `95` because `<details>` content renders
collapsed by default — the `30%` is hidden behind a click. A second
class is the indented code block (4+ leading spaces or tab on a
fresh paragraph) which renders monospace but is parsed by the
extractor as plain text. R3 fix: strip ANY raw-HTML block whose
opening tag is a known visible-hider (details/summary/script/style)
PLUS strip 4-space-or-tab indented code blocks. The strippers run
in order so nested constructs collapse cleanly.

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

# R3 hidden-content strippers (post Codex R2):
# - Visible-hiding HTML containers: <details>, <summary>, <script>, <style>.
#   The opening tag may carry attributes (`<details open>`, etc.).
# - Indented code blocks: per CommonMark, a paragraph-fresh line with 4+
#   leading spaces or a leading tab renders as monospace. We collapse
#   any such run-of-lines to a blank line so its `N%` does not match.
_HTML_HIDER_RE = re.compile(
    r"<(details|summary|script|style)\b[^>]*>.*?</\1\s*>",
    re.DOTALL | re.IGNORECASE,
)
# Match indented code lines: ^( {4,}|\t) followed by anything, plus
# the trailing newline. We strip the line's content but keep the
# newline so paragraph boundaries are preserved.
_INDENTED_CODE_LINE_RE = re.compile(r"(?m)^(?: {4,}|\t)[^\n]*$")

# Match the Self-pass-rate section heading then the first \d+% within
# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
# `### Self-pass-rate`, with-or-without trailing parenthetical.
_HEADING_RE = re.compile(
    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
)
_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")


def _strip_hidden_constructs(body: str) -> str:
    """Remove HTML comments, fenced/inline code, raw-HTML hiders,
    and indented code blocks.

    Pinned by adversarial tests in tests/test_extract_pr_self_pass_rate.py.
    Order is important — strip block-level constructs before line-level
    ones so a `<details>` containing a fenced code block collapses
    cleanly rather than leaving a stray ``` to confuse the next pass.
    """
    body = _HTML_COMMENT_RE.sub("", body)
    body = _HTML_HIDER_RE.sub("", body)  # R3: <details>/<summary>/etc.
    body = _FENCED_BACKTICK_RE.sub("", body)
    body = _FENCED_TILDE_RE.sub("", body)
    body = _INLINE_CODE_RE.sub("", body)
    body = _INDENTED_CODE_LINE_RE.sub("", body)  # R3: indented code
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
