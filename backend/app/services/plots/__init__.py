"""PNG-output minimum for the MVP static-strength report.

RFC-001 §6.1 Bucket B exception: the full PyVista-based VisualizationService
is frozen under `app._frozen.sprint2.visualization` (3D HTML scene exports,
deformation animation, delta visualization). Only the *minimum* PNG-rendering
surface needed by the MVP equipment-foundation static-strength report
(displacement / stress / deformed-shape PNGs) is exposed here.

Layer 3 report generation (W3-W4 per RFC §6.4) will import from this
module. Routes/`api/routes/visualization.py` continues to import from
`_frozen.sprint2.visualization` for HTML-scene fallback paths until those
features are deleted (per `_frozen/sprint2/README.md` expiration policy)
or rebuilt on the Layer-2 ReaderHandle protocol.

This module re-exports — no new logic. Adding PNG features here is OK
(MVP-relevant); adding HTML/3D/web export is NOT (lives in frozen).
"""

from __future__ import annotations

from app._frozen.sprint2.visualization import (
    VisualizationService,
    get_visualization_service,
)

__all__ = [
    "VisualizationService",
    "get_visualization_service",
    "render_displacement_png",
    "render_stress_png",
    "render_deformed_png",
]


def render_displacement_png(nodes, displacements, output_path, *, title="位移分布", component="magnitude"):
    """Thin shim — the MVP-relevant PNG entry for displacement plots."""
    svc = get_visualization_service()
    return svc.create_displacement_plot(
        nodes=nodes,
        displacements=displacements,
        title=title,
        output_path=output_path,
        component=component,
    )


def render_stress_png(nodes, stresses, output_path, *, title="应力分布", stress_component="von_mises"):
    """Thin shim — the MVP-relevant PNG entry for stress plots."""
    svc = get_visualization_service()
    return svc.create_stress_plot(
        nodes=nodes,
        stresses=stresses,
        title=title,
        output_path=output_path,
        stress_component=stress_component,
    )


def render_deformed_png(nodes, displacements, elements, output_path, *, deformation_scale=1.0, title="变形图"):
    """Thin shim — the MVP-relevant PNG entry for deformed-shape plots."""
    svc = get_visualization_service()
    return svc.create_deformed_shape(
        nodes=nodes,
        displacements=displacements,
        elements=elements,
        deformation_scale=deformation_scale,
        title=title,
        output_path=output_path,
    )
