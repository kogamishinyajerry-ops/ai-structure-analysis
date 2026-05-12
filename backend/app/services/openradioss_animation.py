"""Render real OpenRadioss animation output (.A001..A###) as a GIF.

Tier 1 engineering candidate; not signed validation; not benchmark
agreement.

Operates on actual OpenRadioss .A### binary animation frames produced
by the engine. Each frame in the GIF corresponds to ONE .A### file —
node positions and element-deletion state come straight from
``vortex_radioss.animtod3plot.RadiossReader``. No interpolation, no
fabrication. If the engine wrote N frames the GIF has N frames.

Pure PIL renderer (no matplotlib / pyvista at runtime). Wireframe
side-view (XY-plane projection). Element edges are drawn only for
elements that are still alive in that frame — element deletion
(``element_solid_is_alive`` / ``element_shell_is_alive``) is the
visible signal of perforation.

Wording discipline (ADR-023): banner + manifest carry Tier 1
boundary tokens; no affirmative overclaim ever appears.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

CLAIM_BOUNDARY = "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"

_CANVAS_W = 1100
_CANVAS_H = 380
_MARGIN_X = 60
_MARGIN_Y = 60
_HUD_LINE_HEIGHT = 18

_BG_COLOR = (250, 250, 252)
_ALIVE_EDGE_COLOR = (40, 70, 140)
_DEAD_EDGE_COLOR = (210, 120, 90)
_NODE_COLOR = (40, 70, 140)
_AXIS_COLOR = (210, 210, 215)
_TEXT_COLOR = (30, 30, 30)
_BANNER_COLOR = (215, 70, 70)


@dataclass(frozen=True)
class OpenRadiossAnimationInput:
    case_id: str
    anim_files: tuple[Path, ...]  # ordered .A001, .A002, ... (or .gz)
    deck_source: str  # path to starter deck for provenance
    title: str = "OpenRadioss real-output animation"


def write_openradioss_animation(
    inp: OpenRadiossAnimationInput,
    output_dir: Path,
    *,
    frame_duration_ms: int = 200,
) -> Path:
    """Read every .A### frame in ``inp.anim_files`` and render to GIF.

    Returns the manifest path. Both ``openradioss_animation.gif`` and
    ``openradioss_animation_manifest.json`` land in ``output_dir``.
    """
    if not inp.anim_files:
        raise ValueError("anim_files must not be empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    gif_path = output_dir / "openradioss_animation.gif"
    manifest_path = output_dir / "openradioss_animation_manifest.json"

    # Lazy-import vortex-radioss so the module can be loaded in test envs
    # that don't have the openradioss extra installed.
    from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

    frames_data: list[dict[str, Any]] = []
    for src in inp.anim_files:
        path = _ungzip_if_needed(src)
        try:
            rr = RadiossReader(str(path))
            frames_data.append(_extract_frame(rr, source=str(src)))
        finally:
            if path != src:
                path.unlink(missing_ok=True)

    if not frames_data:
        raise RuntimeError("RadiossReader produced no usable frames")

    # Build a stable bbox across all frames so the camera doesn't pan.
    bbox = _bounding_box_across_frames(frames_data)

    pil_frames: list[Image.Image] = []
    for idx, frame in enumerate(frames_data):
        pil_frames.append(
            _render_frame(
                frame_data=frame,
                bbox=bbox,
                case_id=inp.case_id,
                title=inp.title,
                frame_index=idx,
                frame_count=len(frames_data),
            )
        )

    pil_frames[0].save(
        gif_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True,
    )

    manifest = {
        "schema_version": "openradioss-animation-manifest.v1",
        "claim_boundary": CLAIM_BOUNDARY,
        "claim_impact": (
            "Tier 1 visualization of REAL OpenRadioss .A### output. "
            "Each GIF frame = one solver-emitted animation frame; node "
            "positions and element-deletion state come straight from "
            "vortex-radioss. Not benchmark agreement; not signed validation."
        ),
        "case_id": inp.case_id,
        "title": inp.title,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "renderer": "PIL ImageDraw 2D wireframe (XY-plane projection)",
        "deck_source": inp.deck_source,
        "anim_source_files": [str(p) for p in inp.anim_files],
        "frame_count": len(frames_data),
        "frame_duration_ms": frame_duration_ms,
        "frame_size_px": [_CANVAS_W, _CANVAS_H],
        "per_frame": [
            {
                "source": f["source"],
                "timestep": f["timestep"],
                "node_count": f["node_count"],
                "element_count": f["element_count"],
                "elements_alive": f["elements_alive"],
                "elements_deleted": f["element_count"] - f["elements_alive"],
            }
            for f in frames_data
        ],
        "bounding_box": {
            "x_min": bbox[0],
            "x_max": bbox[1],
            "y_min": bbox[2],
            "y_max": bbox[3],
        },
        "artifact": {
            "kind": "openradioss_animation_gif",
            "file_name": gif_path.name,
            "size_bytes": gif_path.stat().st_size,
            "sha256": _sha256(gif_path),
        },
        "limitations": [
            "wireframe XY-plane projection; out-of-plane motion is "
            "not visualised",
            "stress / strain field colour overlay not yet rendered",
            "not signed validation",
            "not benchmark agreement",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ungzip_if_needed(src: Path) -> Path:
    if src.suffix != ".gz":
        return src
    with tempfile.NamedTemporaryFile(suffix=".A001", delete=False) as tmp_file:
        tmp = Path(tmp_file.name)
    with gzip.open(src, "rb") as fin, tmp.open("wb") as fout:
        shutil.copyfileobj(fin, fout)
    return tmp


def _extract_frame(rr: Any, *, source: str) -> dict[str, Any]:
    """Pull what we need from a RadiossReader-loaded frame.

    Supports both shell-only fixtures (GS-100 ball-impact) and
    solid-element decks (GS-102 1+1-hex projectile/plate).
    """
    arrays = rr.arrays
    coords = arrays.get("node_coordinates")
    if coords is None:
        raise RuntimeError(f"RadiossReader frame {source} has no node_coordinates")

    # Element block discovery — try shells first then solids.
    element_block: dict[str, Any] | None = None
    for prefix in ("element_solid", "element_shell"):
        node_idx_key = f"{prefix}_node_indexes"
        alive_key = f"{prefix}_is_alive"
        if node_idx_key in arrays:
            element_block = {
                "kind": prefix,
                "node_indexes": arrays[node_idx_key],
                "is_alive": arrays.get(alive_key),
            }
            break

    if element_block is None:
        raise RuntimeError(
            f"RadiossReader frame {source} has neither element_solid_* "
            "nor element_shell_* arrays"
        )

    node_indexes = element_block["node_indexes"]
    is_alive = element_block["is_alive"]
    # Fallback: assume all elements alive when array is missing.
    is_alive_list = (
        [True] * len(node_indexes) if is_alive is None else [bool(x) for x in is_alive]
    )

    elements_alive = sum(1 for a in is_alive_list if a)

    return {
        "source": source,
        "timestep": _first_float(arrays.get("timesteps")),
        "coords": [(float(c[0]), float(c[1]), float(c[2])) for c in coords],
        "element_kind": element_block["kind"],
        "element_node_indexes": [list(int(i) for i in row) for row in node_indexes],
        "element_is_alive": is_alive_list,
        "node_count": len(coords),
        "element_count": len(node_indexes),
        "elements_alive": elements_alive,
    }


def _bounding_box_across_frames(
    frames: list[dict[str, Any]],
) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for f in frames:
        for c in f["coords"]:
            xs.append(c[0])
            ys.append(c[1])
    if not xs:
        return (0.0, 1.0, 0.0, 1.0)
    return (min(xs), max(xs), min(ys), max(ys))


def _render_frame(
    *,
    frame_data: dict[str, Any],
    bbox: tuple[float, float, float, float],
    case_id: str,
    title: str,
    frame_index: int,
    frame_count: int,
) -> Image.Image:
    img = Image.new("RGB", (_CANVAS_W, _CANVAS_H), _BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _load_font(13)
    big_font = _load_font(15)
    banner_font = _load_font(11)

    project = _build_projector(bbox)

    # Bounding-box rectangle (faint frame around the simulation region)
    bx0, by0 = project(bbox[0], bbox[2])
    bx1, by1 = project(bbox[1], bbox[3])
    draw.rectangle(
        [(min(bx0, bx1), min(by0, by1)), (max(bx0, bx1), max(by0, by1))],
        outline=_AXIS_COLOR,
        width=1,
    )

    coords = frame_data["coords"]
    is_alive = frame_data["element_is_alive"]
    edges_alive: set[tuple[int, int]] = set()
    edges_dead: set[tuple[int, int]] = set()
    for el_nodes, alive in zip(frame_data["element_node_indexes"], is_alive, strict=True):
        for a, b in _element_edges(el_nodes):
            key = (min(a, b), max(a, b))
            (edges_alive if alive else edges_dead).add(key)

    # Draw dead-element edges first (faded), then alive edges on top
    for a, b in edges_dead:
        if a >= len(coords) or b >= len(coords):
            continue
        ax_px, ay_px = project(coords[a][0], coords[a][1])
        bx_px, by_px = project(coords[b][0], coords[b][1])
        draw.line([(ax_px, ay_px), (bx_px, by_px)], fill=_DEAD_EDGE_COLOR, width=1)

    for a, b in edges_alive:
        if a >= len(coords) or b >= len(coords):
            continue
        ax_px, ay_px = project(coords[a][0], coords[a][1])
        bx_px, by_px = project(coords[b][0], coords[b][1])
        draw.line([(ax_px, ay_px), (bx_px, by_px)], fill=_ALIVE_EDGE_COLOR, width=2)

    # Node markers (alive elements only — touched-by-alive nodes)
    touched: set[int] = set()
    for el_nodes, alive in zip(frame_data["element_node_indexes"], is_alive, strict=True):
        if alive:
            for n in el_nodes:
                touched.add(n)
    for n in touched:
        if n >= len(coords):
            continue
        px, py = project(coords[n][0], coords[n][1])
        draw.ellipse([(px - 2, py - 2), (px + 2, py + 2)], fill=_NODE_COLOR)

    # HUD
    elements_alive = frame_data["elements_alive"]
    elements_total = frame_data["element_count"]
    elements_deleted = elements_total - elements_alive
    timestep = frame_data["timestep"]
    hud_lines = [
        title,
        f"case: {case_id}  |  frame {frame_index + 1} / {frame_count}",
        f"source: {Path(frame_data['source']).name}",
        f"t = {timestep * 1e3:.4f} ms (solver emit time)",
        f"elements: {elements_alive} alive / {elements_deleted} deleted (of {elements_total})",
        f"nodes in frame: {frame_data['node_count']}",
    ]
    for i, line in enumerate(hud_lines):
        draw.text(
            (_MARGIN_X, 18 + i * _HUD_LINE_HEIGHT),
            line,
            fill=_TEXT_COLOR,
            font=big_font if i == 0 else font,
        )

    banner = (
        "Tier 1 engineering candidate  |  not signed validation  |  "
        "not benchmark agreement  |  REAL OpenRadioss output, no interpolation"
    )
    draw.text((_MARGIN_X, _CANVAS_H - 22), banner, fill=_BANNER_COLOR, font=banner_font)

    return img


def _element_edges(nodes: list[int]) -> list[tuple[int, int]]:
    """Return edges for the given element. 8-node hex → 12 edges, 4-node
    shell → 4 edges, otherwise sequential pairs."""
    if len(nodes) == 8:
        return [
            (nodes[0], nodes[1]),
            (nodes[1], nodes[2]),
            (nodes[2], nodes[3]),
            (nodes[3], nodes[0]),
            (nodes[4], nodes[5]),
            (nodes[5], nodes[6]),
            (nodes[6], nodes[7]),
            (nodes[7], nodes[4]),
            (nodes[0], nodes[4]),
            (nodes[1], nodes[5]),
            (nodes[2], nodes[6]),
            (nodes[3], nodes[7]),
        ]
    if len(nodes) == 4:
        return [
            (nodes[0], nodes[1]),
            (nodes[1], nodes[2]),
            (nodes[2], nodes[3]),
            (nodes[3], nodes[0]),
        ]
    return [(nodes[i], nodes[(i + 1) % len(nodes)]) for i in range(len(nodes))]


def _first_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        if hasattr(value, "reshape"):
            flattened = value.reshape(-1)
            return float(flattened[0]) if len(flattened) else 0.0
        if isinstance(value, (list, tuple)):
            return float(value[0]) if value else 0.0
        return float(value)
    except (IndexError, TypeError, ValueError):
        return 0.0


def _build_projector(bbox: tuple[float, float, float, float]):
    x_min, x_max, y_min, y_max = bbox
    span_x = max(x_max - x_min, 1e-9)
    span_y = max(y_max - y_min, 1e-9)
    avail_w = _CANVAS_W - 2 * _MARGIN_X
    avail_h = _CANVAS_H - 2 * _MARGIN_Y - 100  # leave room for HUD + banner
    scale = min(avail_w / span_x, avail_h / span_y)
    px_off = _MARGIN_X + (avail_w - span_x * scale) / 2
    py_off = _MARGIN_Y + 100 + (avail_h - span_y * scale) / 2

    def project(x_world: float, y_world: float) -> tuple[int, int]:
        px = int(px_off + (x_world - x_min) * scale)
        py = int(py_off + (y_max - y_world) * scale)
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
    "OpenRadiossAnimationInput",
    "write_openradioss_animation",
    "CLAIM_BOUNDARY",
]
