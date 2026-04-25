"""Discipline + parity checks for ADR-017.

Asserts the contract from `docs/adr/ADR-017-rag-facade-cli-lib-parity.md`:

1. Only `rag_facade.py` (R2 fix: SOLE choke point) under
   `backend/app/workbench/` may import `backend.app.rag.*`. agent_facade.py
   does NOT — agents that internally call RAG do so via the agent-internal
   call site, not via the workbench facade.
2. `rag_facade.py` does NOT import `backend.app.rag.*_cli` / `coverage_audit`
   (the facade goes through the library, not the CLI shell).
3. Each CLI module that exists imports its sibling library module (parity:
   CLI is a thin shell over the library, never re-implements logic).
4. No CLI module imports another CLI module's symbols (CLIs compose through
   the library, never through each other's `main()`).
5. **Singleton policy** (ADR §97-108): `rag_facade.py` uses the
   `kb.get_kb()` startup-singleton accessor and does NOT (a) take a
   per-request `KnowledgeBase` parameter into any public function, nor
   (b) construct `KnowledgeBase(...)` per call (R4: through any aliased
   name resolved from imports/assignments — `KnowledgeBase as KB; KB()`,
   `cls = KnowledgeBase; cls()`, etc.). Per-request load is ~6 s + 2 GB
   resident — singleton-only is the contract.

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
      - `kb: typing.Annotated[KnowledgeBase, ...]`
      - `kb: List[KnowledgeBase]`

    R4 narrowing (post Codex R4 LOW): `type[KnowledgeBase]` is a class
    object reference, NOT an instance — passing the class through is not
    a singleton bypass. We skip the inner walk under any `type[...]` /
    `Type[...]` subscript so this annotation pattern is allowed.
    """
    if node is None:
        return False
    # R4: skip inside type[X] / Type[X] subscripts. The annotation `cls:
    # type[KnowledgeBase]` says "any subclass of KB", not "an instance" —
    # accepting the class doesn't load the model.
    skip_nodes: set[int] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript):
            value = sub.value
            is_type_subscript = (isinstance(value, ast.Name) and value.id in ("type", "Type")) or (
                isinstance(value, ast.Attribute) and value.attr in ("type", "Type")
            )
            if is_type_subscript:
                # Mark every descendant of the subscript's slice as skip.
                slc = sub.slice
                for inner in ast.walk(slc):
                    skip_nodes.add(id(inner))
    for sub in ast.walk(node):
        if id(sub) in skip_nodes:
            continue
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


def _knowledgebase_local_aliases(tree: ast.AST) -> set[str]:
    """Collect every local name that resolves to `KnowledgeBase`.

    R4 hardening (post Codex R4 MEDIUM): the R3 ctor predicate only
    matched the literal name `KnowledgeBase`. Codex showed three live
    bypasses:

      from .kb import KnowledgeBase as KB    →  KB() is a ctor call
      cls = KnowledgeBase                    →  cls() is a ctor call
      from backend.app.rag.kb import (KnowledgeBase as KB)

    This function collects the bound local names so the caller can flag
    `Name(id=...)` calls whose id is in the alias set.
    """
    aliases: set[str] = set()
    # 1. Imports: `from <mod> import KnowledgeBase [as X]`
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "KnowledgeBase":
                    aliases.add(alias.asname or alias.name)
    # 2. Simple module-level assignments: `cls = KnowledgeBase`
    #    (only Name targets; complex unpacking is skipped — vanishingly
    #    rare in a 100-line facade and the facade has private helpers
    #    excluded from public-API checks anyway.)
    # R5 (post Codex R4 R5 MEDIUM): always seed `KnowledgeBase` itself.
    # Codex repro: `from backend.app.rag.kb import *; KB = KnowledgeBase`
    # — star-import binds `KnowledgeBase` without an explicit `import as`,
    # so the import-walk doesn't seed it. Without seeding, `KB =
    # KnowledgeBase` doesn't propagate. Always seeding ensures the
    # assignment chain works regardless of how `KnowledgeBase` came to
    # be in scope.
    seen_aliases = set(aliases) | {"KnowledgeBase"}

    def _value_resolves_to_alias(value: ast.AST) -> bool:
        """True if `value` either is or might be a known KB alias.

        R6 (post Codex R5 MEDIUM): handles three RHS shapes —
        - `cls = KnowledgeBase`                       → bare Name
        - `KB = KnowledgeBase if cond else AltClass`  → IfExp
        - `KB := KnowledgeBase`                       → NamedExpr value
        For IfExp, conservatively flag if EITHER branch matches; a
        statically-undecidable conditional must err toward catching the
        bypass, not letting it through.
        """
        if isinstance(value, ast.Name):
            return value.id in seen_aliases
        if isinstance(value, ast.IfExp):
            return _value_resolves_to_alias(value.body) or _value_resolves_to_alias(value.orelse)
        if isinstance(value, ast.NamedExpr):  # `(KB := KnowledgeBase)`
            return _value_resolves_to_alias(value.value)
        return False

    # Multi-pass to follow chains: `cls = KnowledgeBase; cls2 = cls`.
    for _ in range(8):  # bounded fixpoint
        before = len(seen_aliases)
        for node in ast.walk(tree):
            # Plain `target = value` assignment.
            if isinstance(node, ast.Assign):
                if not _value_resolves_to_alias(node.value):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        seen_aliases.add(target.id)
            # `(target := value)` — walrus expression. Add target name
            # to the alias set so subsequent `target()` is flagged.
            elif isinstance(node, ast.NamedExpr):
                if isinstance(node.target, ast.Name) and _value_resolves_to_alias(node.value):
                    seen_aliases.add(node.target.id)
        if len(seen_aliases) == before:
            break
    return seen_aliases


