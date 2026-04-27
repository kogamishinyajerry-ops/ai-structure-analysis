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
  2. No active source file (under ``backend/``, ``agents/``,
     ``schemas/``, root ``tests/``, etc.) may import via
     ``backend.app.X`` — that creates the dual-module-object
     footgun. The single allowed exception is this test file itself,
     which intentionally references the forbidden form to detect it.
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()

# Deny-list of directory *names* (not paths) we don't recurse into.
# Everything else under REPO_ROOT is scanned. An allow-list approach
# was rejected after R1 — Codex showed it missed legitimately-installed
# top-level trees like ``persistence``, ``scratch`` and ad-hoc one-off
# scripts under ``scripts/``. Scanning the whole repo and excluding
# build/venv/quarantine artifacts is cheaper to keep correct than
# enumerating every active source tree.
_EXCLUDED_DIR_NAMES = frozenset(
    {
        "__pycache__",
        "_frozen",  # Sprint-N quarantine, RFC-001 §6.1 Bucket B
        ".git",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".codebuddy",
        ".vscode",
        ".planning",
        "ai_structure_fea.egg-info",
        "node_modules",
        "htmlcov",
        "build",
        "dist",
        # Pure-data / non-Python tree-roots — scanning them would
        # silently scoop up generated artifacts (vtu/csv/json) and
        # add noise. Python files inside any of these would be a
        # red flag in their own right.
        "calculix_cases",
        "data",
        "docs",
        "frontend",
        "golden_samples",
        "project_state",
        "prompts",
        "reports",
        "runs",
        "templates",
        "config",
        # ``scratch/`` is in .gitignore — local-only ad-hoc files.
        # Different developers have different content here, so we
        # don't enforce the import contract on it. Anything under
        # ``scratch/`` that ought to be canonical-path-clean should
        # be promoted out of scratch first.
        "scratch",
    }
)


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


def _iter_active_python_files() -> Iterator[Path]:
    """Yield every active .py file under REPO_ROOT, skipping the
    deny-listed directories and this test file itself.

    We walk the tree manually instead of ``rglob('*.py')`` so we can
    prune subtrees the instant we see a deny-listed directory name —
    cheaper and less likely to read megabytes from
    ``ai_structure_fea.egg-info`` etc.
    """
    stack: list[Path] = [REPO_ROOT]
    while stack:
        cur = stack.pop()
        try:
            entries = list(cur.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name in _EXCLUDED_DIR_NAMES:
                    continue
                if entry.name.startswith(".") and entry != REPO_ROOT:
                    # Catch any future hidden-dir we forgot to enumerate.
                    continue
                stack.append(entry)
            elif entry.suffix == ".py":
                if entry.samefile(THIS_FILE):
                    continue
                yield entry


def test_no_source_imports_via_backend_app_path() -> None:
    """No active source file in any installed-package tree may import
    ``backend.app.X`` — only ``app.X``.

    Rationale: editable install puts both repo-root and ``backend/`` on
    sys.path, so ``from backend.app.X`` and ``from app.X`` both resolve
    to the same on-disk files but yield distinct module objects.
    Anything module-global (e.g. dataclass slot caches, sys.modules-
    based singletons, lru_cache state) would diverge silently. Keep the
    canonical path ``app.X``.

    Scan walks the entire repo (with a small deny-list of build /
    venv / quarantine / non-Python-data subtrees) so a regression in
    *any* tree the editable install exposes — including ad-hoc
    one-offs in ``scratch/`` or ``scripts/`` and additional top-level
    packages like ``persistence/`` — trips this guard.
    """
    offenders: list[tuple[Path, int, str]] = []
    for py in _iter_active_python_files():
        text = py.read_text(encoding="utf-8", errors="replace")
        for match in _FORBIDDEN_IMPORT.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = text.splitlines()[line_no - 1]
            offenders.append((py.relative_to(REPO_ROOT), line_no, line.strip()))
    assert not offenders, (
        "Found imports via the ``backend.app.X`` path — use ``app.X`` "
        "instead (see tests/test_packaging.py docstring):\n"
        + "\n".join(f"  {p}:{n}: {ln}" for p, n, ln in offenders)
    )


def test_pyproject_advertises_correct_package_layout() -> None:
    """Sanity-check on pyproject.toml: ``app*`` must be in
    ``[tool.setuptools.packages.find]`` ``include``, AND ``backend/``
    must be in ``where``. If either drifts, ``import app`` breaks
    after a fresh install and we won't notice until a console_script
    runs."""
    # ``tomllib`` is in stdlib from 3.11; project's ``requires-python``
    # is >=3.11 so this is unconditional.
    import tomllib

    pyproject = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    find_cfg = data["tool"]["setuptools"]["packages"]["find"]
    assert "backend" in find_cfg["where"], find_cfg
    assert any(pat == "app*" or pat.startswith("app") for pat in find_cfg["include"]), find_cfg
