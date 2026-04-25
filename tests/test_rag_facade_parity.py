"""Discipline + parity checks for ADR-017.

Asserts the contract from `docs/adr/ADR-017-rag-facade-cli-lib-parity.md`:

1. Only `rag_facade.py` (and `agent_facade.py`, per ADR-015) under
   `backend/app/workbench/` may import `backend.app.rag.*`.
2. `rag_facade.py` does NOT import `backend.app.rag.*_cli` / `coverage_audit`
   (the facade goes through the library, not the CLI shell).
3. Each CLI module that exists imports its sibling library module (parity:
   CLI is a thin shell over the library, never re-implements logic).
4. No CLI module imports another CLI module's symbols (CLIs compose through
   the library, never through each other's `main()`).

Pure-AST static checks. Skips gracefully when target modules don't exist
yet — the workbench facade lands in Phase 2.1 follow-up; the RAG track
(PR #38-#47) lands the library + CLI modules.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WORKBENCH_DIR = _REPO_ROOT / "backend" / "app" / "workbench"
_RAG_DIR = _REPO_ROOT / "backend" / "app" / "rag"
# R2 (post Codex R1 HIGH): the choke point is ONLY rag_facade.py.
# agent_facade.py imports agents.*, but if an agent internally calls
# backend.app.rag.* that's the agent's concern — agent_facade itself
# does NOT need RAG access. Forcing rag_facade as the single workbench
# RAG entry-point matches docs/adr/ADR-017 §41-42,49.
_RAG_FACADE_NAME = "rag_facade.py"

# CLI/library pairs as the RAG track defines them. Each tuple is
# (cli_module_filename, library_module_filename). When a CLI exists, it
# must import its library sibling.
_CLI_LIB_PAIRS = [
    ("cli.py", "ingest.py"),  # PR #38: ingest CLI wraps ingest library
    ("query_cli.py", "kb.py"),  # PR #39: query CLI wraps KB
    ("advise_cli.py", "reviewer_advisor.py"),  # PR #41 wraps PR #40
    ("preflight_publish_cli.py", "preflight_publish.py"),  # PR #45 wraps PR #43
]

# CLI modules that must NEVER appear in rag_facade.py imports.
_FORBIDDEN_FACADE_IMPORTS = {
    "backend.app.rag.cli",
    "backend.app.rag.query_cli",
    "backend.app.rag.advise_cli",
    "backend.app.rag.preflight_publish_cli",
    "backend.app.rag.coverage_audit",  # CLI-shaped audit tool
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _module_predicate_from_rag(module: str | None) -> bool:
    if module is None:
        return False
    return module == "backend.app.rag" or module.startswith("backend.app.rag.")


def _imports_modules(tree: ast.AST) -> set[str]:
    """Collect every `from X import …` target and `import X` name.

    R2 (post Codex R1 MEDIUM): also records relative-import targets so
    the contract tests cannot be bypassed by `from . import kb` or
    `from .<sub> import X` syntax. The recorded form for relative
    imports is the bare module name (`kb`, `query_cli`) — the same
    form a CLI would use to import its library sibling.
    """
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                # Absolute or relative-with-module: `from .kb import X` or
                # `from kb import X`. Record the module name.
                seen.add(node.module)
            elif node.level >= 1:
                # Relative-with-bare-module: `from . import kb`. Each
                # alias is itself a module reference.
                for alias in node.names:
                    seen.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                seen.add(alias.name)
    return seen


def _parse_file(path: Path) -> ast.AST | None:
    if not path.is_file():
        return None
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:  # pragma: no cover — surfaces real bugs
        pytest.fail(f"could not parse {path}: {exc}")
        return None


def _workbench_py_files() -> list[Path]:
    if not _WORKBENCH_DIR.is_dir():
        return []
    return sorted(p for p in _WORKBENCH_DIR.rglob("*.py") if p.is_file())


# ---------------------------------------------------------------------------
# Rule #1 — only facade modules import backend.app.rag.* from workbench
# ---------------------------------------------------------------------------


def test_only_rag_facade_imports_rag_from_workbench():
    """ADR-017 rule #1: rag_facade.py is the SOLE choke point for RAG library.

    R2 fix (post Codex R1 HIGH): the previous _FACADE_NAMES set allowed
    both rag_facade.py and agent_facade.py. The ADR explicitly says
    rag_facade is the single choke point — agents that call RAG do so
    internally; agent_facade.py itself does NOT need RAG access.
    """
    if not _WORKBENCH_DIR.is_dir():
        pytest.skip(f"{_WORKBENCH_DIR} does not exist yet — Phase 2.1 follow-up")
    violations: list[str] = []
    for path in _workbench_py_files():
        if path.name == _RAG_FACADE_NAME:
            continue
        tree = _parse_file(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and _module_predicate_from_rag(node.module):
                violations.append(
                    f"{path.relative_to(_REPO_ROOT)}:{node.lineno}: imports `{node.module}`"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if _module_predicate_from_rag(alias.name):
                        violations.append(
                            f"{path.relative_to(_REPO_ROOT)}:{node.lineno}: imports `{alias.name}`"
                        )
    assert not violations, (
        "ADR-017 violation — ONLY rag_facade.py may import backend.app.rag.* "
        "from the workbench package:\n  " + "\n  ".join(violations)
    )


# ---------------------------------------------------------------------------
# Rule #2 — rag_facade.py does NOT import RAG CLI shells
# ---------------------------------------------------------------------------


def test_rag_facade_does_not_import_rag_cli_shells():
    """ADR-017 rule #2: facade goes through library, not CLI."""
    facade = _WORKBENCH_DIR / "rag_facade.py"
    if not facade.is_file():
        pytest.skip(f"{facade} does not exist yet — Phase 2.1 follow-up adds it")
    tree = _parse_file(facade)
    assert tree is not None
    imported = _imports_modules(tree)
    forbidden_hits = imported & _FORBIDDEN_FACADE_IMPORTS
    assert not forbidden_hits, (
        f"ADR-017 violation — rag_facade.py must not import RAG CLI shells; "
        f"found: {sorted(forbidden_hits)}. Use the library API instead."
    )


