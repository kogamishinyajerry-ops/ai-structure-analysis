"""FM-04a Phase 18 E (round 2) — materials HTTP route handler tests.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

Two pre-existing local-env breakages prevent the standard
FastAPI ``TestClient`` flow:

* ``app.api.__init__`` instantiates ``NLParser()`` at module load
  (Sprint-1 artifact). Combined with a stale ``openai`` package
  pinned to the legacy ``proxies`` kwarg, this trips on import.
* The installed ``httpx`` version dropped ``Client(app=app, ...)``
  shape, which Starlette's ``TestClient`` constructor relies on.

Neither breakage is Phase 18's responsibility. To keep the route
tests stable against them, this file calls the route HANDLER
functions directly (they are plain Python — FastAPI decorators
only register the path). The handlers load
``app.services.materials`` (clean dependency) without going through
the ``app.api`` package init.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_materials_route_module():
    """Load ``backend/app/api/routes/materials.py`` directly without
    triggering ``app.api.__init__``.
    """
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    target = (
        repo_root / "backend" / "app" / "api" / "routes" / "materials.py"
    )
    spec = importlib.util.spec_from_file_location(
        "phase18e_materials_route", target
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def route_mod():
    return _load_materials_route_module()


def test_list_handler_returns_phase_18c_baseline_first(route_mod) -> None:
    """Phase 18 C baseline 3 materials remain at the head of the
    payload list. Phase 19 C appends 5 more — pinned by Slice C
    tests separately."""
    body = route_mod.get_materials_list()
    assert body["count"] >= 3
    ids = [m["id"] for m in body["materials"]][:3]
    assert ids == [
        "steel-s355",
        "aluminium-6061-t6",
        "titanium-ti-6al-4v",
    ]


def test_list_handler_carries_claim_banners(route_mod) -> None:
    body = route_mod.get_materials_list()
    assert body["claim_tier"] == "Tier 1 engineering candidate"
    assert "tier1_engineering_candidate" in body["claim_boundary"]
    assert "not_signed_validation" in body["claim_boundary"]


def test_each_material_payload_carries_provenance(route_mod) -> None:
    body = route_mod.get_materials_list()
    for mat in body["materials"]:
        assert mat["reference"], (
            f"material {mat['id']!r} payload has empty reference"
        )
        assert len(mat["reference"]) >= 12
        assert mat["claim_tier"] == "Tier 1 engineering candidate"


@pytest.mark.parametrize(
    "material_id,expected_e_pa,expected_nu",
    [
        ("steel-s355", 210e9, 0.3),
        ("aluminium-6061-t6", 68.9e9, 0.33),
        ("titanium-ti-6al-4v", 113.8e9, 0.342),
    ],
)
def test_get_one_returns_pinned_properties(
    route_mod, material_id: str, expected_e_pa: float, expected_nu: float
) -> None:
    body = route_mod.get_material_by_id(material_id)
    assert body["id"] == material_id
    assert body["youngs_modulus_pa"] == expected_e_pa
    assert body["poisson_ratio"] == expected_nu


def test_get_one_returns_404_on_unknown(route_mod) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        route_mod.get_material_by_id("does-not-exist")
    assert excinfo.value.status_code == 404
    assert "unknown material id" in excinfo.value.detail


def test_list_includes_yield_and_ultimate_when_present(route_mod) -> None:
    body = route_mod.get_materials_list()
    for mat in body["materials"]:
        assert mat["yield_stress_pa"] is not None
        assert mat["ultimate_stress_pa"] is not None
        assert mat["ultimate_stress_pa"] >= mat["yield_stress_pa"]


def test_get_one_carries_human_name(route_mod) -> None:
    body = route_mod.get_material_by_id("steel-s355")
    assert body["name"] == "Structural Steel S355"


def test_route_has_two_registered_paths(route_mod) -> None:
    """Defense: every reviewer-facing route shape change must be
    pinned by a test so silent surface drift trips here."""
    paths = sorted({r.path for r in route_mod.router.routes})
    assert paths == ["/materials/", "/materials/{material_id}"]
