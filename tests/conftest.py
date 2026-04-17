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
