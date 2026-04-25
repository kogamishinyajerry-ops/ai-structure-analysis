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
5. **Singleton policy** (ADR §97-108): `rag_facade.py` uses the
   `kb.get_kb()` startup-singleton accessor and does NOT (a) take a
   per-request `KnowledgeBase` parameter into any public function, nor
   (b) construct `KnowledgeBase(...)` per call. Per-request load is
   ~6 s + 2 GB resident — singleton-only is the contract.

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


# ---------------------------------------------------------------------------
# Rule #5 — Singleton policy for KnowledgeBase (ADR §97-108)
#
# R3 (post Codex R3 MEDIUM): the ADR explicitly promises a discipline
# test asserting the workbench does NOT take a per-request KnowledgeBase
# parameter into the facade — only the singleton accessor `kb.get_kb()`.
# The R2 test file omitted this rule entirely; Codex R3 flagged it.
# ---------------------------------------------------------------------------


def _annotation_mentions_knowledgebase(node: ast.AST | None) -> bool:
    """True if a function-parameter annotation references `KnowledgeBase`.

    Catches:
      - `kb: KnowledgeBase`
      - `kb: backend.app.rag.kb.KnowledgeBase`
      - `kb: "KnowledgeBase"` (string-form forward ref)
      - `kb: Optional[KnowledgeBase]` / `kb: KnowledgeBase | None`
    """
    if node is None:
        return False
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id == "KnowledgeBase":
            return True
        if isinstance(sub, ast.Attribute) and sub.attr == "KnowledgeBase":
            return True
        # forward-ref strings: `kb: "KnowledgeBase"` or `"Optional[KnowledgeBase]"`
        if (
            isinstance(sub, ast.Constant)
            and isinstance(sub.value, str)
            and "KnowledgeBase" in sub.value
        ):
            return True
    return False


def _function_takes_knowledgebase_param(fn: ast.AST) -> bool:
    """True if any function arg/kwarg in fn is annotated as KnowledgeBase."""
    if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
        return False
    args = fn.args
    all_args = (
        list(args.posonlyargs)
        + list(args.args)
        + list(args.kwonlyargs)
        + ([args.vararg] if args.vararg else [])
        + ([args.kwarg] if args.kwarg else [])
    )
    return any(a is not None and _annotation_mentions_knowledgebase(a.annotation) for a in all_args)


def _calls_knowledgebase_constructor(tree: ast.AST) -> bool:
    """True if the module body has `KnowledgeBase(...)` constructor calls.

    `kb.get_kb()` is fine; `KnowledgeBase()` or `kb.KnowledgeBase()` is not
    (per-call construction defeats the singleton).
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "KnowledgeBase":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "KnowledgeBase":
            return True
    return False


def _calls_get_kb_singleton(tree: ast.AST) -> bool:
    """True if the module references `get_kb` as a callable.

    Accepts `get_kb()` (after `from .kb import get_kb`) or `kb.get_kb()`
    (after `from backend.app.rag import kb`). The actual choice of import
    style is left to the implementer; we just check it's invoked.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "get_kb":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "get_kb":
            return True
    return False


def test_rag_facade_uses_singleton_accessor():
    """ADR-017 §97-108: rag_facade.py must use `kb.get_kb()` singleton.

    This pins the architectural decision from Notion 2026-04-26 Q3:
    BGE-M3 loads once at startup; per-request load is ~6 s + 2 GB.
    """
    facade = _WORKBENCH_DIR / _RAG_FACADE_NAME
    if not facade.is_file():
        pytest.skip(f"{facade} does not exist yet — Phase 2.1 follow-up adds it")
    tree = _parse_file(facade)
    assert tree is not None
    assert _calls_get_kb_singleton(tree), (
        f"ADR-017 §97-108 violation — {facade.relative_to(_REPO_ROOT)} must "
        f"invoke `kb.get_kb()` (or `get_kb()` after relative import) to reuse "
        f"the startup-singleton KnowledgeBase. Per-request load is ~6 s + "
        f"2 GB resident; the facade is the gate that enforces the singleton."
    )