# ---------------------------------------------------------------------------
# Rule #3 — each CLI shell imports its library sibling
# ---------------------------------------------------------------------------


def test_each_cli_shell_imports_its_library_sibling():
    """ADR-017 rule #3: CLI modules are thin shells over library modules."""
    if not _RAG_DIR.is_dir():
        pytest.skip(f"{_RAG_DIR} does not exist yet — RAG track (PR #38-#47)")
    skipped = 0
    parity_violations: list[str] = []
    for cli_name, lib_name in _CLI_LIB_PAIRS:
        cli_path = _RAG_DIR / cli_name
        lib_path = _RAG_DIR / lib_name
        if not cli_path.is_file() or not lib_path.is_file():
            skipped += 1
            continue
        tree = _parse_file(cli_path)
        if tree is None:
            continue
        imported = _imports_modules(tree)
        # The CLI may import via `from backend.app.rag.<lib> import …` or
        # `from .<lib> import …` (relative). Accept either.
        lib_stem = lib_name[: -len(".py")]
        absolute = f"backend.app.rag.{lib_stem}"
        relative_targets = {lib_stem}  # `from .<lib_stem> import …`
        ok = absolute in imported or any(t in imported for t in relative_targets)
        # Also accept any module starting with `backend.app.rag.<lib_stem>`
        if not ok:
            ok = any(m == absolute or m.startswith(absolute + ".") for m in imported)
        if not ok:
            parity_violations.append(
                f"{cli_path.relative_to(_REPO_ROOT)}: does not import `{absolute}` "
                f"(or relative `.{lib_stem}`); add a thin-shell import or carve "
                f"the logic out into the library."
            )
    if skipped == len(_CLI_LIB_PAIRS):
        pytest.skip("no CLI/lib pair present yet — RAG track (PR #38-#47) not landed")
    assert not parity_violations, (
        "ADR-017 rule #3 violation — CLI shells must import their library "
        "siblings:\n  " + "\n  ".join(parity_violations)
    )


# ---------------------------------------------------------------------------
# Rule #4 — no CLI imports another CLI's symbols
# ---------------------------------------------------------------------------


def test_no_cli_imports_another_cli():
    """ADR-017 rule #4: CLIs compose through the library, not each other."""
    if not _RAG_DIR.is_dir():
        pytest.skip(f"{_RAG_DIR} does not exist yet — RAG track (PR #38-#47)")
    cli_filenames = {p[0] for p in _CLI_LIB_PAIRS}
    cli_module_names = {f"backend.app.rag.{name[:-len('.py')]}" for name in cli_filenames}
    cli_relative_names = {name[: -len(".py")] for name in cli_filenames}
    violations: list[str] = []
    for cli_name in cli_filenames:
        cli_path = _RAG_DIR / cli_name
        if not cli_path.is_file():
            continue
        tree = _parse_file(cli_path)
        if tree is None:
            continue
        imported = _imports_modules(tree)
        own_module = f"backend.app.rag.{cli_name[: -len('.py')]}"
        own_relative = cli_name[: -len(".py")]
        for mod in imported:
            if mod in cli_module_names and mod != own_module:
                violations.append(
                    f"{cli_path.relative_to(_REPO_ROOT)}: imports another CLI `{mod}`"
                )
            elif mod in cli_relative_names and mod != own_relative:
                violations.append(
                    f"{cli_path.relative_to(_REPO_ROOT)}: imports another CLI `.{mod}`"
                )
    assert not violations, (
        "ADR-017 rule #4 violation — CLIs must not import each other; route "
        "shared logic through the library:\n  " + "\n  ".join(violations)
    )


