"""Discipline + parity checks for ADR-017.

Asserts the contract from `docs/adr/ADR-017-rag-facade-cli-lib-parity.md`:

1. Only `rag_facade.py` (R2 fix: SOLE choke point) under
   `backend/app/workbench/` may import `app.rag.*`. agent_facade.py
   does NOT — agents that internally call RAG do so via the agent-internal
   call site, not via the workbench facade.
2. `rag_facade.py` does NOT import `app.rag.*_cli` / `coverage_audit`
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
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WORKBENCH_DIR = _REPO_ROOT / "backend" / "app" / "workbench"
_RAG_DIR = _REPO_ROOT / "backend" / "app" / "rag"
# R2 (post Codex R1 HIGH): the choke point is ONLY rag_facade.py.
# agent_facade.py imports agents.*, but if an agent internally calls
# app.rag.* that's the agent's concern — agent_facade itself
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
    "app.rag.cli",
    "app.rag.query_cli",
    "app.rag.advise_cli",
    "app.rag.preflight_publish_cli",
    "app.rag.coverage_audit",  # CLI-shaped audit tool
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _module_predicate_from_rag(module: str | None) -> bool:
    if module is None:
        return False
    return module == "app.rag" or module.startswith("app.rag.")


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
# Rule #1 — only facade modules import app.rag.* from workbench
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
        "ADR-017 violation — ONLY rag_facade.py may import app.rag.* "
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
        # The CLI may import via `from app.rag.<lib> import …` or
        # `from .<lib> import …` (relative). Accept either.
        lib_stem = lib_name[: -len(".py")]
        absolute = f"app.rag.{lib_stem}"
        relative_targets = {lib_stem}  # `from .<lib_stem> import …`
        ok = absolute in imported or any(t in imported for t in relative_targets)
        # Also accept any module starting with `app.rag.<lib_stem>`
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
    cli_module_names = {f"app.rag.{name[: -len('.py')]}" for name in cli_filenames}
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
        own_module = f"app.rag.{cli_name[: -len('.py')]}"
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
        tree = _parse("from app.rag.reviewer_advisor import advise\n")
        assert any(_module_predicate_from_rag(m) for m in _imports_modules(tree))

    def test_bare_import_rag_subpackage_is_caught(self):
        tree = _parse("import app.rag.kb\n")
        # `_imports_modules` records the bare-import target as the full name
        names = _imports_modules(tree)
        assert any(_module_predicate_from_rag(n) for n in names)

    def test_unrelated_rag_lookalike_is_ignored(self):
        # `app.ragout` must NOT match `app.rag.*`
        tree = _parse("from app.ragout import helper\n")
        names = _imports_modules(tree)
        assert not any(_module_predicate_from_rag(n) for n in names)

    def test_relative_import_records_module(self):
        tree = _parse("from .reviewer_advisor import advise\n")
        names = _imports_modules(tree)
        assert "reviewer_advisor" in names

    def test_forbidden_facade_set_recognizes_cli_modules(self):
        for name in _FORBIDDEN_FACADE_IMPORTS:
            assert name.startswith("app.rag.")
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
        app.rag.* must be a violation under the R2 contract."""
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


def _annotation_mentions_knowledgebase(
    node: ast.AST | None,
    aliases: set[str] | None = None,
    rag_module_aliases: set[str] | None = None,
) -> bool:
    """True if a function-parameter annotation references `KnowledgeBase`.

    Catches:
      - `kb: KnowledgeBase`
      - `kb: app.rag.kb.KnowledgeBase`
      - `kb: "KnowledgeBase"` (string-form forward ref)
      - `kb: Optional[KnowledgeBase]` / `kb: KnowledgeBase | None`
      - `kb: typing.Annotated[KnowledgeBase, ...]`
      - `kb: List[KnowledgeBase]`

    R4 narrowing (post Codex R4 LOW): `type[KnowledgeBase]` is a class
    object reference, NOT an instance — passing the class through is not
    a singleton bypass. We skip the inner walk under any `type[...]` /
    `Type[...]` subscript so this annotation pattern is allowed.

    R7 hardening (post Codex R4-verification MEDIUM, 2026-04-28): accepts
    a precomputed alias set so renamed imports and KB subclasses are also
    recognised in annotations. Codex repro that exposed the gap:

        from app.rag.kb import KnowledgeBase as KB
        def advise(kb: KB): ...                      # bypasses the
                                                       # literal-name match

        class MyKB(KnowledgeBase): pass
        def advise(kb: MyKB): ...                    # subclass annotation

    The caller passes the alias set built by `_knowledgebase_local_aliases`
    so all three predicates share one resolution policy.

    R7-fix2 (post Codex R1 MEDIUM, 2026-04-28): forward-ref strings now
    also match alias names via word-boundary regex. `def advise(kb: "KB")`
    matches when KB is in aliases; `"KBConfig"` does NOT (\\b anchors).

    R7-fix3 (post Codex R2 MEDIUM, 2026-04-28): the Attribute branch is
    provenance-aware. Literal `<x>.KnowledgeBase` always flags. Alias
    attribute (`<x>.KB`) only flags when the leftmost Name is in
    `rag_module_aliases` — `rag.kb.KB` is genuinely the same class
    via re-export but `obj.MyKB` (where obj is unrelated) does not flag.
    """
    if node is None:
        return False
    name_set = {"KnowledgeBase"} | (aliases or set())
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
    # R7-fix2 (post Codex R1 MEDIUM, 2026-04-28): forward-ref strings
    # must also match alias names. Pre-fix the string branch only matched
    # substrings of the literal "KnowledgeBase", so `def advise(kb: "KB")`
    # where KB is an aliased import slipped through. Use word-boundary
    # matching so `"KBConfig"` does not false-flag.
    string_pattern: re.Pattern[str] | None = None
    if name_set:
        # `re.escape` so alias names containing regex metachars are safe.
        # Alternation is anchored with \b on both sides.
        string_pattern = re.compile(r"\b(?:" + "|".join(re.escape(n) for n in name_set) + r")\b")
    for sub in ast.walk(node):
        if id(sub) in skip_nodes:
            continue
        if isinstance(sub, ast.Name) and sub.id in name_set:
            return True
        # Attribute branch. R7-fix3 (post Codex R2 MEDIUM, 2026-04-28):
        # provenance-aware. The literal class name `KnowledgeBase` is
        # always a hit (it's the canonical class identifier). For
        # aliases, only flag when the leftmost Name in the chain is a
        # known rag-module alias — `rag.kb.KB` is genuinely the same
        # KB if `rag.kb` is the rag.kb module, but `obj.MyKB` where
        # `obj` is an unrelated runtime object must not flag.
        if isinstance(sub, ast.Attribute):
            if sub.attr == "KnowledgeBase":
                return True
            if (
                sub.attr in name_set
                and rag_module_aliases is not None
                and _attribute_root_name(sub) in rag_module_aliases
            ):
                return True
        # forward-ref strings: `kb: "KnowledgeBase"` or `"Optional[KB]"`
        if (
            isinstance(sub, ast.Constant)
            and isinstance(sub.value, str)
            and string_pattern is not None
            and string_pattern.search(sub.value)
        ):
            return True
    return False