def test_rag_facade_does_not_take_knowledgebase_param():
    """ADR-017 §108: facade public functions must not accept KnowledgeBase.

    Taking `kb: KnowledgeBase` as a parameter would let a caller bypass the
    singleton (pass a freshly-constructed KB, defeat the contract). The
    facade reads the singleton via `get_kb()` itself; callers don't pass it.
    """
    facade = _WORKBENCH_DIR / _RAG_FACADE_NAME
    if not facade.is_file():
        pytest.skip(f"{facade} does not exist yet — Phase 2.1 follow-up adds it")
    tree = _parse_file(facade)
    assert tree is not None
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("_"):
                continue  # private helpers may pass KB internally
            if _function_takes_knowledgebase_param(node):
                violations.append(
                    f"{facade.relative_to(_REPO_ROOT)}:{node.lineno}: "
                    f"public function `{node.name}` takes a KnowledgeBase "
                    f"parameter — use `kb.get_kb()` inside the body instead."
                )
    assert not violations, (
        "ADR-017 §108 violation — facade public functions must not accept "
        "KnowledgeBase as a parameter (defeats singleton policy):\n  " + "\n  ".join(violations)
    )


def test_rag_facade_does_not_construct_knowledgebase():
    """ADR-017 §97-108: rag_facade.py must not call `KnowledgeBase(...)`.

    Per-call construction defeats the startup singleton just as effectively
    as taking it via parameter. Only `kb.get_kb()` is the legal accessor.
    """
    facade = _WORKBENCH_DIR / _RAG_FACADE_NAME
    if not facade.is_file():
        pytest.skip(f"{facade} does not exist yet — Phase 2.1 follow-up adds it")
    tree = _parse_file(facade)
    assert tree is not None
    assert not _calls_knowledgebase_constructor(tree), (
        f"ADR-017 §97-108 violation — {facade.relative_to(_REPO_ROOT)} must "
        f"not construct `KnowledgeBase(...)` per call. Use `kb.get_kb()` "
        f"to reuse the startup singleton (~6 s + 2 GB cost otherwise)."
    )


class TestR3SingletonPolicyPredicates:
    """Codex R3 MEDIUM: the ADR §97-108 singleton-policy assertion was
    promised but not implemented in the R2 test file. Pin the predicates
    with synthetic fixtures so they cannot regress silently."""

    def test_param_annotation_bare_name_is_caught(self):
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def advise(query: str, kb: KnowledgeBase) -> dict: ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_param_annotation_dotted_path_is_caught(self):
        tree = _parse(
            "import backend.app.rag.kb\n"
            "def advise(query, kb: backend.app.rag.kb.KnowledgeBase): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_param_annotation_string_forward_ref_is_caught(self):
        tree = _parse('def advise(query: str, kb: "KnowledgeBase") -> dict: ...\n')
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_param_annotation_optional_wrapped_is_caught(self):
        tree = _parse(
            "from typing import Optional\n"
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def advise(query, kb: Optional[KnowledgeBase] = None): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_kwonly_kb_parameter_is_caught(self):
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def advise(query, *, kb: KnowledgeBase): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_unrelated_param_is_ignored(self):
        tree = _parse("def advise(query: str, top_k: int = 3) -> dict: ...\n")
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert not _function_takes_knowledgebase_param(fn)

    def test_lookalike_class_name_is_ignored(self):
        """KnowledgeBaseConfig is NOT KnowledgeBase — must not match."""
        tree = _parse(
            "def advise(query, cfg: KnowledgeBaseConfig): ...\n"  # noqa: F821
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        # KnowledgeBaseConfig is a different Name; bare-name match is exact.
        assert not _function_takes_knowledgebase_param(fn)

    def test_constructor_call_bare_name_is_caught(self):
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n" "def f(): return KnowledgeBase()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_constructor_call_attribute_form_is_caught(self):
        tree = _parse(
            "from backend.app.rag import kb\n" "def f(): return kb.KnowledgeBase(arg=1)\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_get_kb_call_is_not_a_constructor(self):
        """`get_kb()` is the accessor, NOT a constructor — must not match."""
        tree = _parse("from backend.app.rag.kb import get_kb\n" "def f(): return get_kb()\n")
        assert not _calls_knowledgebase_constructor(tree)
        assert _calls_get_kb_singleton(tree)

    def test_get_kb_attribute_form_is_recognized(self):
        tree = _parse("from backend.app.rag import kb\n" "def f(): return kb.get_kb()\n")
        assert _calls_get_kb_singleton(tree)
        assert not _calls_knowledgebase_constructor(tree)

    def test_no_get_kb_in_module_returns_false(self):
        tree = _parse("def f(query): return query\n")
        assert not _calls_get_kb_singleton(tree)

    def test_async_function_param_is_caught(self):
        """FastAPI handlers are async; the predicate must walk async defs."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "async def advise(query, kb: KnowledgeBase): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef))
        assert _function_takes_knowledgebase_param(fn)