# ---------------------------------------------------------------------------
# Synthetic-fixture coverage — pin the AST predicates
# ---------------------------------------------------------------------------


def _parse(src: str) -> ast.AST:
    return ast.parse(src, filename="<synthetic>")


class TestPredicates:
    def test_from_rag_lib_is_caught(self):
        tree = _parse("from backend.app.rag.reviewer_advisor import advise\n")
        assert any(_module_predicate_from_rag(m) for m in _imports_modules(tree))

    def test_bare_import_rag_subpackage_is_caught(self):
        tree = _parse("import backend.app.rag.kb\n")
        # `_imports_modules` records the bare-import target as the full name
        names = _imports_modules(tree)
        assert any(_module_predicate_from_rag(n) for n in names)

    def test_unrelated_rag_lookalike_is_ignored(self):
        # `backend.app.ragout` must NOT match `backend.app.rag.*`
        tree = _parse("from backend.app.ragout import helper\n")
        names = _imports_modules(tree)
        assert not any(_module_predicate_from_rag(n) for n in names)

    def test_relative_import_records_module(self):
        tree = _parse("from .reviewer_advisor import advise\n")
        names = _imports_modules(tree)
        assert "reviewer_advisor" in names

    def test_forbidden_facade_set_recognizes_cli_modules(self):
        for name in _FORBIDDEN_FACADE_IMPORTS:
            assert name.startswith("backend.app.rag.")
            tail = name.rsplit(".", 1)[1]
            # Each forbidden module is either a CLI shell or the coverage_audit
            # CLI-shaped tool. "cli" alone (PR #38 ingest CLI) counts.
            assert tail.endswith("_cli") or tail == "cli" or tail == "coverage_audit"


class TestR2RelativeImportNoBypass:
    """Codex R1 MEDIUM: rules #3/#4 ignored `from . import kb` syntax."""

    def test_relative_bare_import_records_each_alias(self):
        """`from . import kb` records 'kb' (was missing pre-R2)."""
        tree = _parse("from . import kb\n")
        assert "kb" in _imports_modules(tree)

    def test_relative_bare_import_with_multiple_names(self):
        tree = _parse("from . import kb, query_cli\n")
        names = _imports_modules(tree)
        assert "kb" in names
        assert "query_cli" in names

    def test_relative_with_alias_records_each_alias_target(self):
        """`from . import kb as K` still records the source name 'kb'."""
        tree = _parse("from . import kb as K\n")
        # We record the source name, not the alias target — that's what
        # rules #3/#4 actually need to assert against the lib-name table.
        assert "kb" in _imports_modules(tree)

    def test_relative_with_module_records_module_name(self):
        """`from .kb import X` records 'kb' — covered by the existing
        path because node.module='kb'."""
        tree = _parse("from .kb import advise\n")
        assert "kb" in _imports_modules(tree)

    def test_double_relative_bare_import(self):
        """`from .. import x` (parent-relative) also records 'x'."""
        tree = _parse("from .. import kb\n")
        assert "kb" in _imports_modules(tree)


class TestR2RagFacadeIsSoleChokePoint:
    """Codex R1 HIGH: previously _FACADE_NAMES allowed both rag_facade
    and agent_facade; the ADR says only rag_facade."""

    def test_facade_constant_is_only_rag_facade(self):
        assert _RAG_FACADE_NAME == "rag_facade.py"

    def test_agent_facade_is_not_a_legal_rag_import_site(self):
        """Synthetic check: a hypothetical agent_facade.py importing
        backend.app.rag.* must be a violation under the R2 contract."""
        # The actual file-walk happens in the integration test
        # `test_only_rag_facade_imports_rag_from_workbench`. This
        # synthetic test pins the constant so a future PR can't
        # silently re-include agent_facade.py.
        assert _RAG_FACADE_NAME != "agent_facade.py"
