"""Smoke test — verify every new module is importable.

This ensures the skeleton has no syntax errors and all
``__init__.py`` files are correctly structured.
"""

from __future__ import annotations

import importlib

import pytest

MODULES = [
    "agents",
    "agents.architect",
    "agents.geometry",
    "agents.mesh",
    "agents.solver",
    "agents.reviewer",
    "agents.viz",
    "agents.graph",
    "tools",
    "tools.freecad_driver",
    "tools.gmsh_driver",
    "tools.calculix_driver",
    "tools.frd_parser",
    "schemas",
    "schemas.sim_plan",
    "checkers",
    "checkers.jacobian",
    "checkers.geometry_checker",
    "reporters",
    "reporters.markdown",
    "reporters.vtp",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_import(module_name: str):
    """Each skeleton module must be importable without errors."""
    mod = importlib.import_module(module_name)
    assert mod is not None
