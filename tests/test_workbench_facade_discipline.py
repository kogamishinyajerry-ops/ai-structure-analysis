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


def _agent_local_names(tree: ast.AST) -> set[str]:
    """Return every local name that is bound to an agent module.

    Covers all ways the workbench can take a reference to an agent
    module (Codex R1 HIGH#1: `from agents import architect` then
    `architect.X = Y` previously slipped past the root-name check).

    Forms recognized:
    - `import agents`                          → 'agents'
    - `import agents as A`                     → 'A'
    - `import agents.architect`                → 'agents' (deep-attr access)
    - `import agents.architect as A`           → 'A'
    - `from agents import architect`           → 'architect'
    - `from agents import architect as A`      → 'A'
    - `from agents.<sub> import X`             → 'X'
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "agents" or alias.name.startswith("agents."):
                    if alias.asname is not None:
                        names.add(alias.asname)
                    else:
                        # `import agents.architect` binds 'agents'
                        names.add(alias.name.split(".", 1)[0])
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (node.module == "agents" or node.module.startswith("agents."))
        ):
            for alias in node.names:
                bound = alias.asname or alias.name
                if bound != "*":  # star imports aren't bindable to a name
                    names.add(bound)
    return names


def _assigns_to_agent_module(tree: ast.AST) -> list[ast.Assign]:
    """Find any `<agent_local>.X = ...` assignment.

    The set of `<agent_local>` names comes from `_agent_local_names`:
    it includes every alias the file uses to refer to an agent module,
    not just the literal name `agents`. This closes the Codex R1 HIGH:

        from agents import architect
        architect.GLOBAL_FLAG = True   # silently bypassed the old check
    """
    agent_names = _agent_local_names(tree)
    if not agent_names:
        return []
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
            if isinstance(base, ast.Name) and base.id in agent_names:
                hits.append(node)
                break
    return hits


def _imports_sim_state(tree: ast.AST) -> list[ast.AST]:
    """Find every way the file pulls in `schemas.sim_state`.

    Closes Codex R1 HIGH#2: the previous check matched only the
    fully-qualified module string. These three are equivalent imports
    of the HF1.4 module that all need to be flagged:

    - `import schemas.sim_state`
    - `from schemas.sim_state import SimState`
    - `from schemas import sim_state`
    - `from schemas import sim_state as S`
    """
    hits: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "schemas.sim_state":
                hits.append(node)
                continue
            if node.module == "schemas":
                for alias in node.names:
                    if alias.name == "sim_state":
                        hits.append(node)
                        break
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "schemas.sim_state":
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
    """ADR-015 discipline rule #2: read-only contract on agent modules.

    Closes Codex R1 HIGH#1 — the check now follows alias bindings, so
    `from agents import architect; architect.X = Y` is also flagged.
    """
    facade = _WORKBENCH_DIR / _FACADE_FILENAME
    if not facade.is_file():
        pytest.skip(f"{facade} not present yet — Phase 2.1 follow-up PR introduces it")
    tree = ast.parse(facade.read_text(encoding="utf-8"), filename=str(facade))
    hits = _assigns_to_agent_module(tree)
    rendered = [
        f"{facade.relative_to(_REPO_ROOT)}:{node.lineno}: assigns to agent-module attribute"
        for node in hits
    ]
    assert not hits, (
        "ADR-015 violation — agent_facade.py must not mutate agent module-level "
        "state (read-only contract; effects flow through ADR-014's event bus):\n  "
        + "\n  ".join(rendered)
    )


def test_no_workbench_file_imports_sim_state():
    """ADR-015 discipline rule #3: HF1.4 — schemas.sim_state stays internal.

    Closes Codex R1 HIGH#2 — the check now catches all four import
    forms, including `from schemas import sim_state` which bypassed
    the literal-module-name match.
    """
    violations: list[str] = []
    for path in _workbench_py_files():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            pytest.fail(f"could not parse {path}: {exc}")
        hits = _imports_sim_state(tree)
        if hits:
            rel = path.relative_to(_REPO_ROOT)
            for node in hits:
                violations.append(f"{rel}:{node.lineno}: imports `schemas.sim_state` (any form)")
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
        tree = _parse("from app.api import runs\nimport json\n")
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
        assert len(_assigns_to_agent_module(tree)) == 1

    def test_deep_attribute_assignment_is_caught(self):
        tree = _parse("import agents\nagents.solver.driver.cache = {}\n")
        assert len(_assigns_to_agent_module(tree)) == 1

    def test_assignment_to_local_variable_is_ignored(self):
        tree = _parse("agents = []\nagents_seen = True\n")
        assert _assigns_to_agent_module(tree) == []

    def test_assignment_to_unrelated_module_is_ignored(self):
        tree = _parse("import json\njson.something = 1\n")
        assert _assigns_to_agent_module(tree) == []

    def test_sim_state_import_is_caught(self):
        tree = _parse("from schemas.sim_state import SimState\n")
        assert len(_imports_sim_state(tree)) == 1

    def test_sim_plan_import_is_allowed(self):
        tree = _parse("from schemas.sim_plan import SimPlan\n")
        assert _imports_sim_state(tree) == []


class TestR2AliasBypassClosed:
    """Codex R1 HIGH#1: alias-import + attribute mutation must be caught."""

    def test_from_agents_import_then_assign_is_caught(self):
        """`from agents import architect` + `architect.X = Y` is the
        sanctioned import form for agent_facade.py — its mutation
        path slipped past the root-name check before R2."""
        tree = _parse("from agents import architect\narchitect.GLOBAL_FLAG = True\n")
        assert len(_assigns_to_agent_module(tree)) == 1

    def test_from_agents_import_with_alias_then_assign_is_caught(self):
        tree = _parse("from agents import architect as A\nA.cache = {}\n")
        assert len(_assigns_to_agent_module(tree)) == 1

    def test_from_agents_subpkg_import_then_assign_is_caught(self):
        tree = _parse("from agents.architect import run\nrun.attr = 1\n")
        assert len(_assigns_to_agent_module(tree)) == 1

    def test_import_agents_arch_as_alias_then_assign_is_caught(self):
        tree = _parse("import agents.architect as A\nA.x = 1\n")
        assert len(_assigns_to_agent_module(tree)) == 1

    def test_unrelated_local_named_architect_is_not_an_agent_local(self):
        """A local variable named `architect` that wasn't imported from
        agents must NOT trip the check."""
        tree = _parse("architect = object()\narchitect.x = 1\n")
        assert _assigns_to_agent_module(tree) == []

    def test_local_names_set_extracts_alias_bindings(self):
        tree = _parse(
            "from agents import architect\n"
            "from agents.solver import driver as D\n"
            "import agents.mesh\n"
            "import agents as core\n"
        )
        names = _agent_local_names(tree)
        # `from agents import architect` → architect
        # `from agents.solver import driver as D` → D
        # `import agents.mesh` → agents (root binding)
        # `import agents as core` → core
        assert names == {"architect", "D", "agents", "core"}


