"""CalculiX ``solve.inp`` deck renderer (SimPlan + Jinja2 template).

This lives in the LOW driver layer (``tools/``) so BOTH the agent layer
(``agents.solver``) and the aeron FEABackend driver (``aeron.drivers.calculix_backend``)
can depend on it DOWNWARD — the ADR-015 dependency direction. It was previously a private
``agents.solver._render_inp_deck`` helper, which forced aeron to import UP into the agent
layer's private surface (the layering inversion fixed by audit Rank 7). The body is a pure
deck-render: jinja2 + a ``schemas.sim_plan.SimPlan``-shaped ``plan``, zero agent-layer
concerns. ``agents.solver`` now re-exports this under the old name for back-compat.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import jinja2

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_inp_deck(plan: Any, mesh_inp_path: str, output_dir: Path) -> Path:
    """Render a CalculiX ``solve.inp`` deck from SimPlan + Jinja2 template."""
    template_name = "linear_static.inp.j2"
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Solver template not found: {template_path}")

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR), encoding="utf-8"),
        undefined=jinja2.StrictUndefined,
    )
    template = env.get_template(template_name)

    material = plan.material
    load_magnitude = 0.0
    load_node_set = "Nall"
    for load in plan.loads:
        if load.kind == "concentrated_force":
            load_magnitude = load.parameters.get("magnitude", 0.0)
            load_node_set = load.parameters.get("node_set", "Nall")
            break

    fixed_node_set = "Nfix"
    for bc in plan.boundary_conditions:
        if bc.kind == "fixed":
            fixed_node_set = bc.parameters.get("node_set", "Nfix")
            break

    rendered = template.render(
        mesh_include=mesh_inp_path,
        material_name=material.name,
        youngs_modulus=material.youngs_modulus_pa,
        poissons_ratio=material.poissons_ratio,
        load_magnitude=load_magnitude,
        load_node_set=load_node_set,
        fixed_node_set=fixed_node_set,
    )

    deck_path = output_dir / "solve.inp"
    deck_path.write_text(rendered, encoding="utf-8")
    logger.info("Rendered solver deck -> %s", deck_path)
    return deck_path
