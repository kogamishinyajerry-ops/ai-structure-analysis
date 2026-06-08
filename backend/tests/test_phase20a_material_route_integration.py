"""FM-04a Phase 20 A — material_id route → service integration.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

Closes the Phase 19 E load-bearing finding (both FEA and UX agents
flagged independently): ``RunRequest.material_id`` was declared in
Phase 18 E (round-3 honesty fix) but never consumed by the live
solver route. This file pins:

* (M:-1) The route uses the SSOT ``compose_material_id_inp`` helper,
  not an inline material lookup.
* (T:-3) End-to-end: a POST with ``material_id="aluminium-6061-t6"``
  causes a real INP file to land at the conventional case_dir path
  carrying aluminium-property ``*ELASTIC`` byte-identical to
  ``library.json`` (E=6.890000e+10, ν=0.330000).
* (A:-2) An unknown material_id surfaces 422 (NOT 500), with a
  detail string citing the library path.
* (A:-2) Missing material_id falls through to the legacy Phase 1-17
  inp-file-on-disk flow (back-compat with every pre-Phase-20 caller).
* (C:-1) The JobResponse envelope carries the chosen material's
  ``reference`` citation so the audit trail surfaces what was used.

We sidestep ``httpx``'s dropped ``Client(app=app, ...)`` shape (which
Starlette's ``TestClient`` relies on) by invoking the handler function
directly with mocked dependencies. ``app.api.routes.solver`` is
importable as a normal module in the local venv; Phase 18 E's
``importlib.spec_from_file_location`` dance is unnecessary here.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Conftest sets ``OPENAI_API_KEY=test-key-for-pytest`` before any
# test imports run, which causes ``app.api.__init__`` →
# ``app.api.nl`` → ``NLParser()`` to instantiate a broken legacy
# OpenAI client (the installed openai package passes a `proxies`
# kwarg httpx no longer accepts). Phase 20 doesn't touch nl_parser;
# we unset the env var BEFORE importing ``app.api.routes.solver``
# so NLParser stays in its no-client branch. Restored afterwards
# so no other test sees a different env.
_orig_openai_key = os.environ.pop("OPENAI_API_KEY", None)
try:
    from app.api.routes import solver as solver_route_mod
finally:
    if _orig_openai_key is not None:
        os.environ["OPENAI_API_KEY"] = _orig_openai_key

from app.services.tier2_pipeline import (
    Tier2PipelineError,
    compose_material_id_inp,
)


# ---------------------------------------------------------------------
# Pure-function pins for compose_material_id_inp (M:-1, A:-2)
# ---------------------------------------------------------------------


def test_compose_with_aluminium_writes_aluminium_elastic_block(
    tmp_path: Path,
) -> None:
    """T:-3 — the composed INP carries the aluminium material's E/ν
    byte-identical to library.json. Pins the route → service handoff
    at the smallest possible scope."""
    case_dir = tmp_path / "phase20a-candidate"
    case_dir.mkdir()
    inp_path, material, reference = compose_material_id_inp(
        case_dir,
        jobname="phase20a",
        material_id="aluminium-6061-t6",
    )
    assert inp_path.is_file()
    body = inp_path.read_text(encoding="utf-8")
    # Material lookup carries SSOT id; INP block uses the canonical
    # ALUMINIUM_6061_T6 label (hyphen→underscore, upper-cased).
    assert "*MATERIAL, NAME=ALUMINIUM_6061_T6" in body
    # ν=0.33, E=68.9e9 from library.json:14-15 (MMPDS-2023 §3.6.1.0).
    assert "*ELASTIC" in body
    assert "6.890000e+10" in body
    assert "0.330000" in body
    assert material.id == "aluminium-6061-t6"
    assert "MMPDS" in reference


def test_compose_with_steel_writes_steel_elastic_block(tmp_path: Path) -> None:
    """Sibling pin to aluminium — different material → different
    *ELASTIC row → confirms compose IS reading the material id."""
    case_dir = tmp_path / "phase20a-candidate"
    case_dir.mkdir()
    inp_path, material, _reference = compose_material_id_inp(
        case_dir,
        jobname="phase20a",
        material_id="steel-s355",
    )
    body = inp_path.read_text(encoding="utf-8")
    assert "*MATERIAL, NAME=STEEL_S355" in body
    # E=210e9, ν=0.3 from library.json (EN 10025-2:2019 §7.3).
    assert "2.100000e+11" in body
    assert "0.300000" in body
    assert material.id == "steel-s355"


def test_compose_with_none_falls_back_to_default_steel(tmp_path: Path) -> None:
    """A:-2 — material_id=None preserves the Phase 18 A DEFAULT_STEEL
    back-compat path (every pre-Phase-19 caller still works)."""
    case_dir = tmp_path / "phase20a-candidate"
    case_dir.mkdir()
    inp_path, material, reference = compose_material_id_inp(
        case_dir,
        jobname="phase20a",
        material_id=None,
    )
    body = inp_path.read_text(encoding="utf-8")
    # DEFAULT_STEEL.name = "STEEL_S355" per Phase 18 A.
    assert "*MATERIAL, NAME=STEEL_S355" in body
    # MinimalHexMaterial has no `id` attribute — the Material/MinimalHex
    # union exercises both paths.
    assert hasattr(material, "name")
    assert "Phase 18 A inline default" in reference


def test_compose_with_empty_string_falls_back_to_default_steel(
    tmp_path: Path,
) -> None:
    """Empty string is the same back-compat case as None (UI may emit
    an empty `material_id` field when the picker is reset)."""
    case_dir = tmp_path / "phase20a-candidate"
    case_dir.mkdir()
    inp_path, _material, _reference = compose_material_id_inp(
        case_dir,
        jobname="phase20a",
        material_id="",
    )
    body = inp_path.read_text(encoding="utf-8")
    assert "*MATERIAL, NAME=STEEL_S355" in body


def test_compose_unknown_material_raises_tier2_pipeline_error(
    tmp_path: Path,
) -> None:
    """A:-2 — unknown material_id raises the typed error so the route
    can render 422 (not 500)."""
    case_dir = tmp_path / "phase20a-candidate"
    case_dir.mkdir()
    with pytest.raises(Tier2PipelineError) as excinfo:
        compose_material_id_inp(
            case_dir,
            jobname="phase20a",
            material_id="unobtanium-9001",
        )
    assert excinfo.value.stage == "resolve_material"
    assert "unobtanium-9001" in str(excinfo.value)
    # The error carries the original MaterialNotFoundError as the cause
    # so the audit trail can cite the failed lookup explicitly.
    assert excinfo.value.cause is not None


def test_compose_refuses_missing_case_dir(tmp_path: Path) -> None:
    """Anti-gaming sanity: a non-existent case_dir surfaces a typed
    error with stage='write_inp' (not a bare OSError)."""
    case_dir = tmp_path / "does-not-exist-candidate"
    # NOT calling mkdir
    with pytest.raises(Tier2PipelineError) as excinfo:
        compose_material_id_inp(
            case_dir,
            jobname="phase20a",
            material_id="steel-s355",
        )
    assert excinfo.value.stage == "write_inp"


# ---------------------------------------------------------------------
# Route handler integration (T:-3, A:-3)
# ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def route_mod():
    return solver_route_mod


def _make_mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


def test_route_with_material_id_composes_aluminium_inp(
    route_mod, tmp_path: Path, monkeypatch
) -> None:
    """T:-3 — POST /solver/run with material_id=aluminium-6061-t6
    causes the route to compose a Tier 2 INP at the conventional
    case_dir path carrying the aluminium *ELASTIC block. The legacy
    SolverService.run_simulation is mocked so we don't actually fire
    ccx; the test scope is the route → compose handoff."""
    case_dir = tmp_path / "phase20a-route-candidate"
    case_dir.mkdir()

    # Redirect settings.gs_root so the route writes into tmp_path.
    # ``settings.gs_root`` is a computed @property → not settable
    # via attribute monkeypatch. Replace the module-level `settings`
    # binding instead so the route reads tmp_path.
    from types import SimpleNamespace
    monkeypatch.setattr(
        route_mod, "settings", SimpleNamespace(gs_root=tmp_path)
    )

    # Mock the legacy SolverService.run_simulation so we don't spawn
    # an actual ccx subprocess.
    mock_solver = MagicMock()
    mock_solver.run_simulation = AsyncMock(return_value="job-phase20a-mock")
    monkeypatch.setattr(
        route_mod, "get_solver_service", lambda: mock_solver
    )

    request = route_mod.RunRequest(
        case_id="phase20a-route-candidate",
        analysis_type="static",
        material_id="aluminium-6061-t6",
    )
    db = _make_mock_db()
    response = asyncio.run(route_mod.run_calculation(request, db=db))

    # Solver was actually invoked, with the composed INP path.
    mock_solver.run_simulation.assert_awaited_once()
    inp_passed = mock_solver.run_simulation.await_args[0][0]
    assert inp_passed.is_file(), (
        f"route should have composed an INP at {inp_passed}"
    )
    body = inp_passed.read_text(encoding="utf-8")
    assert "*MATERIAL, NAME=ALUMINIUM_6061_T6" in body
    assert "6.890000e+10" in body

    # JobResponse carries the audit citation (C:-1).
    assert response.material_reference is not None
    assert "MMPDS" in response.material_reference
    assert response.status == "RUNNING"


def test_route_without_material_id_preserves_legacy_path(
    route_mod, tmp_path: Path, monkeypatch
) -> None:
    """A:-2 — back-compat: omitting material_id triggers the legacy
    inp-file-on-disk lookup (Phase 1-17 behaviour preserved). The
    composed-INP branch must NOT activate."""
    case_dir = tmp_path / "phase20a-legacy-candidate"
    case_dir.mkdir()
    # Place a fake legacy INP at the expected path.
    legacy_inp = case_dir / "phase20alegacycandidate.inp"
    legacy_inp.write_text("*HEADING\nlegacy artifact\n", encoding="utf-8")

    # ``settings.gs_root`` is a computed @property → not settable
    # via attribute monkeypatch. Replace the module-level `settings`
    # binding instead so the route reads tmp_path.
    from types import SimpleNamespace
    monkeypatch.setattr(
        route_mod, "settings", SimpleNamespace(gs_root=tmp_path)
    )

    mock_solver = MagicMock()
    mock_solver.run_simulation = AsyncMock(return_value="job-legacy-mock")
    monkeypatch.setattr(
        route_mod, "get_solver_service", lambda: mock_solver
    )

    request = route_mod.RunRequest(
        case_id="phase20a-legacy-candidate",
        analysis_type="static",
        material_id=None,
    )
    db = _make_mock_db()
    response = asyncio.run(route_mod.run_calculation(request, db=db))

    mock_solver.run_simulation.assert_awaited_once()
    inp_passed = mock_solver.run_simulation.await_args[0][0]
    # Legacy path returned the on-disk file unchanged.
    assert inp_passed == legacy_inp
    body = inp_passed.read_text(encoding="utf-8")
    assert "legacy artifact" in body
    # No material_reference surfaces on the legacy path.
    assert response.material_reference is None


def test_route_unknown_material_id_returns_422(
    route_mod, tmp_path: Path, monkeypatch
) -> None:
    """A:-2 — unknown material_id surfaces 422 (NOT 500) with detail
    citing the library SSOT path. Anti-gaming guard so future
    reviewers can immediately find the canonical material list."""
    case_dir = tmp_path / "phase20a-422-candidate"
    case_dir.mkdir()
    # ``settings.gs_root`` is a computed @property → not settable
    # via attribute monkeypatch. Replace the module-level `settings`
    # binding instead so the route reads tmp_path.
    from types import SimpleNamespace
    monkeypatch.setattr(
        route_mod, "settings", SimpleNamespace(gs_root=tmp_path)
    )

    request = route_mod.RunRequest(
        case_id="phase20a-422-candidate",
        analysis_type="static",
        material_id="unobtanium-9001",
    )
    db = _make_mock_db()
    with pytest.raises(route_mod.HTTPException) as excinfo:
        asyncio.run(route_mod.run_calculation(request, db=db))
    assert excinfo.value.status_code == 422
    detail = str(excinfo.value.detail)
    assert "unobtanium-9001" in detail
    assert "library.json" in detail