class TestR2SimStateBypassClosed:
    """Codex R1 HIGH#2: `from schemas import sim_state` must be caught."""

    def test_from_schemas_import_sim_state_is_caught(self):
        """The bypass form: module='schemas', name='sim_state'."""
        tree = _parse("from schemas import sim_state\n")
        assert len(_imports_sim_state(tree)) == 1

    def test_from_schemas_import_sim_state_with_alias_is_caught(self):
        tree = _parse("from schemas import sim_state as S\n")
        assert len(_imports_sim_state(tree)) == 1

    def test_import_schemas_sim_state_is_caught(self):
        tree = _parse("import schemas.sim_state\n")
        assert len(_imports_sim_state(tree)) == 1

    def test_from_schemas_import_unrelated_is_ignored(self):
        """Importing OTHER schemas modules is fine — only sim_state is HF1.4."""
        tree = _parse("from schemas import sim_plan\n")
        assert _imports_sim_state(tree) == []

    def test_from_schemas_import_multiple_with_sim_state_caught(self):
        tree = _parse("from schemas import sim_plan, sim_state\n")
        assert len(_imports_sim_state(tree)) == 1

    def test_relative_schemas_import_is_ignored(self):
        """Relative imports (level >= 1) are not absolute schemas references."""
        tree = _parse("from . import sim_state\n")
        assert _imports_sim_state(tree) == []
