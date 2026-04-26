"""Smoke test for the GET /visualize/plot shim added by this PR.

The frontend iframe at frontend/src/App.tsx hits /visualize/plot via GET
with `?case_id=<id>&output_format=html&increment_index=<n>`. The original
backend only exposed POST /plot taking a full VisualizeRequest body, so
the iframe got 405 Method Not Allowed. This shim adds a GET form that:

1. Looks up the Case by case_id
2. Resolves the FRD result file path (handling the GS-001 vs gs001_result.frd
   naming mismatch)
3. Calls export_scene_as_html with a small fallback chain of field names
4. Returns either the rendered scene or a case-info HTML page when the
   PyVista path is unavailable

Two test layers:

1. **AST surface** (TestGetShim*): asserts the route exists with the right
   HTTP method/path and references the expected collaborators. Doesn't
   import the module — the dev test env lacks fastapi/sqlalchemy.

2. **R2 behavioral** (TestR2*): exercises the pure helpers extracted into
   `_viz_helpers.py` (post Codex R1). These are loaded directly via
   importlib to bypass the `app.api.routes` package init (which pulls
   in fastapi). They run unmodified in dev env and CI.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

_VIZ_PATH = (
    Path(__file__).resolve().parent.parent
    / "backend"
    / "app"
    / "api"
    / "routes"
    / "visualization.py"
)


def _parse_module():
    return ast.parse(_VIZ_PATH.read_text(encoding="utf-8"), filename=str(_VIZ_PATH))


def _function_decorators(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    out = []
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute):
            out.append(d.func.attr)
        elif isinstance(d, ast.Attribute):
            out.append(d.attr)
    return out


def _find_function(name: str) -> ast.AsyncFunctionDef | ast.FunctionDef | None:
    tree = _parse_module()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return node
    return None


def _decorator_method(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> str | None:
    """Return the HTTP method ('get'/'post') from @router.<method>(...)."""
    for d in fn.decorator_list:
        if (
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and isinstance(d.func.value, ast.Name)
            and d.func.value.id == "router"
        ):
            return d.func.attr
    return None


def _decorator_path(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> str | None:
    """Return the URL string from @router.<method>('<path>')."""
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and d.args:
            arg = d.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
    return None


class TestGetShimRouteSurface:
    """Assert the route exists with the right HTTP method + path."""

    def test_visualize_by_case_id_function_exists(self):
        fn = _find_function("visualize_by_case_id")
        assert fn is not None, "visualize_by_case_id missing"
        assert isinstance(fn, ast.AsyncFunctionDef), "must be async (FastAPI handler)"

    def test_visualize_by_case_id_is_GET_on_plot(self):
        fn = _find_function("visualize_by_case_id")
        assert fn is not None
        assert _decorator_method(fn) == "get", "shim must be a GET (matches frontend iframe)"
        assert _decorator_path(fn) == "/plot", "shim must be at /plot"

    def test_post_plot_still_present(self):
        """Regression guard: the original POST /plot must NOT be removed
        — other callers (CLI, tests) may still rely on it."""
        fn = _find_function("create_visualization")
        assert fn is not None
        assert _decorator_method(fn) == "post"
        assert _decorator_path(fn) == "/plot"

    def test_get_shim_takes_case_id_query_param(self):
        fn = _find_function("visualize_by_case_id")
        assert fn is not None
        arg_names = [a.arg for a in fn.args.args]
        assert "case_id" in arg_names, "frontend iframe sends ?case_id=..."
        # output_format and increment_index are optional; presence only.
        assert "output_format" in arg_names
        assert "increment_index" in arg_names


class TestGetShimBodyReferences:
    """Assert the handler wires up the expected collaborators."""

    def _body_text(self) -> str:
        fn = _find_function("visualize_by_case_id")
        assert fn is not None
        return ast.unparse(fn) if hasattr(ast, "unparse") else _VIZ_PATH.read_text()

    def test_body_loads_case_from_db(self):
        body = self._body_text()
        assert "Case" in body, "must select Case row"
        assert "case_id" in body

    def test_body_uses_frd_parser(self):
        body = self._body_text()
        assert "FRDParser" in body or "frd_parser" in body

    def test_body_calls_export_scene_as_html(self):
        body = self._body_text()
        assert "export_scene_as_html" in body

    def test_body_handles_missing_pyvista_with_fallback_html(self):
        """When export_scene_as_html returns empty, must NOT raise — must
        return a fallback HTML page so the iframe shows something."""
        body = self._body_text()
        assert "HTMLResponse" in body
        # The fallback must include at least one piece of case metadata
        # so the user can still see what they selected.
        assert "case.name" in body or "case_id" in body

    def test_body_resolves_frd_filename_variants(self):
        """The naming mismatch (GS-001 → gs001_result.frd) was the original
        bug; the shim must consider multiple candidate paths.

        After R2 refactor the candidate logic lives in `_resolve_frd_path`
        in the sibling `_viz_helpers` module. The handler must delegate
        to that helper, and the helper must encode the `_result.frd`
        convention.
        """
        helper_path = (
            Path(__file__).resolve().parent.parent
            / "backend"
            / "app"
            / "api"
            / "routes"
            / "_viz_helpers.py"
        )
        helper_text = helper_path.read_text(encoding="utf-8")
        assert "_result.frd" in helper_text, "helper must try the *_result.frd convention"
        # Handler delegates to the resolver:
        body = self._body_text()
        assert "_resolve_frd_path" in body


# ---------------------------------------------------------------------------
# R2 hardening — behavioral tests for the extracted helpers
# (post Codex R1 LOW: AST-only tests miss runtime bugs)
# ---------------------------------------------------------------------------


# R2 helpers live in `_viz_helpers.py` — a fastapi-free pure-stdlib module
# extracted from `visualization.py` so behavioral tests run in the dev
# env (which doesn't install fastapi/sqlalchemy).
#
# Load it directly via importlib to bypass the `app.api.routes` package
# __init__ (which transitively imports fastapi-dependent siblings).
_HELPER_PATH = (
    Path(__file__).resolve().parent.parent
    / "backend"
    / "app"
    / "api"
    / "routes"
    / "_viz_helpers.py"
)
_spec = importlib.util.spec_from_file_location("_viz_helpers", _HELPER_PATH)
_viz_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_viz_helpers)

_allowed_fs_roots = _viz_helpers._allowed_fs_roots
_apply_increment = _viz_helpers._apply_increment
_fallback_html_render_failed = _viz_helpers._fallback_html_render_failed
_fallback_html_unavailable_pyvista = _viz_helpers._fallback_html_unavailable_pyvista
_is_under_allowed_root = _viz_helpers._is_under_allowed_root
_resolve_frd_path = _viz_helpers._resolve_frd_path
_validate_case_id = _viz_helpers._validate_case_id


class TestR2ValidateCaseId:
    """Path-traversal guard: case_id must match a safe shape.

    Helpers raise ValueError; the route layer translates to HTTP 400.
    """

    def test_accepts_GS_001_format(self):
        _validate_case_id("GS-001")  # no raise

    def test_accepts_alphanumeric_underscore(self):
        _validate_case_id("My_Case_42")

    def test_accepts_uppercase(self):
        _validate_case_id("ABCDEF123")

    def test_rejects_path_traversal_attempt(self):
        with pytest.raises(ValueError):
            _validate_case_id("../../etc/passwd")

    def test_rejects_slash(self):
        with pytest.raises(ValueError):
            _validate_case_id("foo/bar")

    def test_rejects_null_byte(self):
        with pytest.raises(ValueError):
            _validate_case_id("foo\x00bar")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            _validate_case_id("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError):
            _validate_case_id("A" * 65)


class TestR2ResolveFrdPath:
    """FRD resolution + allowed-root anchoring."""

    def test_resolves_real_GS_001_under_golden_samples(self, tmp_path, monkeypatch):
        # Use the actual repo's golden_samples.
        repo = Path(__file__).resolve().parent.parent
        monkeypatch.chdir(repo)
        result = _resolve_frd_path("GS-001", str(repo / "golden_samples" / "GS-001" / "gs-001.inp"))
        assert result is not None
        assert result.name == "gs001_result.frd"
        assert result.is_file()

    def test_returns_none_for_nonexistent_case(self, tmp_path, monkeypatch):
        repo = Path(__file__).resolve().parent.parent
        monkeypatch.chdir(repo)
        result = _resolve_frd_path("GS-999", None)
        assert result is None

    def test_rejects_candidate_outside_allowed_root(self, tmp_path, monkeypatch):
        """A poisoned db_frd_path pointing at /tmp must be rejected even if
        the file exists there (it's outside golden_samples/, project_state/,
        calculix_cases/)."""
        outside = tmp_path / "evil.frd"
        outside.write_text("dummy")
        repo = Path(__file__).resolve().parent.parent
        monkeypatch.chdir(repo)
        result = _resolve_frd_path("evil_case", str(outside))
        assert result is None, "candidate outside allowed roots must be rejected"

    def test_resolves_to_absolute_path(self, monkeypatch):
        repo = Path(__file__).resolve().parent.parent
        monkeypatch.chdir(repo)
        result = _resolve_frd_path("GS-001", None)
        assert result is not None
        assert result.is_absolute()


class TestR2AllowedRootHelper:
    def test_under_root_accepts_subpath(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gs = tmp_path / "golden_samples" / "x"
        gs.mkdir(parents=True)
        f = gs / "a.frd"
        f.write_text("x")
        roots = _allowed_fs_roots()
        assert _is_under_allowed_root(f, roots)

    def test_under_root_rejects_sibling(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        outside = tmp_path / "outside.frd"
        outside.write_text("x")
        roots = _allowed_fs_roots()
        assert not _is_under_allowed_root(outside, roots)


class TestR2ApplyIncrement:
    """increment_index honor: top-level fields swap to the chosen increment."""

    def test_no_op_when_no_increments(self):
        class Fake:
            displacements = "original"
            stresses = "original"
            increments = []

        f = Fake()
        _apply_increment(f, 0)
        assert f.displacements == "original"
        assert f.stresses == "original"

    def test_no_op_when_index_out_of_range(self):
        class Inc:
            displacements = "inc0"
            stresses = "stress0"

        class Fake:
            displacements = "top"
            stresses = "topS"
            increments = [Inc()]

        f = Fake()
        _apply_increment(f, 99)
        assert f.displacements == "top"

    def test_swaps_top_level_to_chosen_increment(self):
        class Inc:
            def __init__(self, d, s):
                self.displacements = d
                self.stresses = s

        class Fake:
            increments = [Inc("d0", "s0"), Inc("d1", "s1"), Inc("d2", "s2")]
            displacements = None
            stresses = None

        f = Fake()
        _apply_increment(f, 1)
        assert f.displacements == "d1"
        assert f.stresses == "s1"

    def test_negative_index_no_op(self):
        class Inc:
            displacements = "inc"
            stresses = "stress"

        class Fake:
            increments = [Inc()]
            displacements = "top"
            stresses = "topS"

        f = Fake()
        _apply_increment(f, -1)
        assert f.displacements == "top"


class TestR2XssEscaping:
    """Fallback HTML must escape every dynamic value (Codex R1 MEDIUM)."""

    def test_unavailable_pyvista_escapes_case_name(self):
        attack = "<img src=x onerror=alert(1)>"
        out = _fallback_html_unavailable_pyvista(attack)
        assert attack not in out, "raw HTML must not appear"
        assert "&lt;img" in out, "must be html-escaped"

    def test_render_failed_escapes_case_name(self):
        attack = '<script>alert("xss")</script>'
        out = _fallback_html_render_failed(attack, "truss", 100, 50, 1)
        assert attack not in out
        assert "&lt;script&gt;" in out

    def test_render_failed_escapes_structure_type(self):
        attack = '"><img src=x>'
        out = _fallback_html_render_failed("safe", attack, 100, 50, 1)
        assert attack not in out
        # html.escape encodes < and > and " by default
        assert "&lt;img" in out

    def test_render_failed_does_not_leak_paths(self):
        """The fallback must NOT include frd_path or any internal paths."""
        out = _fallback_html_render_failed("safe", "truss", 100, 50, 1)
        assert "/Users/" not in out
        assert "/tmp/" not in out
        assert "frd_path" not in out
        assert ".frd" not in out

    def test_render_failed_does_not_leak_exception_text(self):
        """The fallback must NOT include `last_err` or any exception message."""
        out = _fallback_html_render_failed("safe", "truss", 100, 50, 1)
        assert "Last error" not in out
        assert "last_err" not in out
        assert "Exception" not in out
        assert "Traceback" not in out

    def test_unavailable_handles_none_case_name(self):
        out = _fallback_html_unavailable_pyvista(None)
        assert "(unnamed case)" in out

    def test_render_failed_handles_none_case_name(self):
        out = _fallback_html_render_failed(None, None, "?", "?", 0)
        assert "(unnamed case)" in out