def _function_takes_knowledgebase_param(
    fn: ast.AST,
    aliases: set[str] | None = None,
    rag_module_aliases: set[str] | None = None,
) -> bool:
    """True if any function arg/kwarg in fn is annotated as KnowledgeBase.

    R7 hardening (post Codex R4-verification MEDIUM, 2026-04-28): accepts
    an optional alias set so callers that have already walked the
    enclosing module pass it through to `_annotation_mentions_knowledgebase`.
    Without aliases, only the literal name `KnowledgeBase` and dotted-attr
    forms match — alias and subclass annotations evade.

    R7-fix3 (post Codex R2 MEDIUM, 2026-04-28): also threads the rag-
    module alias set into the Attribute branch so provenance-aware
    matching applies to `<rag-module>.<alias>` annotations.
    """
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
    return any(
        a is not None
        and _annotation_mentions_knowledgebase(a.annotation, aliases, rag_module_aliases)
        for a in all_args
    )


def _rag_module_aliases(tree: ast.AST) -> set[str]:
    """Collect local names that resolve to a known rag-package module.

    R7-fix3 (post Codex R2 MEDIUM, 2026-04-28): used as the provenance
    gate for Attribute-form alias matching. Without a provenance check,
    treating any `attr in aliases` as a hit false-flagged unrelated
    attribute access (`some.KB()`, `obj.MyKB()`) once `KB` or `MyKB`
    happened to be in the alias set. We only widen the Attribute branch
    when the leftmost Name resolves to a rag-package module — at that
    point `<rag-module>.<KB-alias>` IS a KnowledgeBase reference under
    a re-exported alias.

    Catches ONLY unambiguous module-import shapes:
      - `import rag` / `import rag.X` (no alias)         → bind `rag`
      - `import <X.rag.Y> as <Q>` (alias)                → bind `Q`

    Explicitly does NOT trust ImportFrom at all. Per Codex R4 finding
    (2026-04-28): Python `from MOD import X` is statically ambiguous
    between submodule import and class/function re-export via
    __init__.py. `from app.rag import KnowledgeBase` re-exports the
    class; `from app.rag import kb` imports the submodule; AST cannot
    tell them apart, so trusting the bound name re-opens provenance
    bypasses (`KB.MyKB()` flagged where KB is a class re-export).

    Known limitations (acceptable conservative bias for a discipline
    test — these are rare shapes in real facade code, and Codex review
    provides post-hoc catches):
      - `from app.rag import kb; kb.KnowledgeBase()` — literal class
        name still flags via the canonical-name branch (provenance-free).
      - `from app.rag import kb; kb.KB()` (alias attribute via member
        import) — does NOT flag because `kb` was never trusted.
      - `from . import kb; kb.X()` — same.

    R7-fix3.2 (post Codex R4 MEDIUM, 2026-04-28).
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias_node in node.names:
            parts = alias_node.name.split(".")
            if alias_node.asname:
                # `import X.Y.Z as Q` — Q binds the full module path;
                # trust if the dotted path contains `rag`.
                if "rag" in parts:
                    aliases.add(alias_node.asname)
            else:
                # `import X.Y.Z` — leftmost X is bound. Trust ONLY
                # when leftmost is literally `rag`. So `import rag`,
                # `import rag.kb` add `rag`; `import app.rag.kb`
                # binds `app` (parent) which is NOT trusted.
                if parts and parts[0] == "rag":
                    aliases.add(parts[0])
    return aliases


def _attribute_root_name(node: ast.AST) -> str | None:
    """Return the leftmost Name id of an Attribute chain, or None.

    For `a.b.c` returns `"a"`; for `a` returns `"a"`; for non-Name roots
    (e.g. `func().attr`) returns None.
    """
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _knowledgebase_local_aliases(tree: ast.AST) -> set[str]:
    """Collect every local name that resolves to `KnowledgeBase`.

    R4 hardening (post Codex R4 MEDIUM): the R3 ctor predicate only
    matched the literal name `KnowledgeBase`. Codex showed three live
    bypasses:

      from .kb import KnowledgeBase as KB    →  KB() is a ctor call
      cls = KnowledgeBase                    →  cls() is a ctor call
      from app.rag.kb import (KnowledgeBase as KB)

    This function collects the bound local names so the caller can flag
    `Name(id=...)` calls whose id is in the alias set.
    """
    aliases: set[str] = set()
    # R7-fix3: provenance gate for the Attribute-form subclass branch.
    rag_module_aliases_local = _rag_module_aliases(tree)
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
    # Codex repro: `from app.rag.kb import *; KB = KnowledgeBase`
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
    # R7 (post Codex R4-verification MEDIUM, 2026-04-28): also fold in
    # subclasses. A subclass of KnowledgeBase is constructable as a KB
    # instance (Liskov), and instances of it ARE KnowledgeBase instances.
    # Codex bypass repro:
    #
    #     class MyKB(KnowledgeBase): pass
    #     def advise(kb: MyKB): ...        # annotation evades literal match
    #     def build(): return MyKB()       # ctor evades literal match
    #
    # We treat any class whose bases reference a known alias as itself an
    # alias. The fixpoint loop already iterates so transitive subclass
    # chains (`class A(KB); class B(A)`) propagate cleanly.
    def _bases_reference_alias(class_def: ast.ClassDef) -> bool:
        for base in class_def.bases:
            if isinstance(base, ast.Name) and base.id in seen_aliases:
                return True
            if isinstance(base, ast.Attribute):
                # `class X(kb.KnowledgeBase)` — literal class name
                # always pinned regardless of leftmost name.
                if base.attr == "KnowledgeBase":
                    return True
                # R7-fix3 (post Codex R2 MEDIUM, 2026-04-28):
                # provenance-aware. Only flag alias-attr base when the
                # leftmost Name is a known rag-module alias. `obj.MyKB`
                # where MyKB is in seen_aliases through unrelated path
                # must NOT flag.
                if (
                    base.attr in seen_aliases
                    and _attribute_root_name(base) in rag_module_aliases_local
                ):
                    return True
        return False

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
            # R7: subclass declaration. `class MyKB(KnowledgeBase)` adds
            # `MyKB` to the alias set so both annotation and ctor checks
            # catch its use downstream.
            elif isinstance(node, ast.ClassDef) and _bases_reference_alias(node):
                seen_aliases.add(node.name)
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
    rag_module_aliases = _rag_module_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in aliases:
            return True
        # `kb.KnowledgeBase()` literal-class always flags. R7-fix3 (post
        # Codex R2 MEDIUM, 2026-04-28): alias-form attribute (`kb.KB()`,
        # `rag.kb.KB()`) only flags when the leftmost Name is a known
        # rag-module alias. This prevents `obj.MyKB()` from false-flagging
        # once MyKB happens to be in the alias set through unrelated path.
        if isinstance(func, ast.Attribute):
            if func.attr == "KnowledgeBase":
                return True
            if func.attr in aliases and _attribute_root_name(func) in rag_module_aliases:
                return True
        # R6 (post Codex R5 LOW): `(KB := KnowledgeBase)()` — Call.func
        # is a NamedExpr whose value resolves to a KB alias. The walrus
        # binds KB AND immediately calls it; both halves are caught
        # here (the alias-walk also adds KB for downstream use).
        if isinstance(func, ast.NamedExpr):
            inner = func.value
            if isinstance(inner, ast.Name) and inner.id in aliases:
                return True
            if isinstance(inner, ast.Attribute):
                if inner.attr == "KnowledgeBase":
                    return True
                if inner.attr in aliases and _attribute_root_name(inner) in rag_module_aliases:
                    return True
    return False


def _calls_get_kb_singleton(tree: ast.AST) -> bool:
    """True if the module invokes the rag.kb singleton accessor `get_kb()`.

    R4 hardening (post Codex R4 MEDIUM): provenance-aware. A locally
    defined `def get_kb()` that wraps `KnowledgeBase()` would otherwise
    let the singleton check pass while the facade still constructs a
    fresh KB per call. The fix:

      - Reject the singleton check if there is a local `def get_kb` AND
        no `get_kb` import from `app.rag(.kb)?`.
      - Accept `get_kb()` only when its provenance traces to the rag
        package: either imported as `from app.rag.kb import
        get_kb` / `from .kb import get_kb` / `from app.rag
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
            # Absolute: `from app.rag.kb import get_kb`
            #           `from app.rag import kb`
            # Relative: `from .kb import get_kb`, `from . import kb`
            from_rag_kb_module = mod == "app.rag.kb" or (level >= 1 and mod == "kb")
            from_rag_pkg = mod == "app.rag" or (level >= 1 and mod == "")
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
    # R7: resolve aliases (renamed imports + subclasses + assignment chains)
    # once per module so annotation matching catches alias forms too.
    # R7-fix3: also resolve rag-module aliases for provenance-aware
    # Attribute-form matching.
    aliases = _knowledgebase_local_aliases(tree)
    rag_module_aliases = _rag_module_aliases(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("_"):
                continue  # private helpers may pass KB internally
            if _function_takes_knowledgebase_param(node, aliases, rag_module_aliases):
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
            "from app.rag.kb import KnowledgeBase\n"
            "def advise(query: str, kb: KnowledgeBase) -> dict: ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_param_annotation_dotted_path_is_caught(self):
        tree = _parse("import app.rag.kb\ndef advise(query, kb: app.rag.kb.KnowledgeBase): ...\n")
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_param_annotation_string_forward_ref_is_caught(self):
        tree = _parse('def advise(query: str, kb: "KnowledgeBase") -> dict: ...\n')
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_param_annotation_optional_wrapped_is_caught(self):
        tree = _parse(
            "from typing import Optional\n"
            "from app.rag.kb import KnowledgeBase\n"
            "def advise(query, kb: Optional[KnowledgeBase] = None): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_kwonly_kb_parameter_is_caught(self):
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\ndef advise(query, *, kb: KnowledgeBase): ...\n"
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
        tree = _parse("from app.rag.kb import KnowledgeBase\ndef f(): return KnowledgeBase()\n")
        assert _calls_knowledgebase_constructor(tree)

    def test_constructor_call_attribute_form_is_caught(self):
        tree = _parse("from app.rag import kb\ndef f(): return kb.KnowledgeBase(arg=1)\n")
        assert _calls_knowledgebase_constructor(tree)

    def test_get_kb_call_is_not_a_constructor(self):
        """`get_kb()` is the accessor, NOT a constructor — must not match."""
        tree = _parse("from app.rag.kb import get_kb\ndef f(): return get_kb()\n")
        assert not _calls_knowledgebase_constructor(tree)
        assert _calls_get_kb_singleton(tree)

    def test_get_kb_attribute_form_is_recognized(self):
        tree = _parse("from app.rag import kb\ndef f(): return kb.get_kb()\n")
        assert _calls_get_kb_singleton(tree)
        assert not _calls_knowledgebase_constructor(tree)

    def test_no_get_kb_in_module_returns_false(self):
        tree = _parse("def f(query): return query\n")
        assert not _calls_get_kb_singleton(tree)

    def test_async_function_param_is_caught(self):
        """FastAPI handlers are async; the predicate must walk async defs."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
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
#   requires get_kb to come from app.rag.kb / .kb / rag pkg).
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
            "from app.rag.kb import KnowledgeBase as KB\n"
            "def get_kb(): return KB()\n"
            "def advise(q): return get_kb()\n"
        )
        assert _calls_knowledgebase_constructor(tree)  # KB() flagged
        assert not _calls_get_kb_singleton(tree)  # local shadow rejected

    def test_alias_imported_constructor_is_caught(self):
        """`from x import KnowledgeBase as KB; KB()` — must catch alias."""
        tree = _parse("from app.rag.kb import KnowledgeBase as KB\nKB()\n")
        assert _calls_knowledgebase_constructor(tree)

    def test_assigned_alias_constructor_is_caught(self):
        """`cls = KnowledgeBase; cls()` — chain via assignment."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\ncls = KnowledgeBase\ndef f(): return cls()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_multi_hop_alias_chain_is_caught(self):
        """`a = KnowledgeBase; b = a; b()` — multi-step chain."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "a = KnowledgeBase\n"
            "b = a\n"
            "c = b\n"
            "def f(): return c()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_locally_defined_get_kb_without_import_is_rejected(self):
        """A local `def get_kb` and no rag import = singleton bypass."""
        tree = _parse("def get_kb(): return object()\ndef advise(q): return get_kb()\n")
        assert not _calls_get_kb_singleton(tree)

    def test_get_kb_imported_from_rag_kb_is_accepted(self):
        """Bare get_kb() with proper import is accepted."""
        tree = _parse("from app.rag.kb import get_kb\ndef f(): return get_kb()\n")
        assert _calls_get_kb_singleton(tree)

    def test_get_kb_via_kb_module_attribute_is_accepted(self):
        """`from app.rag import kb; kb.get_kb()` is accepted."""
        tree = _parse("from app.rag import kb\ndef f(): return kb.get_kb()\n")
        assert _calls_get_kb_singleton(tree)

    def test_get_kb_via_relative_import_is_accepted(self):
        """`from .kb import get_kb; get_kb()` is accepted."""
        tree = _parse("from .kb import get_kb\ndef f(): return get_kb()\n")
        assert _calls_get_kb_singleton(tree)

    def test_kb_get_kb_with_unrelated_kb_alias_is_rejected(self):
        """`kb` shadowed as a local variable that's not the rag module
        must NOT count as a singleton call."""
        tree = _parse(
            "class kb:\n    @staticmethod\n    def get_kb(): pass\ndef f(): return kb.get_kb()\n"
        )
        assert not _calls_get_kb_singleton(tree)

    def test_getattr_pattern_is_not_accepted(self):
        """Documented as a known LOW: `getattr(kb, 'get_kb')()` is too
        opaque to verify statically. The predicate stays syntax-pinned."""
        tree = _parse("from app.rag import kb\ndef f(): return getattr(kb, 'get_kb')()\n")
        assert not _calls_get_kb_singleton(tree)


class TestR4TypeSubscriptNarrowing:
    """`type[KnowledgeBase]` is a class object — accepting it is not a
    singleton bypass. R4 narrows _annotation_mentions_knowledgebase to
    skip inside type[...] / Type[...] subscripts."""

    def test_type_lower_bracket_knowledgebase_is_allowed(self):
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\ndef f(cls: type[KnowledgeBase]): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert not _function_takes_knowledgebase_param(fn)

    def test_typing_Type_capital_knowledgebase_is_allowed(self):
        tree = _parse(
            "from typing import Type\n"
            "from app.rag.kb import KnowledgeBase\n"
            "def f(cls: Type[KnowledgeBase]): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert not _function_takes_knowledgebase_param(fn)

    def test_bare_knowledgebase_still_caught_when_type_also_used(self):
        """Defensive: a function with BOTH `type[KB]` and a bare KB param
        must still be flagged for the bare param."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "def f(cls: type[KnowledgeBase], kb: KnowledgeBase): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_typing_annotated_knowledgebase_still_caught(self):
        """`Annotated[KnowledgeBase, ...]` carries a real instance — must
        still be caught (not narrowed by R4)."""
        tree = _parse(
            "from typing import Annotated\n"
            "from app.rag.kb import KnowledgeBase\n"
            "def f(kb: Annotated[KnowledgeBase, 'fast']): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        assert _function_takes_knowledgebase_param(fn)

    def test_list_knowledgebase_still_caught(self):
        """`List[KnowledgeBase]` is an instance container — must still be
        caught (not narrowed by R4)."""
        tree = _parse(
            "from typing import List\n"
            "from app.rag.kb import KnowledgeBase\n"
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
# - MEDIUM: `from app.rag.kb import *; KB = KnowledgeBase; KB()`
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
            from app.rag.kb import *
            KB = KnowledgeBase
            def advise(q): return KB()
        Pre-R5: alias-walk seed missed `KnowledgeBase` (no `import as`),
        so `KB` chain didn't propagate, ctor=False. Post-R5: always-seed
        catches the assignment chain and `KB()` is flagged."""
        tree = _parse("from app.rag.kb import *\nKB = KnowledgeBase\ndef advise(q): return KB()\n")
        assert _calls_knowledgebase_constructor(tree)

    def test_codex_r5_star_import_full_repro_yields_violation(self):
        """The full Codex repro (also has kb.get_kb() before KB()):
            from app.rag import kb
            from app.rag.kb import *
            KB = KnowledgeBase
            def advise(q):
                kb.get_kb()
                return KB()
        Singleton check passes (real kb.get_kb call), but the ctor
        check now FLAGS this — exactly the right outcome."""
        tree = _parse(
            "from app.rag import kb\n"
            "from app.rag.kb import *\n"
            "KB = KnowledgeBase\n"
            "def advise(q):\n"
            "    kb.get_kb()\n"
            "    return KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)
        assert _calls_get_kb_singleton(tree)  # the real call still detected

    def test_r5_star_import_direct_constructor_is_caught(self):
        """`from .kb import *; KnowledgeBase()` — direct call, no alias."""
        tree = _parse("from app.rag.kb import *\nKnowledgeBase()\n")
        assert _calls_knowledgebase_constructor(tree)

    def test_codex_r5_class_method_get_kb_does_not_shadow(self):
        """The exact Codex R4 R5 LOW repro:
            from app.rag import kb
            class Helper:
                def get_kb(self): return 1
            def advise(q): return kb.get_kb()
        Pre-R5: ast.walk found Helper.get_kb method and falsely set
        locally_defined_get_kb=True → singleton check rejected.
        Post-R5: only module-level defs scanned, so kb.get_kb() passes."""
        tree = _parse(
            "from app.rag import kb\n"
            "class Helper:\n"
            "    def get_kb(self): return 1\n"
            "def advise(q): return kb.get_kb()\n"
        )
        assert _calls_get_kb_singleton(tree)

    def test_r5_nested_function_get_kb_does_not_shadow(self):
        """A nested `def get_kb` inside another function does not shadow
        the module-level singleton import either."""
        tree = _parse(
            "from app.rag import kb\n"
            "def outer():\n"
            "    def get_kb(): return 1\n"
            "    return get_kb()\n"
            "def advise(q): return kb.get_kb()\n"
        )
        assert _calls_get_kb_singleton(tree)

    def test_r5_module_level_get_kb_shadow_is_still_rejected(self):
        """Regression guard: module-level `def get_kb` MUST still be
        flagged as a shadow, even after the class-method narrowing."""
        tree = _parse("def get_kb(): return 1\ndef advise(q): return get_kb()\n")
        assert not _calls_get_kb_singleton(tree)

    def test_r5_async_module_level_get_kb_shadow_is_rejected(self):
        """`async def get_kb` at module level is also a shadow."""
        tree = _parse("async def get_kb(): return 1\nasync def advise(q): return await get_kb()\n")
        assert not _calls_get_kb_singleton(tree)

    def test_r5_class_method_does_not_block_real_get_kb_import(self):
        """Even if the class method is named get_kb AND a real import
        of get_kb exists, the singleton check should pass (the real
        import takes precedence; the method is in a different scope)."""
        tree = _parse(
            "from app.rag.kb import get_kb\n"
            "class Helper:\n"
            "    def get_kb(self): return 1\n"
            "def advise(q): return get_kb()\n"
        )
        assert _calls_get_kb_singleton(tree)

    def test_r5_assignment_chain_after_star_import(self):
        """Multi-hop chain post star-import: `import *; a=KB; b=a; b()`."""
        tree = _parse(
            "from app.rag.kb import *\na = KnowledgeBase\nb = a\nc = b\ndef f(): return c()\n"
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
            from app.rag.kb import KnowledgeBase
            KB = KnowledgeBase if cond else AltClass
            def advise(q): return KB()
        Pre-R6: KB binding from IfExp not propagated. Post-R6:
        IfExp.body/orelse walked; if EITHER resolves to a KB alias,
        target is bound."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "KB = KnowledgeBase if cond else AltClass\n"
            "def advise(q): return KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_ifexp_with_kb_in_orelse_is_caught(self):
        """KB on the orelse branch only (still must flag — conservative)."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "KB = AltClass if cond else KnowledgeBase\n"
            "def f(): return KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_ifexp_with_neither_branch_is_kb_is_not_flagged(self):
        """Both branches non-KB → no false positive."""
        tree = _parse("Foo = AltClass if cond else OtherClass\ndef f(): return Foo()\n")
        assert not _calls_knowledgebase_constructor(tree)

    def test_r6_nested_ifexp_chain_is_caught(self):
        """`a = X if c1 else (Y if c2 else KnowledgeBase); a()`."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "a = X if c1 else (Y if c2 else KnowledgeBase)\n"
            "def f(): return a()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_codex_r6_walrus_call_is_caught(self):
        """The exact Codex R5 R6 LOW repro: `(KB := KnowledgeBase)()`.
        The walrus binds AND immediately calls; the call's func is
        NamedExpr whose value is the KB alias."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\ndef f(): return (KB := KnowledgeBase)()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_walrus_call_via_aliased_name_is_caught(self):
        """`(KB := AnotherAlias)()` after `AnotherAlias = KnowledgeBase`."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "AnotherAlias = KnowledgeBase\n"
            "def f(): return (KB := AnotherAlias)()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r6_walrus_assignment_propagates_alias(self):
        """`(KB := KnowledgeBase); KB()` — walrus binds KB, later
        bare-name call is also flagged via the aliases set."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
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
        tree = _parse("from app.rag import kb\ndef f(): return (K := kb.KnowledgeBase)()\n")
        assert _calls_knowledgebase_constructor(tree)


# ---------------------------------------------------------------------------
# R7 hardening — alias annotations + subclass tracking
# (post Codex R4-verification 2026-04-28 MEDIUM)
#
# Codex's R4 verification of the merged PR #53 found two open bypasses
# the R4-R6 hardenings did NOT cover:
#
#   MEDIUM-1 (alias annotation): `from x import KnowledgeBase as KB;
#     def advise(kb: KB): ...` — _annotation_mentions_knowledgebase
#     only matched the literal name `KnowledgeBase`, so renamed imports
#     evaded the param check entirely.
#
#   MEDIUM-2 (subclass): `class MyKB(KnowledgeBase): pass; def advise(kb:
#     MyKB); MyKB()` — neither annotation nor ctor predicate tracked
#     subclasses; both passed silently.
#
# R7 fix:
# - _annotation_mentions_knowledgebase accepts an alias set; the public
#   test functions resolve it via _knowledgebase_local_aliases per-module.
# - _knowledgebase_local_aliases also folds in any class whose bases
#   reference a known alias (or `kb.KnowledgeBase` attribute form).
# - Alias propagation is a fixpoint, so transitive subclass chains
#   (`class A(KB); class B(A)`) all resolve.
# ---------------------------------------------------------------------------


