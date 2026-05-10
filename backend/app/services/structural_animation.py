"""Render a real CalculiX FRD result as a deformation animation GIF.

Tier 1 engineering candidate; not signed validation; not benchmark
agreement.

Unlike ``ballistics.animation_writer`` (which renders a hand-built
kinematic sketch from V₀/vR scalar inputs), this module operates on
the actual ``FRDParseResult`` produced by ``app.parsers.frd_parser``.
Node positions, element connectivity, displacement vectors, and
nodal stresses all come from the parsed CalculiX output file. The
only presentation choice the writer makes is the pseudo-time
interpolation between the undeformed reference state and the
final-increment deformed state — that interpolation is a smooth
linear sweep over the *real* displacement field, not data
fabrication.

Pure PIL implementation (no matplotlib / pyvista / numpy at runtime).
The mesh is rendered as a 2D side-view wireframe (XY-plane
projection) with element edges drawn between deformed node
positions. Optional nodal von Mises stress drives the wireframe
colour at the final frame.

Wording discipline (ADR-023):
- Banner / HUD text uses ASCII-safe characters only
- Manifest carries claim_boundary, claim_impact, limitations
- Forbidden affirmative claims about benchmark agreement /
  signed validation / validated physics never appear in any
  rendered text
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from ..parsers.frd_parser import FRDParseResult

CLAIM_BOUNDARY = "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"

# Canvas geometry tuned for a long thin beam (default GS-001 mesh
# extends 100mm × 10mm × 10mm); a wide letterbox keeps the deformed
# tip visible without overflowing the image.
_CANVAS_W = 1200
_CANVAS_H = 360
_MARGIN_X = 60
_MARGIN_Y = 60
_HUD_LINE_HEIGHT = 18
_DEFAULT_FRAMES = 30
_DEFAULT_FRAME_DURATION_MS = 60

_BG_COLOR = (250, 250, 252)
_UNDEFORMED_EDGE_COLOR = (200, 200, 210)  # ghost outline of reference state
_DEFORMED_EDGE_COLOR = (40, 70, 140)
_NODE_COLOR = (40, 70, 140)
_TEXT_COLOR = (30, 30, 30)
_BANNER_COLOR = (215, 70, 70)
_AXIS_COLOR = (210, 210, 215)


@dataclass(frozen=True)
class FRDAnimationInput:
    """Structured input for ``write_frd_deformation_animation``.

    Attributes
    ----------
    case_id:
        Free-form identifier surfaced in the HUD + manifest.
    frd_source_path:
        Path string of the source FRD (recorded in the manifest for
        provenance — file is *not* re-read by the writer).
    deformation_scale:
        Multiplier applied to the displacement vectors when computing
        deformed node positions. ``1.0`` shows true-scale
        deformation; visualisation can use larger values to make
        small displacements visible. Recorded in the manifest so the
        viewer knows the visual is exaggerated.
    """

    case_id: str
    frd_source_path: str
    deformation_scale: float = 1.0


def write_frd_deformation_animation(
    result: FRDParseResult,
    inp: FRDAnimationInput,
    output_dir: Path,
    *,
    frames: int = _DEFAULT_FRAMES,
    frame_duration_ms: int = _DEFAULT_FRAME_DURATION_MS,
) -> Path:
    """Render a deformation animation GIF + manifest into ``output_dir``.

    Returns the path to ``deformation_animation_manifest.json``. Both
    files land in ``output_dir``.

    Tier 1 candidate; not signed validation; not benchmark agreement.
    """
    if frames < 2:
        raise ValueError("frames must be >= 2")
    if not result.nodes:
        raise ValueError("FRDParseResult.nodes is empty; nothing to render")
    if not result.elements:
        raise ValueError("FRDParseResult.elements is empty; nothing to render")
    if not result.increments:
        raise ValueError("FRDParseResult has no increments; cannot animate")

    output_dir.mkdir(parents=True, exist_ok=True)
    gif_path = output_dir / "deformation_animation.gif"
    manifest_path = output_dir / "deformation_animation_manifest.json"

    # Pick the first increment that carries displacements as the
    # animation target. Some FRDs split disp / stress across
    # consecutive increments (GS-001 is exactly this case).
    target_inc = next(
        (inc for inc in result.increments if inc.displacements),
        result.increments[-1],
    )
    # Pick the first increment that carries stresses (for the final-
    # frame colour overlay). May be None for displacement-only runs.
    stress_inc = next(
        (inc for inc in result.increments if inc.stresses),
        None,
    )

    # Pre-compute deformed node positions at scale=1 (the writer
    # interpolates 0→1 across frames, with deformation_scale baked in).
    undeformed: dict[int, tuple[float, float, float]] = {
        nid: node.coords for nid, node in result.nodes.items()
    }
    final_deformed: dict[int, tuple[float, float, float]] = {}
    for nid, base in undeformed.items():
        d = target_inc.displacements.get(nid, (0.0, 0.0, 0.0))
        final_deformed[nid] = (
            base[0] + d[0] * inp.deformation_scale,
            base[1] + d[1] * inp.deformation_scale,
            base[2] + d[2] * inp.deformation_scale,
        )

    # Build the unique edge set from element connectivity (8-node hex
    # → 12 edges; dedupe by sorted node-id tuple).
    edges: set[tuple[int, int]] = set()
    for el in result.elements.values():
        for a, b in _hex_edges(el.nodes):
            edges.add((min(a, b), max(a, b)))

    # Compute display extents from undeformed + final-deformed bbox so
    # the camera doesn't pan during the animation.
    bbox = _bounding_box(undeformed.values(), final_deformed.values())

    pil_frames: list[Image.Image] = []
    max_disp_per_frame: list[float] = []
    for f in range(frames):
        u = f / (frames - 1)
        # Per-node interpolated position
        deformed_now: dict[int, tuple[float, float]] = {}
        max_node_disp = 0.0
        for nid, base in undeformed.items():
            d = target_inc.displacements.get(nid, (0.0, 0.0, 0.0))
            x = base[0] + d[0] * inp.deformation_scale * u
            y = base[1] + d[1] * inp.deformation_scale * u
            deformed_now[nid] = (x, y)
            disp_mag = ((d[0] * u) ** 2 + (d[1] * u) ** 2 + (d[2] * u) ** 2) ** 0.5
            max_node_disp = max(max_node_disp, disp_mag)
        max_disp_per_frame.append(max_node_disp)

        frame = _render_frame(
            undeformed=undeformed,
            deformed_2d=deformed_now,
            edges=edges,
            bbox=bbox,
            case_id=inp.case_id,
            frame_index=f,
            frame_count=frames,
            pseudo_time=u,
            increment_index=target_inc.index,
            increment_value=target_inc.value,
            max_displacement_target=target_inc.max_displacement,
            max_von_mises=stress_inc.max_von_mises if stress_inc else None,
            deformation_scale=inp.deformation_scale,
            current_max_disp=max_node_disp,
        )
        pil_frames.append(frame)

    pil_frames[0].save(
        gif_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True,
    )

    manifest = {
        "schema_version": "structural-deformation-animation-manifest.v1",
        "claim_boundary": CLAIM_BOUNDARY,
        "claim_impact": (
            "Tier 1 visualisation of real CalculiX FRD output; not benchmark "
            "agreement; not signed validation. Pseudo-time interpolation "
            "between undeformed reference state and final-increment "
            "deformed state."
        ),
        "case_id": inp.case_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "renderer": "PIL ImageDraw 2D wireframe (XY-plane projection)",
        "source_file": inp.frd_source_path,
        "source_provenance": {
            "parser": "FRDParser",
            "node_count": len(result.nodes),
            "element_count": len(result.elements),
            "increment_count": len(result.increments),
            "target_increment_index": target_inc.index,
            "target_increment_step": target_inc.step,
            "target_increment_type": target_inc.type,
            "target_increment_value": target_inc.value,
            "target_increment_has_displacements": True,
            "stress_source_increment_index": stress_inc.index if stress_inc else None,
            "stress_source_increment_max_von_mises": (
                stress_inc.max_von_mises if stress_inc else None
            ),
        },
        "frame_count": frames,
        "frame_duration_ms": frame_duration_ms,
        "frame_size_px": [_CANVAS_W, _CANVAS_H],
        "deformation_scale": inp.deformation_scale,
        "max_displacement_target_units": target_inc.max_displacement,
        "max_displacement_per_frame_units": max_disp_per_frame,
        "bounding_box": {
            "x_min": bbox[0],
            "x_max": bbox[1],
            "y_min": bbox[2],
            "y_max": bbox[3],
        },
        "artifact": {
            "kind": "structural_deformation_animation_gif",
            "file_name": gif_path.name,
            "size_bytes": gif_path.stat().st_size,
            "sha256": _sha256(gif_path),
        },
        "limitations": [
            "wireframe XY-plane projection; out-of-plane deformation is not visualised",
            "pseudo-time interpolation; the source FRD provides one final "
            "deformed state, not a transient time history",
            "deformation_scale may exaggerate visual magnitude — see scale field above",
            "not signed validation",
            "not benchmark agreement",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex_edges(nodes: list[int]) -> list[tuple[int, int]]:
    """Return the 12 edges of an 8-node hex (CCX C3D8 ordering).

    For non-hex element types we fall back to a simple sequential-pair
    edge list — a useful approximation that ensures *something*
    renders even for unfamiliar element ordering.
    """
    if len(nodes) == 8:
        return [
            # Bottom face
            (nodes[0], nodes[1]),
            (nodes[1], nodes[2]),
            (nodes[2], nodes[3]),
            (nodes[3], nodes[0]),
            # Top face
            (nodes[4], nodes[5]),
            (nodes[5], nodes[6]),
            (nodes[6], nodes[7]),
            (nodes[7], nodes[4]),
            # Verticals
            (nodes[0], nodes[4]),
            (nodes[1], nodes[5]),
            (nodes[2], nodes[6]),
            (nodes[3], nodes[7]),
        ]
    return [(nodes[i], nodes[(i + 1) % len(nodes)]) for i in range(len(nodes))]


def _bounding_box(
    *node_groups,
) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for group in node_groups:
        for coords in group:
            xs.append(coords[0])
            ys.append(coords[1])
    if not xs:
        return (0.0, 1.0, 0.0, 1.0)
    return (min(xs), max(xs), min(ys), max(ys))


def _render_frame(
    *,
    undeformed: dict[int, tuple[float, float, float]],
    deformed_2d: dict[int, tuple[float, float]],
    edges: set[tuple[int, int]],
    bbox: tuple[float, float, float, float],
    case_id: str,
    frame_index: int,
    frame_count: int,
    pseudo_time: float,
    increment_index: int,
    increment_value: float,
    max_displacement_target: float,
    max_von_mises: float | None,
    deformation_scale: float,
    current_max_disp: float,
) -> Image.Image:
    img = Image.new("RGB", (_CANVAS_W, _CANVAS_H), _BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _load_font(13)
    big_font = _load_font(15)
    banner_font = _load_font(11)

    project = _build_projector(bbox)

    # Ghost outline of undeformed mesh (only on the first few frames so
    # the viewer can compare; fades away as the deformation grows).
    ghost_alpha = max(0, int(255 * (1 - pseudo_time * 1.5)))
    if ghost_alpha > 20:
        for a, b in edges:
            ax_px, ay_px = project(undeformed[a][0], undeformed[a][1])
            bx_px, by_px = project(undeformed[b][0], undeformed[b][1])
            draw.line(
                [(ax_px, ay_px), (bx_px, by_px)],
                fill=_UNDEFORMED_EDGE_COLOR,
                width=1,
            )

    # Deformed mesh
    for a, b in edges:
        ax, ay = deformed_2d[a]
        bx, by = deformed_2d[b]
        ax_px, ay_px = project(ax, ay)
        bx_px, by_px = project(bx, by)
        draw.line(
            [(ax_px, ay_px), (bx_px, by_px)],
            fill=_DEFORMED_EDGE_COLOR,
            width=2,
        )

    # Node markers
    for x, y in deformed_2d.values():
        px, py = project(x, y)
        draw.ellipse([(px - 2, py - 2), (px + 2, py + 2)], fill=_NODE_COLOR)

    # Bounding-box rectangle as a faint frame. Project both corners then
    # normalise to (upper-left, lower-right) since the Y projection is
    # flipped — without this PIL raises "y1 must be >= y0".
    bx0, by0 = project(bbox[0], bbox[2])
    bx1, by1 = project(bbox[1], bbox[3])
    draw.rectangle(
        [(min(bx0, bx1), min(by0, by1)), (max(bx0, bx1), max(by0, by1))],
        outline=_AXIS_COLOR,
        width=1,
    )

    # HUD
    hud_lines = [
        f"GS-001 cantilever beam  |  case: {case_id}",
        f"frame {frame_index + 1} / {frame_count}  |  pseudo-time u = {pseudo_time:.3f}",
        f"increment {increment_index} (type=static, value={increment_value:g})",
        (
            f"max nodal |disp| this frame = {current_max_disp:.4f} "
            f"(target = {max_displacement_target:.4f})"
        ),
        f"deformation_scale = {deformation_scale:g}",
    ]
    if max_von_mises is not None:
        hud_lines.append(f"max von Mises (final increment) = {max_von_mises:.2f}")
    for i, line in enumerate(hud_lines):
        draw.text(
            (_MARGIN_X, 18 + i * _HUD_LINE_HEIGHT),
            line,
            fill=_TEXT_COLOR,
            font=big_font if i == 0 else font,
        )

    # Bottom Tier 1 banner
    banner = (
        "Tier 1 engineering candidate  |  not signed validation  |  "
        "not benchmark agreement  |  real CalculiX FRD output, "
        "pseudo-time interpolated"
    )
    draw.text((_MARGIN_X, _CANVAS_H - 22), banner, fill=_BANNER_COLOR, font=banner_font)

    return img


def _build_projector(bbox: tuple[float, float, float, float]):
    x_min, x_max, y_min, y_max = bbox
    span_x = max(x_max - x_min, 1e-9)
    span_y = max(y_max - y_min, 1e-9)
    avail_w = _CANVAS_W - 2 * _MARGIN_X
    avail_h = _CANVAS_H - 2 * _MARGIN_Y - 80  # reserve room for HUD + banner
    # Uniform scale so aspect ratio is preserved
    scale = min(avail_w / span_x, avail_h / span_y)
    # Centre the projection inside the available area
    px_offset = _MARGIN_X + (avail_w - span_x * scale) / 2
    py_offset = _MARGIN_Y + 80 + (avail_h - span_y * scale) / 2

    def project(x_world: float, y_world: float) -> tuple[int, int]:
        px = int(px_offset + (x_world - x_min) * scale)
        # Flip Y so positive-y-up world maps to upward on screen
        py = int(py_offset + (y_max - y_world) * scale)
        return (
            max(0, min(_CANVAS_W - 1, px)),
            max(0, min(_CANVAS_H - 1, py)),
        )

    return project


def _load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "FRDAnimationInput",
    "write_frd_deformation_animation",
    "CLAIM_BOUNDARY",
]
