"""Shared pytest fixtures for AI-FEA tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def runs_dir(repo_root: Path, tmp_path: Path) -> Path:
    """Return a temporary runs directory for test isolation."""
    d = tmp_path / "runs"
    d.mkdir()
    return d


@pytest.fixture(autouse=True)
def _reset_signoff_rate_limit_state() -> None:
    """FM-04a Phase 10 D — clear the per-(case, reviewer) signoff
    rate-limit state before every test.

    The rate limit is module-level state, so without this reset a
    test that POSTs 5 signoffs as the same reviewer to the same case
    would pollute the next test in the same module. Phase 10
    anti-gaming guard M: -3 requires a documented reset hook; this
    fixture uses it.
    """
    from app.services.reporting.signoff_rate_limit import _reset_state_for_tests

    _reset_state_for_tests()