class TestR7AliasAnnotationAndSubclass:
    """Codex R4-verification (2026-04-28): the two open MEDIUM bypasses."""

    def test_codex_r7_renamed_import_in_annotation_is_caught(self):
        """The exact Codex bypass: alias param annotation."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\ndef advise(query, kb: KB): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        aliases = _knowledgebase_local_aliases(tree)
        assert _function_takes_knowledgebase_param(fn, aliases)

    def test_codex_r7_subclass_param_annotation_is_caught(self):
        """`class MyKB(KnowledgeBase); def advise(kb: MyKB)` — subclass."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"
            "def advise(query, kb: MyKB): ...\n"
        )
        fn = next(
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "advise"
        )
        aliases = _knowledgebase_local_aliases(tree)
        assert "MyKB" in aliases
        assert _function_takes_knowledgebase_param(fn, aliases)

    def test_codex_r7_subclass_constructor_call_is_caught(self):
        """`class MyKB(KnowledgeBase); return MyKB()` — subclass ctor."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"
            "def build(): return MyKB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r7_subclass_via_attribute_base_is_caught(self):
        """`class MyKB(kb.KnowledgeBase): pass` — attribute-form base."""
        tree = _parse(
            "from app.rag import kb\n"
            "class MyKB(kb.KnowledgeBase): pass\n"
            "def build(): return MyKB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r7_transitive_subclass_chain_is_caught(self):
        """`class A(KB); class B(A); B()` — transitive via fixpoint."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "class A(KnowledgeBase): pass\n"
            "class B(A): pass\n"
            "def build(): return B()\n"
        )
        aliases = _knowledgebase_local_aliases(tree)
        assert "A" in aliases and "B" in aliases
        assert _calls_knowledgebase_constructor(tree)

    def test_r7_unrelated_class_is_not_flagged(self):
        """`class OtherClass(SomeUnrelatedBase)` — must NOT be aliased."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "class OtherClass(object): pass\n"
            "def build(): return OtherClass()\n"
        )
        aliases = _knowledgebase_local_aliases(tree)
        assert "OtherClass" not in aliases
        assert not _calls_knowledgebase_constructor(tree)

    def test_r7_alias_annotation_with_optional_wrapper_is_caught(self):
        """`Optional[KB]` where KB is a renamed import — must be caught."""
        tree = _parse(
            "from typing import Optional\n"
            "from app.rag.kb import KnowledgeBase as KB\n"
            "def advise(query, kb: Optional[KB] = None): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        aliases = _knowledgebase_local_aliases(tree)
        assert _function_takes_knowledgebase_param(fn, aliases)

    def test_r7_unresolved_alias_without_aliases_falls_back_to_literal(self):
        """Backwards compatibility: callers passing no alias set still get
        the pre-R7 literal-name behaviour. Documents the failure mode for
        callers that haven't been wired through."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\ndef advise(query, kb: KB): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        # Without aliases, alias annotation is missed (this is the gap the
        # R7 fix closes when callers do pass aliases).
        assert not _function_takes_knowledgebase_param(fn)


