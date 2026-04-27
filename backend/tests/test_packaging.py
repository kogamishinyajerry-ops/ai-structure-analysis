"""Packaging regression tests — RFC-001 §6 W5-prep.

The repo's two source trees (legacy ``agents/tools/schemas/...`` at the
root + the RFC-001 Layer-1..4 codebase under ``backend/app/``) install
side-by-side as top-level packages so that ``app.X`` and ``agents.X``
both resolve after ``pip install -e .``.

A side-effect of putting the repo root on ``sys.path`` is that
``backend`` is discoverable as an implicit-namespace package, which
makes ``from backend.app.X import Y`` *also* resolve to the same on-
disk files as ``from app.X import Y``. They produce distinct module
objects, however — anything module-global (caches, registries, locks)
would silently diverge if both import paths got used.

Canonical import path is ``app.X``. These tests guard against drift:

  1. ``app`` must be importable as a top-level package (otherwise the
     ``run-well-harness`` and ``report-cli`` console scripts break).
  2. No source file under ``backend/`` may import via ``backend.app.X``
     — that creates the dual-module-object footgun. The single
     allowed exception is this test file itself, which intentionally
     references the forbidden form to detect it.
"""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()


def test_app_is_importable_as_top_level() -> None:
    """``import app`` and a deep submodule must succeed.

    If this fails, ``pip install -e .`` produced a broken environment
    and every console_script under ``[project.scripts]`` will
    ModuleNotFoundError on first use.
    """
    importlib.import_module("app")
    importlib.import_module("app.services.report.cli")


def test_console_script_entry_points_resolve() -> None:
    """The two ``[project.scripts]`` entries must point at importable
    callables. We don't shell-out to the script (CI environments may
    not put the venv ``bin/`` on PATH); we just resolve the entry
    point the way the wheel's launcher would."""
    from app.services.report.cli import main as report_main
    from app.well_harness.cli import main as harness_main

    assert callable(report_main)
    assert callable(harness_main)


# Match ``import backend.app...`` and ``from backend.app...`` (with or
# without a leading ``.`` segment), but NOT plain ``backend.``-prefixed
# things in strings, comments, or unrelated identifiers like
# ``my_backend_app``. We only accept whitespace or start-of-line before.
_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+backend\.app\b",
    re.MULTILINE,
)


def _python_files_under(root: Path) -> list[Path]:
    return [
        p
        for p in root.rglob("*.py")
        # Skip the test file itself — it intentionally references the
        # pattern in a comment + the regex above. We use ``samefile``
        # instead of path equality so it survives symlinks.
        if not p.samefile(THIS_FILE)
        # Skip __pycache__ artifacts.
        and "__pycache__" not in p.parts
        # Skip the frozen-Sprint-N quarantine — those modules are not
        # actively maintained (RFC-001 §6.1 Bucket B). The CI harness
        # excludes them too via the ``legacy`` marker.
        and "_frozen" not in p.parts
    ]


def test_no_source_imports_via_backend_app_path() -> None:
    """No active source file may import ``backend.app.X`` — only ``app.X``.

    Rationale: editable install puts both repo-root and ``backend/`` on
    sys.path, so ``from backend.app.X`` and ``from app.X`` both resolve
    to the same on-disk files but yield distinct module objects.
    Anything module-global (e.g. dataclass slot caches, sys.modules-
    based singletons, lru_cache state) would diverge silently. Keep the
    canonical path ``app.X``.
    """
    offenders: list[tuple[Path, int, str]] = []
    for py in _python_files_under(BACKEND_ROOT):
        text = py.read_text(encoding="utf-8", errors="replace")
        for match in _FORBIDDEN_IMPORT.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = text.splitlines()[line_no - 1]
            offenders.append((py.relative_to(REPO_ROOT), line_no, line.strip()))
    assert not offenders, (
        "Found imports via the ``backend.app.X`` path — use ``app.X`` "
        "instead (see backend/tests/test_packaging.py docstring):\n"
        + "\n".join(f"  {p}:{n}: {ln}" for p, n, ln in offenders)
    )


def test_pyproject_advertises_correct_package_layout() -> None:
    """Sanity-check on pyproject.toml: ``app*`` must be in
    ``[tool.setuptools.packages.find]`` ``include``, AND ``backend/``
    must be in ``where``. If either drifts, ``import app`` breaks
    after a fresh install and we won't notice until a console_script
    runs."""
    if sys.version_info >= (3, 11):
        import tomllib  # type: ignore[import-not-found,unused-ignore]
    else:  # pragma: no cover — project requires-python is >=3.11
        pytest.skip("tomllib needs Python 3.11+")
    pyproject = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    find_cfg = data["tool"]["setuptools"]["packages"]["find"]
    assert "backend" in find_cfg["where"], find_cfg
    assert any(
        pat == "app*" or pat.startswith("app")
        for pat in find_cfg["include"]
    ), find_cfg
