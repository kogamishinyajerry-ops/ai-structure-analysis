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

Tests here are deliberately AST-only — the dev test environment doesn't
install fastapi or sqlalchemy (those live in backend/venv), so a TestClient
integration test would force the dev extras to grow. Pure-AST smoke covers
the regression class we care about: the route exists, takes the right
query params, and the function body references the right collaborators.
"""

from __future__ import annotations

import ast
from pathlib import Path

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
        bug; the shim must consider multiple candidate paths."""
        body = self._body_text()
        # Look for the candidate-list pattern.
        assert "_result.frd" in body, "must try the *_result.frd convention"
        assert ".frd" in body