class TestR7Fix2AliasForwardRefAndAttributeAlias:
    """Codex R1 verification on PR #104 found two open bypasses post-R7:

    MEDIUM-1: alias forward-ref string. `def advise(kb: "KB")` where
      KB is an aliased import — string-annotation branch only matched
      substrings of literal "KnowledgeBase".

    MEDIUM-2: subclass / ctor via attribute alias. `class MyKB(rag.kb.KB)`
      and `rag.kb.KB()` (where KB is an aliased re-export) evaded
      because the Attribute branch only matched literal
      `attr == "KnowledgeBase"`.

    Fix: string-annotation matches alias names with word boundaries;
    Attribute branches in `_calls_knowledgebase_constructor` and
    `_bases_reference_alias` widen to any attr in the alias set.
    """

    def test_r7fix2_alias_forward_ref_string_is_caught(self):
        """`def advise(kb: "KB")` after `import KnowledgeBase as KB`."""
        tree = _parse(
            'from app.rag.kb import KnowledgeBase as KB\ndef advise(query, kb: "KB"): ...\n'
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        aliases = _knowledgebase_local_aliases(tree)
        assert "KB" in aliases
        assert _function_takes_knowledgebase_param(fn, aliases)

    def test_r7fix2_alias_forward_ref_string_word_boundary(self):
        """`KBConfig` is NOT KB — must not false-flag despite alias=`KB`."""
        tree = _parse(
            'from app.rag.kb import KnowledgeBase as KB\ndef advise(query, cfg: "KBConfig"): ...\n'  # noqa: F722
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        aliases = _knowledgebase_local_aliases(tree)
        # KB is in aliases but "KBConfig" is a different identifier;
        # word-boundary regex must not match.
        assert not _function_takes_knowledgebase_param(fn, aliases)

    def test_r7fix2_subclass_via_attribute_alias_is_caught(self):
        """`class MyKB(rag.kb.KB): pass` after `from x.y import KB`."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\n"
            "import rag.kb\n"
            "class MyKB(rag.kb.KB): pass\n"
            "def build(): return MyKB()\n"
        )
        aliases = _knowledgebase_local_aliases(tree)
        assert "MyKB" in aliases
        assert _calls_knowledgebase_constructor(tree)

    def test_r7fix2_attribute_alias_constructor_call_is_caught(self):
        """`return rag.kb.KB()` directly — Attribute call to aliased re-export."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\n"
            "import rag.kb\n"
            "def build(): return rag.kb.KB()\n"
        )
        assert _calls_knowledgebase_constructor(tree)

    def test_r7fix2_attribute_alias_in_annotation_is_caught(self):
        """`def advise(kb: rag.kb.KB)` — Attribute annotation via alias.
        R7-fix3: requires rag_module_aliases for the provenance gate."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\n"
            "import rag.kb\n"
            "def advise(query, kb: rag.kb.KB): ...\n"
        )
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        aliases = _knowledgebase_local_aliases(tree)
        rma = _rag_module_aliases(tree)
        assert _function_takes_knowledgebase_param(fn, aliases, rma)

    def test_r7fix2_unrelated_attribute_attr_is_not_flagged(self):
        """`some.module.OtherThing()` — must NOT be flagged as KB ctor."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "import some.module\n"
            "def build(): return some.module.OtherThing()\n"
        )
        assert not _calls_knowledgebase_constructor(tree)


