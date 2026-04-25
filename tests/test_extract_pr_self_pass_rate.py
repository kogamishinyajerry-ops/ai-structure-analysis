"""Tests for scripts/extract_pr_self_pass_rate.py (ADR-013)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load():
    import extract_pr_self_pass_rate  # type: ignore[import-not-found]

    return extract_pr_self_pass_rate


@pytest.fixture(scope="module")
def mod():
    return _load()


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_h2_with_parenthetical_bold_percent(mod):
    body = """## Summary
Stuff.

## Self-pass-rate (mechanically derived)

**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in state file.

## Test plan
- [x] tests
"""
    assert mod.extract_claim(body) == 30


def test_h2_plain_percent(mod):
    body = "## Self-pass-rate\n\n80%\n"
    assert mod.extract_claim(body) == 80


def test_h3_heading(mod):
    body = "### Self-pass-rate\n95%\n"
    assert mod.extract_claim(body) == 95


def test_heading_with_space(mod):
    """Tolerate 'Self pass rate' with spaces."""
    body = "## Self pass rate\n\n50%\n"
    assert mod.extract_claim(body) == 50


def test_picks_first_percent_after_heading(mod):
    body = "## Self-pass-rate\n\n**80%** baseline (raised from 50% earlier).\n"
    assert mod.extract_claim(body) == 80


def test_zero_percent_is_valid(mod):
    body = "## Self-pass-rate\n\n0%\n"
    assert mod.extract_claim(body) == 0


def test_one_hundred_percent_is_valid(mod):
    body = "## Self-pass-rate\n\n100%\n"
    assert mod.extract_claim(body) == 100


# ---------------------------------------------------------------------------
# Unhappy paths
# ---------------------------------------------------------------------------


def test_no_heading_returns_none(mod):
    body = "## Summary\n\nWe have 95% confidence here.\n"
    assert mod.extract_claim(body) is None


def test_heading_without_percent_returns_none(mod):
    body = "## Self-pass-rate\n\nTBD — script will fill in.\n"
    assert mod.extract_claim(body) is None


def test_above_100_rejected(mod):
    body = "## Self-pass-rate\n\n150%\n"
    assert mod.extract_claim(body) is None


def test_h1_heading_rejected(mod):
    """Single-# heading must NOT match (PR body sections are h2+)."""
    body = "# Self-pass-rate\n\n95%\n"
    assert mod.extract_claim(body) is None


def test_inline_mention_rejected(mod):
    """Mentioning self-pass-rate in prose must not match."""
    body = "## Summary\n\nThe self-pass-rate is 95% trust me bro.\n"
    assert mod.extract_claim(body) is None


def test_empty_body_returns_none(mod):
    assert mod.extract_claim("") is None


