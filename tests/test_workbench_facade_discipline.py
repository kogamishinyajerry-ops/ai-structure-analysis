"""Facade discipline check for ADR-015.

Asserts the contract from `docs/adr/ADR-015-workbench-agent-rpc-boundary.md`:

1. Only `backend/app/workbench/agent_facade.py` may import from `agents.*`.
2. `agent_facade.py` does not assign to attributes of `agents.*` modules
   (read-only contract — agents emit effects, the facade observes them).
3. No file under `backend/app/workbench/` imports from `schemas.sim_state`
   (HF1.4); the workbench surface uses `schemas.sim_plan` only.

Pure-AST static check — no module-level execution of workbench code.
Skips when `backend/app/workbench/` does not exist (Phase 2.1 follow-up
PRs add the actual modules; this test guards their landing).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WORKBENCH_DIR = _REPO_ROOT / "backend" / "app" / "workbench"
_FACADE_FILENAME = "agent_facade.py"


def _workbench_py_files() -> list[Path]:
    if not _WORKBENCH_DIR.is_dir():
        return []
    return sorted(p for p in _WORKBENCH_DIR.rglob("*.py") if p.is_file())


def _is_agents_module(module: str | None) -> bool:
    if module is None:
        return False
    return module == "agents" or module.startswith("agents.")


def _is_sim_state_module(module: str | None) -> bool:
    if module is None:
        return False
    return module == "schemas.sim_state"


def _imports_from(tree: ast.AST, predicate) -> list[ast.AST]:
    hits: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and predicate(node.module):
            hits.append(node)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if predicate(alias.name):
                    hits.append(node)
                    break
    return hits


def _assigns_to_agents_attribute(tree: ast.AST) -> list[ast.Assign]:
    """Find `agents.X.Y = ...` style mutations of agent module state."""
    hits: list[ast.Assign] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Attribute):
                continue
            base = target
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name) and base.id == "agents":
                hits.append(node)
                break
    return hits


def test_workbench_dir_exists_or_skip():
    if not _WORKBENCH_DIR.is_dir():
        pytest.skip(
            f"{_WORKBENCH_DIR} does not exist yet — Phase 2.1 follow-up PRs "
            "add workbench modules. Discipline check is a no-op until then."
        )
    assert _WORKBENCH_DIR.is_dir()


def test_only_agent_facade_imports_from_agents():
    """ADR-015 discipline rule #1: facade is the choke point for agents.*"""
    violations: list[str] = []
    for path in _workbench_py_files():
        if path.name == _FACADE_FILENAME:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            pytest.fail(f"could not parse {path}: {exc}")
        hits = _imports_from(tree, _is_agents_module)
        if hits:
            rel = path.relative_to(_REPO_ROOT)
            for node in hits:
                module = getattr(node, "module", None) or "<bare import>"
                violations.append(f"{rel}:{node.lineno}: imports from `{module}`")
    assert not violations, (
        "ADR-015 violation — only backend/app/workbench/agent_facade.py "
        "may import from `agents.*`:\n  " + "\n  ".join(violations)
    )


def test_agent_facade_does_not_mutate_agent_state():
    """ADR-015 discipline rule #2: read-only contract on agent modules."""
    facade = _WORKBENCH_DIR / _FACADE_FILENAME
    if not facade.is_file():
        pytest.skip(f"{facade} not present yet — Phase 2.1 follow-up PR introduces it")
    tree = ast.parse(facade.read_text(encoding="utf-8"), filename=str(facade))
    hits = _assigns_to_agents_attribute(tree)
    rendered = [
        f"{facade.relative_to(_REPO_ROOT)}:{node.lineno}: assigns to agents.* attribute"
        for node in hits
    ]
    assert not hits, (
        "ADR-015 violation — agent_facade.py must not mutate agent module-level "
        "state (read-only contract; effects flow through ADR-014's event bus):\n  "
        + "\n  ".join(rendered)
    )


def test_no_workbench_file_imports_sim_state():
    """ADR-015 discipline rule #3: HF1.4 — schemas.sim_state stays internal."""
    violations: list[str] = []
    for path in _workbench_py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            pytest.fail(f"could not parse {path}: {exc}")
        hits = _imports_from(tree, _is_sim_state_module)
        if hits:
            rel = path.relative_to(_REPO_ROOT)
            for node in hits:
                violations.append(f"{rel}:{node.lineno}: imports from `schemas.sim_state`")
    assert not violations, (
        "ADR-015 violation — workbench code must not import schemas.sim_state "
        "(HF1.4); use schemas.sim_plan instead:\n  " + "\n  ".join(violations)
    )


# ---------------------------------------------------------------------------
# Synthetic-fixture coverage — verify the AST predicates catch what they must.
# These tests parse strings (not on-disk files) so they pass regardless of the
# real workbench/ contents and pin the discipline-check semantics.
# ---------------------------------------------------------------------------


def _parse(src: str) -> ast.AST:
    return ast.parse(src, filename="<synthetic>")


class TestPredicates:
    def test_from_agents_router_is_caught(self):
        tree = _parse("from agents.router import route_simplan\n")
        hits = _imports_from(tree, _is_agents_module)
        assert len(hits) == 1

    def test_bare_import_agents_is_caught(self):
        tree = _parse("import agents.solver as solver\n")
        hits = _imports_from(tree, _is_agents_module)
        assert len(hits) == 1

    def test_unrelated_import_is_ignored(self):
        tree = _parse("from backend.app.api import runs\nimport json\n")
        assert _imports_from(tree, _is_agents_module) == []

    def test_relative_import_is_ignored(self):
        # `from .agent_facade import X` — module is "agent_facade", NOT "agents.*"
        tree = _parse("from .agent_facade import draft_simplan\n")
        assert _imports_from(tree, _is_agents_module) == []

    def test_lookalike_module_is_ignored(self):
        # "agentsuite" must not match "agents" — startswith check is "agents."
        tree = _parse("from agentsuite import helpers\n")
        assert _imports_from(tree, _is_agents_module) == []

    def test_assignment_to_agents_attribute_is_caught(self):
        tree = _parse("import agents\nagents.router.GLOBAL_FLAG = True\n")
        assert len(_assigns_to_agents_attribute(tree)) == 1

    def test_deep_attribute_assignment_is_caught(self):
        tree = _parse("import agents\nagents.solver.driver.cache = {}\n")
        assert len(_assigns_to_agents_attribute(tree)) == 1

    def test_assignment_to_local_variable_is_ignored(self):
        tree = _parse("agents = []\nagents_seen = True\n")
        assert _assigns_to_agents_attribute(tree) == []

    def test_assignment_to_unrelated_module_is_ignored(self):
        tree = _parse("import json\njson.something = 1\n")
        assert _assigns_to_agents_attribute(tree) == []

    def test_sim_state_import_is_caught(self):
        tree = _parse("from schemas.sim_state import SimState\n")
        hits = _imports_from(tree, _is_sim_state_module)
        assert len(hits) == 1

    def test_sim_plan_import_is_allowed(self):
        tree = _parse("from schemas.sim_plan import SimPlan\n")
        assert _imports_from(tree, _is_sim_state_module) == []