class TestR7Fix3ProvenanceAwareAttribute:
    """Codex R2 (2026-04-28) flagged 1 MEDIUM: blanket `attr in aliases`
    in the Attribute branch was provenance-blind. False positives:
      - `_calls_knowledgebase_constructor` flagged `some.KB()` if KB in aliases
      - flagged `obj.MyKB()` once MyKB tracked as subclass
      - `_function_takes_knowledgebase_param` flagged `kb: other.MyKB`
      - `class Derived(other.MyKB)` added Derived to alias set

    R7-fix3: only widen the Attribute branch when leftmost Name is a
    known rag-module alias. Literal `attr == "KnowledgeBase"` always
    flags (canonical class identifier).
    """

    def test_r7fix3_unrelated_attr_call_no_false_positive(self):
        """`some.KB()` where some is NOT a rag module — KB-named alias
        in scope must NOT cause false flag."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\n"
            "import some.module as some\n"
            "def f(): return some.KB()\n"
        )
        # KB IS in aliases (from the rag.kb import), but `some.KB` is
        # an unrelated module attribute. Must NOT flag.
        aliases = _knowledgebase_local_aliases(tree)
        assert "KB" in aliases
        assert not _calls_knowledgebase_constructor(tree)

    def test_r7fix3_unrelated_obj_subclass_call_no_false_positive(self):
        """`obj.MyKB()` where obj is unrelated — must NOT flag despite
        MyKB being tracked as a subclass alias somewhere."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"  # MyKB enters aliases
            "import some.factory as obj\n"
            "def f(): return obj.MyKB()\n"
        )
        aliases = _knowledgebase_local_aliases(tree)
        assert "MyKB" in aliases  # subclass tracking works
        # But obj.MyKB is unrelated — must not flag.
        assert not _calls_knowledgebase_constructor(tree)

    def test_r7fix3_unrelated_attr_annotation_no_false_positive(self):
        """`def advise(kb: other.MyKB)` — alias-named attr but unrelated root."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"
            "import other\n"
            "def advise(query, kb: other.MyKB): ...\n"
        )
        fn = next(
            n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "advise"
        )
        aliases = _knowledgebase_local_aliases(tree)
        rma = _rag_module_aliases(tree)
        assert "other" not in rma  # unrelated module
        assert not _function_takes_knowledgebase_param(fn, aliases, rma)

    def test_r7fix3_unrelated_subclass_base_not_added_to_aliases(self):
        """`class Derived(other.MyKB)` must NOT add Derived to aliases."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"
            "import other\n"
            "class Derived(other.MyKB): pass\n"
        )
        aliases = _knowledgebase_local_aliases(tree)
        assert "MyKB" in aliases
        assert "Derived" not in aliases

    def test_r7fix3_rag_module_attr_alias_still_caught(self):
        """`rag.kb.KB()` where rag is a known rag-module — MUST still flag."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\n"
            "import rag.kb\n"
            "def f(): return rag.kb.KB()\n"
        )
        rma = _rag_module_aliases(tree)
        assert "rag" in rma
        assert _calls_knowledgebase_constructor(tree)

    def test_r7fix3_literal_kb_knowledgebase_attr_always_flags(self):
        """`obj.KnowledgeBase()` — literal class name is provenance-free hit."""
        tree = _parse("import some.unrelated as obj\ndef f(): return obj.KnowledgeBase()\n")
        # No rag-module alias for `obj`, but the .attr is the literal
        # canonical class name. Must flag (defensive: anyone spelling
        # KnowledgeBase verbatim cannot legitimately mean something else).
        assert _calls_knowledgebase_constructor(tree)

    def test_r7fix3_rag_module_aliases_collects_known_shapes(self):
        """R7-fix3.2: _rag_module_aliases trusts ONLY `import` statements
        with literal `rag` in the path. ImportFrom shapes (regardless of
        target) are statically ambiguous between submodule and class
        re-export and are not trusted (see Codex R4 finding)."""
        tree = _parse(
            "import rag.kb\n"
            "import rag.kb as rk\n"
            "from app.rag import kb\n"
            "from app.rag import kb as rk2\n"
            "from . import kb as relkb\n"
            "import unrelated.module\n"
        )
        rma = _rag_module_aliases(tree)
        # Trusted (Import statements with `rag` in path):
        assert "rag" in rma
        assert "rk" in rma
        # Not trusted (ImportFrom — could be class re-export):
        assert "kb" not in rma
        assert "rk2" not in rma
        assert "relkb" not in rma
        # Unrelated import never trusted:
        assert "unrelated" not in rma

    def test_r7fix3_attribute_root_name_helper(self):
        """`_attribute_root_name` returns leftmost Name id or None."""
        # a.b.c → "a"
        tree = _parse("x = a.b.c\n")
        attr = next(n for n in ast.walk(tree) if isinstance(n, ast.Attribute))
        assert _attribute_root_name(attr) == "a"
        # bare Name returns its id
        name = ast.Name(id="solo")
        assert _attribute_root_name(name) == "solo"
        # non-Name root (Call().attr) returns None
        tree2 = _parse("x = make().b\n")
        attr2 = next(n for n in ast.walk(tree2) if isinstance(n, ast.Attribute))
        assert _attribute_root_name(attr2) is None


class TestR7Fix31RagModuleAliasesTighten:
    """Codex R3 (2026-04-28) found `_rag_module_aliases` over-trusts
    parent segments and class-member imports. R7-fix3.1 tightens it.

    Bypass classes Codex R3 reproduced:
      - `import app.rag.kb` adds `app` to rma → `app.other.KB()` flags.
      - `from app.rag.kb import KnowledgeBase as KB` adds `KB` to rma →
        `KB.MyKB()` (where MyKB is tracked subclass) flags.
      - `from app import rag` was missed → `rag.kb.KB()` doesn't flag.
    """

    def test_r7fix31_import_app_rag_kb_does_not_trust_app(self):
        """`import app.rag.kb` must NOT add `app` to rma."""
        tree = _parse("import app.rag.kb\n")
        rma = _rag_module_aliases(tree)
        assert "app" not in rma

    def test_r7fix31_import_app_rag_kb_app_other_call_no_false_positive(self):
        """The full Codex R3 repro #1: `app.other.KB()`."""
        tree = _parse(
            "import app.rag.kb\n"
            "import app.other\n"
            "from app.rag.kb import KnowledgeBase as KB\n"
            "def f(): return app.other.KB()\n"
        )
        # KB is in aliases (from rag.kb import as), but `app` must NOT
        # be in rma — the call goes through unrelated `app.other` path.
        rma = _rag_module_aliases(tree)
        assert "app" not in rma
        assert not _calls_knowledgebase_constructor(tree)

    def test_r7fix31_class_import_does_not_pollute_rma(self):
        """`from app.rag.kb import KnowledgeBase as KB` must NOT add KB to rma."""
        tree = _parse("from app.rag.kb import KnowledgeBase as KB\n")
        rma = _rag_module_aliases(tree)
        assert "KB" not in rma  # KB is a class, not a module

    def test_r7fix31_class_import_no_kb_dot_other_false_positive(self):
        """The Codex R3 repro #2: `KB.MyKB()` where KB is the class."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase as KB\n"
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"
            "def f(): return KB.MyKB()\n"  # weird but legal Python
        )
        # KB in aliases (subclass tracking), MyKB in aliases (subclass).
        # rma must NOT contain KB (it's a class member, not a module).
        # Therefore `KB.MyKB()` must NOT flag as KB ctor.
        aliases = _knowledgebase_local_aliases(tree)
        rma = _rag_module_aliases(tree)
        assert "KB" in aliases
        assert "MyKB" in aliases
        assert "KB" not in rma
        assert not _calls_knowledgebase_constructor(tree)

    def test_r7fix32_from_app_import_rag_not_collected(self):
        """R7-fix3.2: `from app import rag` is ambiguous (rag could be a
        class re-export from app/__init__.py) and is NOT trusted. To get
        the rag-package alias trusted, write `import rag` instead."""
        tree = _parse("from app import rag\n")
        rma = _rag_module_aliases(tree)
        assert "rag" not in rma

    def test_r7fix32_from_kb_member_import_does_not_pollute_rma(self):
        """`from .kb import get_kb` (member of kb submodule) must NOT add."""
        tree = _parse("from .kb import get_kb\n")
        rma = _rag_module_aliases(tree)
        assert "get_kb" not in rma

    def test_r7fix32_from_dot_import_kb_not_collected(self):
        """R7-fix3.2: `from . import kb` is also statically ambiguous
        (kb could be a class re-export from __init__) and is NOT trusted.
        Documented limitation — facade callers should `import rag.kb`
        instead, which is unambiguously a submodule import."""
        tree = _parse("from . import kb\n")
        rma = _rag_module_aliases(tree)
        assert "kb" not in rma

    def test_r7fix31_import_rag_kb_collected(self):
        """`import rag.kb` adds `rag` (leftmost is literally `rag`)."""
        tree = _parse("import rag.kb\n")
        rma = _rag_module_aliases(tree)
        assert "rag" in rma

    def test_r7fix31_import_rag_kb_as_aliased(self):
        """`import rag.kb as r` adds `r`."""
        tree = _parse("import rag.kb as r\n")
        rma = _rag_module_aliases(tree)
        assert "r" in rma
        assert "rag" not in rma  # alias replaces the leftmost binding

    def test_r7fix31_unrelated_module_not_collected(self):
        """`import unrelated.module` must NOT add anything."""
        tree = _parse("import unrelated.module\n")
        rma = _rag_module_aliases(tree)
        assert "unrelated" not in rma


class TestR7Fix32ImportFromIsAmbiguous:
    """Codex R4 (2026-04-28) showed `_rag_module_aliases` over-trusted
    ImportFrom: `from app.rag import KnowledgeBase as KB` re-exports a
    class but added KB to rma, re-opening `KB.MyKB()` as a false positive.
    Same for `from app.rag import get_kb`.

    R7-fix3.2: ImportFrom is statically ambiguous between submodule
    import and class/function re-export (Python `__init__.py` can
    re-export anything). Stop trusting any ImportFrom-bound name.
    """

    def test_r7fix32_from_rag_import_class_alias_no_false_positive(self):
        """The Codex R4 repro #1: `from app.rag import KnowledgeBase as KB; KB.MyKB()`."""
        tree = _parse(
            "from app.rag import KnowledgeBase as KB\n"
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"
            "def f(): return KB.MyKB()\n"
        )
        rma = _rag_module_aliases(tree)
        assert "KB" not in rma  # class re-export, not a module
        assert not _calls_knowledgebase_constructor(tree)

    def test_r7fix32_from_rag_import_function_alias_no_false_positive(self):
        """The Codex R4 repro #2: `from app.rag import get_kb; get_kb.MyKB()`."""
        tree = _parse(
            "from app.rag import get_kb\n"
            "from app.rag.kb import KnowledgeBase\n"
            "class MyKB(KnowledgeBase): pass\n"
            "def f(): return get_kb.MyKB()\n"
        )
        rma = _rag_module_aliases(tree)
        assert "get_kb" not in rma  # function re-export, not a module
        assert not _calls_knowledgebase_constructor(tree)

    def test_r7fix32_import_rag_kb_still_collected(self):
        """The trusted shape still works: `import rag.kb` adds `rag`."""
        tree = _parse("import rag.kb\n")
        rma = _rag_module_aliases(tree)
        assert "rag" in rma

    def test_r7fix32_import_rag_kb_then_rag_kb_kb_ctor_flags(self):
        """`import rag.kb; from x import KB; rag.kb.KB()` STILL flags."""
        tree = _parse(
            "import rag.kb\n"
            "from app.rag.kb import KnowledgeBase as KB\n"
            "def f(): return rag.kb.KB()\n"
        )
        rma = _rag_module_aliases(tree)
        assert "rag" in rma
        # rag.kb.KB(): leftmost `rag` in rma, attr `KB` in aliases. Flag.
        assert _calls_knowledgebase_constructor(tree)

    def test_r7fix32_literal_class_attr_always_flags_no_provenance(self):
        """Provenance-free literal `KnowledgeBase` attr always flags
        regardless of leftmost name."""
        tree = _parse(
            "from app.rag.kb import KnowledgeBase\n"
            "import some.unrelated as obj\n"
            "def f(): return obj.KnowledgeBase()\n"
        )
        # `obj` not in rma (unrelated), but attr is the literal canonical
        # class name — must still flag.
        assert _calls_knowledgebase_constructor(tree)