def _calls_knowledgebase_constructor(tree: ast.AST) -> bool:
    """True if the module body constructs `KnowledgeBase(...)` per call.

    R4 hardening (post Codex R4 MEDIUM): resolves aliases and assignments
    so renamed/aliased constructor calls are also caught:

      `from .kb import KnowledgeBase as KB; KB()` → caught
      `cls = KnowledgeBase; cls()` → caught
      `cls2 = cls; cls2()` → caught (multi-hop chain)

    Reflective calls like `globals()["KnowledgeBase"]()` remain a known
    blind spot for any pure-AST predicate. The discipline test is a
    deterrent, not a sandbox.
    """
    aliases = _knowledgebase_local_aliases(tree) | {"KnowledgeBase"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in aliases:
            return True
        # `kb.KnowledgeBase()` style — attribute always pinned to the
        # class name itself, regardless of the parent module's binding.
        if isinstance(func, ast.Attribute) and func.attr == "KnowledgeBase":
            return True
        # R6 (post Codex R5 LOW): `(KB := KnowledgeBase)()` — Call.func
        # is a NamedExpr whose value resolves to a KB alias. The walrus
        # binds KB AND immediately calls it; both halves are caught
        # here (the alias-walk also adds KB for downstream use).
        if isinstance(func, ast.NamedExpr):
            inner = func.value
            if isinstance(inner, ast.Name) and inner.id in aliases:
                return True
            if isinstance(inner, ast.Attribute) and inner.attr == "KnowledgeBase":
                return True
    return False


def _calls_get_kb_singleton(tree: ast.AST) -> bool:
    """True if the module invokes the rag.kb singleton accessor `get_kb()`.

    R4 hardening (post Codex R4 MEDIUM): provenance-aware. A locally
    defined `def get_kb()` that wraps `KnowledgeBase()` would otherwise
    let the singleton check pass while the facade still constructs a
    fresh KB per call. The fix:

      - Reject the singleton check if there is a local `def get_kb` AND
        no `get_kb` import from `backend.app.rag(.kb)?`.
      - Accept `get_kb()` only when its provenance traces to the rag
        package: either imported as `from backend.app.rag.kb import
        get_kb` / `from .kb import get_kb` / `from backend.app.rag
        import kb` (then `kb.get_kb()`).

    Matches both `get_kb()` and `kb.get_kb()` invocation forms once
    provenance is satisfied. `getattr(kb, "get_kb")()` is still NOT
    accepted — it's syntactically opaque and any real facade can spell
    the call directly.
    """
    # Collect import provenance for `get_kb` and for the `kb` module name.
    get_kb_imported_from_rag = False
    rag_kb_module_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            level = node.level or 0
            # Absolute: `from backend.app.rag.kb import get_kb`
            #           `from backend.app.rag import kb`
            # Relative: `from .kb import get_kb`, `from . import kb`
            from_rag_kb_module = mod == "backend.app.rag.kb" or (level >= 1 and mod == "kb")
            from_rag_pkg = mod == "backend.app.rag" or (level >= 1 and mod == "")
            for alias in node.names:
                if from_rag_kb_module and alias.name == "get_kb":
                    get_kb_imported_from_rag = True
                if from_rag_pkg and alias.name == "kb":
                    rag_kb_module_aliases.add(alias.asname or alias.name)

    # Detect a MODULE-LEVEL local `def get_kb` shadow.
    # R5 (post Codex R4 R5 LOW): scan only top-level definitions, not
    # nested class methods. Codex repro: `class Helper: def get_kb(self):
    # ...` — `ast.walk` would have flagged this even though only
    # module-level shadows defeat the singleton import. Only check
    # tree.body (Module-level FunctionDef nodes).
    module_body = getattr(tree, "body", [])
    locally_defined_get_kb = any(
        isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == "get_kb"
        for n in module_body
    )
    if locally_defined_get_kb and not get_kb_imported_from_rag:
        return False  # singleton-shadow bypass — fail closed

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Bare `get_kb()` — accept iff imported from rag.kb.
        if isinstance(func, ast.Name) and func.id == "get_kb" and get_kb_imported_from_rag:
            return True
        # `kb.get_kb()` — accept iff `kb` is the rag-package alias.
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "get_kb"
            and isinstance(func.value, ast.Name)
            and func.value.id in rag_kb_module_aliases
        ):
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