def test_percent_too_far_after_heading_ignored(mod):
    """Search window is bounded so a wandering paragraph doesn't pollute."""
    body = "## Self-pass-rate\n\n" + ("filler. " * 200) + "95%\n"
    assert mod.extract_claim(body) is None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_prints_claim(mod, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", _StdinShim("## Self-pass-rate\n\n30%\n"))
    rc = mod.main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.strip() == "30"


def test_cli_exits_2_when_no_claim(mod, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", _StdinShim("## Summary\n\nNo claim here.\n"))
    rc = mod.main([])
    captured = capsys.readouterr()
    assert rc == 2
    assert "Self-pass-rate" in captured.err


class _StdinShim:
    def __init__(self, text: str):
        self._text = text

    def read(self) -> str:
        return self._text


# ---------------------------------------------------------------------------
# R2 hardening — adversarial hidden-marker bypass cases (Codex R1 HIGH #2)
# ---------------------------------------------------------------------------


def test_r2_html_comment_bypass_codex_repro(mod):
    """The exact Codex reproduction: hidden 30% via HTML comment, visible 95%.

    Before R2: returned 30 (hidden marker). After R2: returns 95 (visible).
    """
    body = "## Self-pass-rate\n\n<!-- 30% -->\n\n**95%**\n"
    assert mod.extract_claim(body) == 95


def test_r2_html_comment_with_only_hidden_returns_none(mod):
    """If the only `N%` after the heading is inside an HTML comment,
    the result must be None (no visible claim)."""
    body = "## Self-pass-rate\n\n<!-- 30% -->\n\nTBD.\n"
    assert mod.extract_claim(body) is None


def test_r2_multiline_html_comment_stripped(mod):
    body = """## Self-pass-rate

<!--
This is a multi-line comment
with a hidden 50% claim.
-->

80%
"""
    assert mod.extract_claim(body) == 80


def test_r2_fenced_backtick_code_bypass(mod):
    """A fenced code block hiding `30%` must not be the parsed claim."""
    body = """## Self-pass-rate

```
30%
```

95%
"""
    assert mod.extract_claim(body) == 95


def test_r2_fenced_tilde_code_bypass(mod):
    """Tilde fences (~~~) are also treated as code blocks."""
    body = """## Self-pass-rate

~~~
30%
~~~

95%
"""
    assert mod.extract_claim(body) == 95


def test_r2_fenced_with_language_tag(mod):
    """```python ... ``` should also be stripped."""
    body = """## Self-pass-rate

```python
SELF_PASS_RATE = "30%"
```

**80%**
"""
    assert mod.extract_claim(body) == 80


def test_r2_inline_code_bypass(mod):
    """Inline code spans like `30%` must not be the parsed claim."""
    body = "## Self-pass-rate\n\nExample: `30%`. Actual: **75%**\n"
    assert mod.extract_claim(body) == 75


def test_r2_combined_bypass_attempts(mod):
    """A bad-faith body using multiple hidden constructs at once."""
    body = """## Self-pass-rate

<!-- 30% -->

```
50%
```

`60%`

<!-- 70% -->

**95%**
"""
    assert mod.extract_claim(body) == 95


def test_r2_only_hidden_constructs_returns_none(mod):
    """If every `N%` is hidden, no claim is found."""
    body = """## Self-pass-rate

<!-- 30% -->

```
80%
```

`95%`
"""
    assert mod.extract_claim(body) is None


def test_r2_html_comment_before_heading_does_not_consume_heading(mod):
    """Make sure stripping an HTML comment doesn't accidentally remove
    text adjacent to the section heading."""
    body = "<!-- TODO: revisit -->\n\n## Self-pass-rate\n\n50%\n"
    assert mod.extract_claim(body) == 50


def test_r2_multiple_self_pass_rate_sections(mod):
    """If a body has two Self-pass-rate sections (template + copy-paste
    artifact), the FIRST visible claim wins."""
    body = """## Self-pass-rate

50%

## Self-pass-rate

80%
"""
    assert mod.extract_claim(body) == 50


# ---------------------------------------------------------------------------
# R3 adversarial — collapsed-HTML + indented-code bypass class
# (Codex R2 finding 2026-04-26)
# ---------------------------------------------------------------------------


def test_r3_details_block_bypass_codex_repro(mod):
    """Codex R2 repro verbatim: <details> hides 30%, visible 95%."""
    body = "## Self-pass-rate\n\n<details><summary>x</summary>30%</details>\n\n95%\n"
    assert mod.extract_claim(body) == 95


def test_r3_details_with_attributes_is_stripped(mod):
    """`<details open>` and arbitrary attribute values still strip cleanly."""
    body = '## Self-pass-rate\n\n<details open class="x" data-foo="30%">30%</details>\n\n**95%**\n'
    assert mod.extract_claim(body) == 95


def test_r3_summary_only_block_is_stripped(mod):
    body = "## Self-pass-rate\n\n<summary>Hidden 30%</summary>\n\n**95%**\n"
    assert mod.extract_claim(body) == 95


def test_r3_script_block_is_stripped(mod):
    body = "## Self-pass-rate\n\n<script>alert('30%')</script>\n\n**95%**\n"
    assert mod.extract_claim(body) == 95


def test_r3_style_block_is_stripped(mod):
    body = "## Self-pass-rate\n\n<style>.foo::before{content:'30%'}</style>\n\n**95%**\n"
    assert mod.extract_claim(body) == 95


def test_r3_details_uppercase_tag_is_stripped(mod):
    """HTML tags are case-insensitive."""
    body = "## Self-pass-rate\n\n<DETAILS><SUMMARY>x</SUMMARY>30%</DETAILS>\n\n**95%**\n"
    assert mod.extract_claim(body) == 95


def test_r3_details_multiline_body_is_stripped(mod):
    """The hider can span many lines."""
    body = (
        "## Self-pass-rate\n\n"
        "<details>\n"
        "  <summary>click</summary>\n"
        "  30%\n"
        "  more text\n"
        "</details>\n\n"
        "95%\n"
    )
    assert mod.extract_claim(body) == 95


def test_r3_indented_4_space_code_block_bypass(mod):
    """4+ leading spaces renders as monospace; the value is hidden in the UI."""
    body = "## Self-pass-rate\n\n    30%\n\n**95%**\n"
    assert mod.extract_claim(body) == 95


def test_r3_indented_tab_code_block_bypass(mod):
    """Leading tab is also a CommonMark indented-code marker."""
    body = "## Self-pass-rate\n\n\t30%\n\n**95%**\n"
    assert mod.extract_claim(body) == 95


def test_r3_combined_hider_and_indented_bypass(mod):
    """Stacked attempts: <details> + indented code + fenced code; visible wins."""
    body = (
        "## Self-pass-rate\n\n"
        "<details>30%</details>\n"
        "    40%\n"
        "```\n50%\n```\n"
        "<!-- 60% -->\n\n"
        "**95%**\n"
    )
    assert mod.extract_claim(body) == 95


def test_r3_all_hidden_returns_none(mod):
    """If every percent is hidden, extractor returns None (not a stale value)."""
    body = "## Self-pass-rate\n\n<details>30%</details>\n    40%\n<!-- 50% -->\n"
    assert mod.extract_claim(body) is None


def test_r3_visible_text_with_indent_under_4_spaces_kept(mod):
    """3 leading spaces is NOT a code block; the percent stays visible."""
    body = "## Self-pass-rate\n\n   30%\n"  # 3 spaces — paragraph continuation, not code
    assert mod.extract_claim(body) == 30


def test_r3_details_inside_fenced_block_already_stripped_by_fence(mod):
    """Defense-in-depth: a <details> inside a fenced code block was
    already stripped by the fence rule; R3 just removes a second copy."""
    body = "## Self-pass-rate\n\n```\n<details>30%</details>\n```\n\n95%\n"
    assert mod.extract_claim(body) == 95


def test_r3_self_closing_details_does_not_consume_following_paragraph(mod):
    """A bare `<details/>` shouldn't eat the next paragraph's percent."""
    body = "## Self-pass-rate\n\n<details></details>\n\n95%\n"
    assert mod.extract_claim(body) == 95


def test_r3_indented_code_block_does_not_eat_following_visible_paragraph(mod):
    """A blank line ends an indented code block; the next paragraph stays visible."""
    body = "## Self-pass-rate\n\n    30%\n    still in code\n\n95%\n"
    assert mod.extract_claim(body) == 95


# ---------------------------------------------------------------------------
# R4 adversarial — nested hider blocks (Codex R3 finding 2026-04-26)
# ---------------------------------------------------------------------------


def test_r4_nested_details_codex_r3_repro(mod):
    """Codex R3 repro verbatim:
    `<details><summary>x</summary><details>99%</details>30%</details>` + visible 95%
    Pre-R4: returned 30 (single-pass regex stripped only inner <details>).
    Post-R4: returns 95 (fixpoint iteration collapses both layers).
    """
    body = (
        "## Self-pass-rate\n\n"
        "<details><summary>x</summary><details>99%</details>30%</details>\n\n"
        "95%\n"
    )
    assert mod.extract_claim(body) == 95


def test_r4_triply_nested_details(mod):
    """Three layers deep. Each iteration of the fixpoint loop peels
    one layer; we cap at 64 so this is well within bounds."""
    body = (
        "## Self-pass-rate\n\n"
        "<details><details><details>10%</details>20%</details>30%</details>\n\n"
        "95%\n"
    )
    assert mod.extract_claim(body) == 95


def test_r4_alternating_nested_details_summary(mod):
    """Alternating <details>/<summary> nesting (the R3 hider tag set
    treats both as visible-hiders so they all collapse)."""
    body = (
        "## Self-pass-rate\n\n"
        "<details><summary><details>10%</details>summary text 20%</summary>30%</details>\n\n"
        "95%\n"
    )
    assert mod.extract_claim(body) == 95


def test_r4_nested_with_attributes(mod):
    body = (
        "## Self-pass-rate\n\n"
        '<details open><details class="x" data-foo="30%">99%</details>30%</details>\n\n'
        "95%\n"
    )
    assert mod.extract_claim(body) == 95


def test_r4_all_hidden_with_nested_returns_none(mod):
    """If every percent is inside a nested hider, no claim found."""
    body = "## Self-pass-rate\n\n<details><details>10%</details>20%</details>\n"
    assert mod.extract_claim(body) is None


def test_r4_fixpoint_loop_terminates_within_cap(mod):
    """Defensive: the fixpoint loop has a hard 64-iteration cap and
    each iteration strictly shrinks the body, so even pathological
    deeply-nested input must terminate."""
    # 50 nested layers — well within the 64-iter cap.
    body = "## Self-pass-rate\n\n" + ("<details>" * 50) + "10%" + ("</details>" * 50) + "\n\n95%\n"
    assert mod.extract_claim(body) == 95


def test_r4_nested_details_with_indented_code_inside(mod):
    """Nested <details> with an indented code block inside also collapses."""
    body = (
        "## Self-pass-rate\n\n"
        "<details>outer\n"
        "    30%\n"
        "    <details>99%</details>\n"
        "</details>\n\n"
        "95%\n"
    )
    assert mod.extract_claim(body) == 95


# ---------------------------------------------------------------------------
# R5 hardening — post Codex R4 (2026-04-26)
#
# Codex R4 found two residual gaps:
# (a) HIGH: depth >64 nesting exhausts the fixpoint cap with hider
#     openers still present; the leftover pseudo-balanced text leaks.
# (b) MEDIUM: the paired hider regex never matches unmatched/malformed
#     openers like `<details>30%<details>99%</details>` — the orphan
#     opener `<details>30%` survives stripping and 30% leaks as the
#     parsed claim.
# R5 fix: after the fixpoint loop, _HTML_HIDER_OPENER_RE detects ANY
# surviving opener and the strip wipes from that opener to EOF. Both
# bug classes collapse to a fail-closed None (or to whatever was
# visible BEFORE the surviving opener — usually nothing past the
# heading).
# ---------------------------------------------------------------------------


def test_r5_codex_unmatched_outer_repro_returns_none(mod):
    """Codex R4 MEDIUM repro: orphan outer <details> with inner pair.

    Previous R4 strip leaves `<details>30%` after one pass; the lazy
    regex never closes it, so 30% leaks. R5 wipes from the surviving
    opener to EOF, so neither 30% nor 99% (and not the visible 95%)
    can be parsed → claim is None (fail closed).
    """
    body = "## Self-pass-rate\n\n<details>30%<details>99%</details>\n\n95%\n"
    assert mod.extract_claim(body) is None


def test_r5_depth_65_exceeds_cap_returns_none(mod):
    """Codex R4 HIGH repro: 65 nested layers exceed the 64-iter cap.

    Pre-R5 the function returned the layer-text from whatever was
    leaked by cap exhaustion (Codex got `64`). Post-R5: any surviving
    opener after the fixpoint terminates → wipe to EOF → None.
    """
    nested = "10%"
    for i in range(65):
        nested = f"<details>{nested} {i}%</details>"
    body = f"## Self-pass-rate\n\n{nested}\n\n95%\n"
    assert mod.extract_claim(body) is None


def test_r5_depth_64_still_works(mod):
    """Regression guard: depth ≤64 must still parse the visible claim
    correctly. Builds 64 nested layers and a visible 95% AFTER the
    closer; the fixpoint terminates within the cap and no opener
    survives to trigger the R5 wipe."""
    nested = "10%"
    for _ in range(64):
        nested = f"<details>{nested}</details>"
    body = f"## Self-pass-rate\n\n{nested}\n\n95%\n"
    assert mod.extract_claim(body) == 95


def test_r5_unmatched_lone_opener_returns_none(mod):
    """A single unmatched `<details>` after the heading must wipe the
    rest of the body (fail closed) — even though pre-opener heading
    is intact, the post-opener percentage is untrustworthy."""
    body = "## Self-pass-rate\n\n<details>30%\n\n95%\n"
    assert mod.extract_claim(body) is None


def test_r5_unmatched_summary_opener_returns_none(mod):
    """Same gap class for <summary>/<script>/<style>."""
    body = "## Self-pass-rate\n\n<summary>30%\n\n95%\n"
    assert mod.extract_claim(body) is None


def test_r5_unmatched_script_opener_returns_none(mod):
    body = '## Self-pass-rate\n\n<script type="x">30%\n\n95%\n'
    assert mod.extract_claim(body) is None


def test_r5_unmatched_style_opener_returns_none(mod):
    body = "## Self-pass-rate\n\n<style>30%\n\n95%\n"
    assert mod.extract_claim(body) is None


def test_r5_visible_claim_before_orphan_opener_still_parses(mod):
    """If the visible claim is BEFORE the orphan opener, the R5 wipe
    leaves the heading + claim intact. This is the only non-None case
    for malformed bodies — the user's claim was visible before the
    hider attempt began."""
    body = "## Self-pass-rate\n\n95%\n\n<details>99%\n"
    assert mod.extract_claim(body) == 95


def test_r5_orphan_opener_inside_fenced_code_does_not_trigger(mod):
    """Fenced code is stripped FIRST, so a fake `<details>` inside it
    must not cause a false R5 wipe. Visible claim must still parse."""
    body = "## Self-pass-rate\n\n**95%**\n\n```\nexample: <details>30%\n```\n"
    assert mod.extract_claim(body) == 95


def test_r5_orphan_opener_inside_html_comment_does_not_trigger(mod):
    """HTML comments are stripped FIRST, so a fake `<details>` inside
    a comment must not cause a false R5 wipe."""
    body = "## Self-pass-rate\n\n**95%**\n\n<!-- example: <details>30% -->\n"
    assert mod.extract_claim(body) == 95


def test_r5_orphan_close_tag_alone_does_not_trigger(mod):
    """A bare `</details>` (no opener) is NOT a hider opener; the R5
    regex matches `<details ...>` only. Should not fail-close."""
    body = "## Self-pass-rate\n\n**95%** </details>\n"
    assert mod.extract_claim(body) == 95
