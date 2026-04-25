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