# ---------------------------------------------------------------------------
# R4 hardening — alias/shadow + type[X] + provenance (post Codex R4 MEDIUM/LOW)
#
# Codex R4 found three live bypasses for the R3 predicates:
# (a) MEDIUM: `from .kb import KnowledgeBase as KB; def get_kb(): return KB();
#     def f(): return get_kb()` defeated all three predicates because the R3
#     ctor check matched only the literal name `KnowledgeBase` and the
#     R3 get_kb check accepted any name `get_kb` regardless of provenance.
# (b) LOW: `kb: type[KnowledgeBase]` was flagged the same as `kb:
#     KnowledgeBase` even though it accepts a class object, not an instance.
# (c) LOW: docstring still mentioned `agent_facade.py`.
#
# R4 fix:
# - _knowledgebase_local_aliases() resolves imports + simple assignments.
# - _calls_knowledgebase_constructor() flags any aliased ctor.
# - _calls_get_kb_singleton() is provenance-aware (rejects local-shadow,
#   requires get_kb to come from backend.app.rag.kb / .kb / rag pkg).
# - _annotation_mentions_knowledgebase() skips inside type[...] subscripts.
# ---------------------------------------------------------------------------


class TestR4AliasShadowBypass:
    """The exact bypass classes Codex R4 reproduced live."""

    def test_codex_r4_local_get_kb_shadow_bypass_is_caught(self):
        """The Codex R4 repro:
            from .kb import KnowledgeBase as KB
            def get_kb(): return KB()
            def advise(q): return get_kb()
        Pre-R4 all three predicates passed. Post-R4 the ctor check sees
        KB() as a constructor AND the singleton check fails closed because
        a local def get_kb shadows without a get_kb import."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase as KB\n"
            "def get_kb(): return KB()\n"
            "def advise(q): return get_kb()\n"
        )
        assert _calls_knowledgebase_constructor(tree)  # KB() flagged
        assert not _calls_get_kb_singleton(tree)  # local shadow rejected

    def test_alias_imported_constructor_is_caught(self):
        """`from x import KnowledgeBase as KB; KB()` — must catch alias."""
        tree = _parse("from backend.app.rag.kb import KnowledgeBase as KB\nKB()\n")
        assert _calls_knowledgebase_constructor(tree)

    def test_assigned_alias_constructor_is_caught(self):
        """`cls = KnowledgeBase; cls()` — chain via assignment."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "cls = KnowledgeBase\n"
            "def f(): return cls()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_multi_hop_alias_chain_is_caught(self):
        """`a = KnowledgeBase; b = a; b()` — multi-step chain."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "a = KnowledgeBase\n"
            "b = a\n"
            "c = b\n"
            "def f(): return c()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_locally_defined_get_kb_without_import_is_rejected(self):
        """A local `def get_kb` and no rag import = singleton bypass."""
        tree = _parse("def get_kb(): return object()\n" "def advise(q): return get_kb()\n")
        assert not _calls_get_kb_singleton(tree)

    def test_get_kb_imported_from_rag_kb_is_accepted(self):
        """Bare get_kb() with proper import is accepted."""
        tree = _parse("from backend.app.rag.kb import get_kb\ndef f(): return get_kb()\n")
        assert _calls_get_kb_singleton(tree)

    def test_get_kb_via_kb_module_attribute_is_accepted(self):
        """`from backend.app.rag import kb; kb.get_kb()` is accepted."""
        tree = _parse("from backend.app.rag import kb\ndef f(): return kb.get_kb()\n")
        assert _calls_get_kb_singleton(tree)

    def test_get_kb_via_relative_import_is_accepted(self):
        """`from .kb import get_kb; get_kb()` is accepted."""
        tree = _parse("from .kb import get_kb\ndef f(): return get_kb()\n")
        assert _calls_get_kb_singleton(tree)

    def test_kb_get_kb_with_unrelated_kb_alias_is_rejected(self):
        """`kb` shadowed as a local variable that's not the rag module
        must NOT count as a singleton call."""
        tree = _parse(
            "class kb:\n    @staticmethod\n    def get_kb(): pass\n" "def f(): return kb.get_kb()\n"
        )
        assert not _calls_get_kb_singleton(tree)

    def test_getattr_pattern_is_not_accepted(self):
        """Documented as a known LOW: `getattr(kb, 'get_kb')()` is too
        opaque to verify statically. The predicate stays syntax-pinned."""
        tree = _parse(
            "from backend.app.rag import kb\n" "def f(): return getattr(kb, 'get_kb')()\n"
        )
        assert not _calls_get_kb_singleton(tree)


class TestR4TypeSubscriptNarrowing:
    """`type[KnowledgeBase]` is a class object — accepting it is not a
    singleton bypass. R4 narrows _annotation_mentions_knowledgebase to
    skip inside type[...] / Type[...] subscripts."""

    def test_type_lower_bracket_knowledgebase_is_allowed(self):
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def f(cls: type[KnowledgeBase]): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert not _function_takes_knowledgebase_param(fn)

    def test_typing_Type_capital_knowledgebase_is_allowed(self):
        tree = _parse(
            "from typing import Type\n"
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def f(cls: Type[KnowledgeBase]): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert not _function_takes_knowledgebase_param(fn)

    def test_bare_knowledgebase_still_caught_when_type_also_used(self):
        """Defensive: a function with BOTH `type[KB]` and a bare KB param
        must still be flagged for the bare param."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def f(cls: type[KnowledgeBase], kb: KnowledgeBase): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_typing_annotated_knowledgebase_still_caught(self):
        """`Annotated[KnowledgeBase, ...]` carries a real instance — must
        still be caught (not narrowed by R4)."""
        tree = _parse(
            "from typing import Annotated\n"
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def f(kb: Annotated[KnowledgeBase, 'fast']): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_list_knowledgebase_still_caught(self):
        """`List[KnowledgeBase]` is an instance container — must still be
        caught (not narrowed by R4)."""
        tree = _parse(
            "from typing import List\n"
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def f(pool: List[KnowledgeBase]): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)


class TestR4DocstringConsistency:
    """Codex R4 LOW: docstring formerly said agent_facade.py may import
    RAG, contradicting the R2 enforcement at line ~120. R4 docstring
    explicitly names rag_facade.py as the SOLE choke point."""

    def test_docstring_does_not_say_agent_facade_may_import_rag(self):
        path = _REPO_ROOT / "tests" / "test_rag_facade_parity.py"
        text = path.read_text(encoding="utf-8")
        # The first 30 lines are the module docstring.
        head = "\n".join(text.splitlines()[:30])
        assert "and `agent_facade.py`" not in head, (
            "Module docstring still claims agent_facade.py may import RAG; "
            "that contradicts the R2 'sole choke point' enforcement."
        )

    def test_docstring_states_sole_choke_point(self):
        path = _REPO_ROOT / "tests" / "test_rag_facade_parity.py"
        text = path.read_text(encoding="utf-8")
        head = "\n".join(text.splitlines()[:30])
        assert "SOLE choke point" in head


# ---------------------------------------------------------------------------
# R5 hardening — star-import + class-method false negative (post Codex R4 R5)
#
# Codex R4 R5 found:
# - MEDIUM: `from backend.app.rag.kb import *; KB = KnowledgeBase; KB()`
#   bypassed _calls_knowledgebase_constructor because the alias-walk
#   only seeded names from explicit `import KnowledgeBase` constructs.
# - LOW: a class method `def get_kb(self)` (e.g., `class Helper:
#   def get_kb(self): ...`) caused `_calls_get_kb_singleton()` to
#   falsely reject a legitimate `kb.get_kb()` usage in the module.
#
# R5 fix:
# - _knowledgebase_local_aliases() now ALWAYS seeds the assignment
#   chain with `KnowledgeBase` itself, so `KB = KnowledgeBase` works
#   regardless of how `KnowledgeBase` came into scope (star-import,
#   explicit import, etc.).
# - _calls_get_kb_singleton() restricts the locally-defined-get_kb
#   shadow check to MODULE-LEVEL functions (tree.body), not all
#   FunctionDef nodes. Class methods and nested defs no longer
#   trigger false rejection.
# ---------------------------------------------------------------------------


class TestR5StarImportAndClassMethod:
    """The two Codex R4 R5 repros."""

    def test_codex_r5_star_import_with_assigned_alias_is_caught(self):
        """The exact Codex R4 R5 MEDIUM repro:
            from backend.app.rag.kb import *
            KB = KnowledgeBase
            def advise(q): return KB()
        Pre-R5: alias-walk seed missed `KnowledgeBase` (no `import as`),
        so `KB` chain didn't propagate, ctor=False. Post-R5: always-seed
        catches the assignment chain and `KB()` is flagged."""
        tree = _parse(
            "from backend.app.rag.kb import *\n"
            "KB = KnowledgeBase\n"
            "def advise(q): return KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_codex_r5_star_import_full_repro_yields_violation(self):
        """The full Codex repro (also has kb.get_kb() before KB()):
            from backend.app.rag import kb
            from backend.app.rag.kb import *
            KB = KnowledgeBase
            def advise(q):
                kb.get_kb()
                return KB()
        Singleton check passes (real kb.get_kb call), but the ctor
        check now FLAGS this — exactly the right outcome."""
        tree = _parse(
            "from backend.app.rag import kb\n"
            "from backend.app.rag.kb import *\n"
            "KB = KnowledgeBase\n"
            "def advise(q):\n"
            "    kb.get_kb()\n"
            "    return KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)
        assert _calls_get_kb_singleton(tree)  # the real call still detected

    def test_r5_star_import_direct_constructor_is_caught(self):
        """`from .kb import *; KnowledgeBase()` — direct call, no alias."""
        tree = _parse("from backend.app.rag.kb import *\nKnowledgeBase()\n")
        assert _calls_knowledgebase_constructor(tree)

    def test_codex_r5_class_method_get_kb_does_not_shadow(self):
        """The exact Codex R4 R5 LOW repro:
            from backend.app.rag import kb
            class Helper:
                def get_kb(self): return 1
            def advise(q): return kb.get_kb()
        Pre-R5: ast.walk found Helper.get_kb method and falsely set
        locally_defined_get_kb=True → singleton check rejected.
        Post-R5: only module-level defs scanned, so kb.get_kb() passes."""
        tree = _parse(
            "from backend.app.rag import kb\n"
            "class Helper:\n"
            "    def get_kb(self): return 1\n"
            "def advise(q): return kb.get_kb()\n"
        )
        assert _calls_get_kb_singleton(tree)

    def test_r5_nested_function_get_kb_does_not_shadow(self):
        """A nested `def get_kb` inside another function does not shadow
        the module-level singleton import either."""
        tree = _parse(
            "from backend.app.rag import kb\n"
            "def outer():\n"
            "    def get_kb(): return 1\n"
            "    return get_kb()\n"
            "def advise(q): return kb.get_kb()\n"
        )
        assert _calls_get_kb_singleton(tree)

    def test_r5_module_level_get_kb_shadow_is_still_rejected(self):
        """Regression guard: module-level `def get_kb` MUST still be
        flagged as a shadow, even after the class-method narrowing."""
        tree = _parse("def get_kb(): return 1\n" "def advise(q): return get_kb()\n")
        assert not _calls_get_kb_singleton(tree)

    def test_r5_async_module_level_get_kb_shadow_is_rejected(self):
        """`async def get_kb` at module level is also a shadow."""
        tree = _parse(
            "async def get_kb(): return 1\n" "async def advise(q): return await get_kb()\n"
        )
        assert not _calls_get_kb_singleton(tree)

    def test_r5_class_method_does_not_block_real_get_kb_import(self):
        """Even if the class method is named get_kb AND a real import
        of get_kb exists, the singleton check should pass (the real
        import takes precedence; the method is in a different scope)."""
        tree = _parse(
            "from backend.app.rag.kb import get_kb\n"
            "class Helper:\n"
            "    def get_kb(self): return 1\n"
            "def advise(q): return get_kb()\n"
        )
        assert _calls_get_kb_singleton(tree)

    def test_r5_assignment_chain_after_star_import(self):
        """Multi-hop chain post star-import: `import *; a=KB; b=a; b()`."""
        tree = _parse(
            "from backend.app.rag.kb import *\n"
            "a = KnowledgeBase\n"
            "b = a\n"
            "c = b\n"
            "def f(): return c()\n"
        )
        assert _calls_knowledgebase_constructor(tree)


# ---------------------------------------------------------------------------
# R6 hardening — IfExp + walrus alias forms (post Codex R5 R6 MEDIUM/LOW)
#
# Codex R5 R6 found two more alias forms the alias-walk missed:
# - MEDIUM: `KB = KnowledgeBase if cond else AltClass; KB()` — IfExp
#   value not propagated; the assignment-walk only matched bare Name.
# - LOW: `(KB := KnowledgeBase)()` — walrus expression as Call.func
#   on Python 3.8+ (repo's floor is 3.11). Neither the alias-walk nor
#   the constructor scan recognised NamedExpr.
#
# R6 fix:
# - _knowledgebase_local_aliases() recurses through IfExp.body /
#   IfExp.orelse / NamedExpr.value to detect either-branch matches
#   (conservative: flag if EITHER side resolves to a KB alias).
# - _knowledgebase_local_aliases() also walks `target := value`
#   NamedExpr nodes and binds the target to the alias set.
# - _calls_knowledgebase_constructor() also recognises `Call.func` as
#   `NamedExpr` whose `.value` resolves to a KB alias — catches the
#   in-place call form `(KB := KnowledgeBase)()`.
# ---------------------------------------------------------------------------


class TestR6IfExpAndWalrusAliases:
    """Codex R5 R6 repros for the two new alias forms."""

    def test_codex_r6_ifexp_alias_either_branch_is_caught(self):
        """The exact Codex R5 R6 MEDIUM repro:
            from backend.app.rag.kb import KnowledgeBase
            KB = KnowledgeBase if cond else AltClass
            def advise(q): return KB()
        Pre-R6: KB binding from IfExp not propagated. Post-R6:
        IfExp.body/orelse walked; if EITHER resolves to a KB alias,
        target is bound."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "KB = KnowledgeBase if cond else AltClass\n"
            "def advise(q): return KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_ifexp_with_kb_in_orelse_is_caught(self):
        """KB on the orelse branch only (still must flag — conservative)."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "KB = AltClass if cond else KnowledgeBase\n"
            "def f(): return KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_ifexp_with_neither_branch_is_kb_is_not_flagged(self):
        """Both branches non-KB → no false positive."""
        tree = _parse("Foo = AltClass if cond else OtherClass\n" "def f(): return Foo()\n")
        assert not _calls_knowledgebase_constructor(tree)

    def test_r6_nested_ifexp_chain_is_caught(self):
        """`a = X if c1 else (Y if c2 else KnowledgeBase); a()`."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "a = X if c1 else (Y if c2 else KnowledgeBase)\n"
            "def f(): return a()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_codex_r6_walrus_call_is_caught(self):
        """The exact Codex R5 R6 LOW repro: `(KB := KnowledgeBase)()`.
        The walrus binds AND immediately calls; the call's func is
        NamedExpr whose value is the KB alias."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def f(): return (KB := KnowledgeBase)()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_walrus_call_via_aliased_name_is_caught(self):
        """`(KB := AnotherAlias)()` after `AnotherAlias = KnowledgeBase`."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "AnotherAlias = KnowledgeBase\n"
            "def f(): return (KB := AnotherAlias)()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_walrus_assignment_propagates_alias(self):
        """`(KB := KnowledgeBase); KB()` — walrus binds KB, later
        bare-name call is also flagged via the aliases set."""
        tree = _parse(
            "from backend.app.rag.kb import KnowledgeBase\n"
            "def f():\n"
            "    (KB := KnowledgeBase)\n"
            "    return KB()\n"
        )
        # The alias-walk binds KB; subsequent KB() call flagged.
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_walrus_with_non_kb_value_is_not_flagged(self):
        """`(KB := AltClass)()` — KB is not a KB alias, no false flag."""
        tree = _parse("def f(): return (KB := AltClass)()\n")
        assert not _calls_knowledgebase_constructor(tree)

    def test_r6_walrus_attribute_form_is_caught(self):
        """`(K := kb.KnowledgeBase)()` — attribute-form via walrus."""
        tree = _parse(
            "from backend.app.rag import kb\n" "def f(): return (K := kb.KnowledgeBase)()\n"
        )
        assert _calls_knowledgebase_constructor(tree)
