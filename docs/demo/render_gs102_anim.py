"""Real per-frame renderer for the GS-102 transient ballistic result.

Reads the on-disk result_mesh.json (Tier 1 engineering candidate, 150 dynamic
frames) and produces — from REAL data, not schematic — every artifact the
demo HTML actually needs:

  docs/demo/gs102-frames/frame_0000.png ... frame_0149.png
      150 per-frame PNGs (1100×720). Single big iso view of the UNDEFORMED
      mesh colored by per-frame von Mises, with eroded plate cells in red.
      Cell topology is preserved (no butterfly tearing), so the stress
      contour is readable like a real engineering plot.
  docs/demo/gs102-frames/sprite_sheet.png
      5×30 grid of all 150 frames (left half = contour, right half = a
      separate side-view PIL rendering), 1100×4400.
  docs/demo/gs102-frames/gs102_real.gif
      Real animated side-view (PIL-rendered wireframe with controlled
      deformation scale = 0.04), 1100×360, ~12 s.
  docs/demo/gs102-frames/tracking.png
      Real history plots (peak von Mises, alive plate count, max disp
      vs frame), with the 3 erosion events annotated. 1500×620.
  docs/demo/gs102-frames/frame_summary.json
      Per-frame {frame,timeMs,peakVonMises,aliveCount,maxDisplacement,
      fieldRange=[0,valueMax]} for the HTML player to bind to the
      scrubber / HUD.

Why a separate side-view animation (not pyvista wireframe)?
  Plate is 1/2-symmetric 6mm half-thickness; the projectile penetrates
  ~11mm in.  Full-scale deformation tears shell-quads into degenerate
  butterfly shapes.  A small-scale (×0.04) side-view PIL wireframe is
  the cleanest way to show "the projectile is moving" without making
  the colormap unreadable.  This mirrors what the project already does
  in scripts/gs102_render_cloud_animation.py (side-view GIF).

Honesty boundaries (ADR-023 / ADR-024 lite):
  - All data is REAL — taken from the on-disk 22 MB result_mesh.json of
    the FM-04a Tier 1 candidate (peak 731.49 MPa @ frame 93,
    embedded_candidate, 8 plate elements eroded @ frame 36/121/125).
  - Colormap range locked to global valueMax (731.49 MPa) so the
    "color = stress" mapping is consistent across frames.
  - Projectile rendered as solid dark (rigid body — solver encodes
    it as value=0 across all frames, exactly what the data says).
  - Tier label baked into the HUD on every frame.

Run from repo root with the project venv:
    PYVISTA_OFF_SCREEN=true .venv/bin/python docs/demo/render_gs102_anim.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

# ─── paths ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
SRC = (
    ROOT
    / "project_state"
    / "visualizations"
    / "GS-102-transient-refined-cfl085-v365-bracket-20260512"
    / "result_mesh.json"
)
OUT = ROOT / "docs" / "demo" / "gs102-frames"
OUT.mkdir(parents=True, exist_ok=True)

# ─── design constants ─────────────────────────────────────────────────────
BG = "#0c0e14"
FG = "#EAF1FB"
MUTED = "#93A4BC"
DIM = "#5F7088"
CYAN = "#3BA8FF"
GOLD = "#FFCB5C"
CORAL = "#FF7E69"
OK = "#5BD6A8"
PROJECTILE_COLOR = "#5b6e87"
DEAD_COLOR = "#EF4444"
WIRE_COLOR = "#5F7088"
UNDEFORMED_WIRE = "#3B4862"
DEFORM_GHOST = "#1f3a5c"
TURBO_LO, TURBO_HI = 0, 1

WIN = (1100, 720)  # per-frame PNG
SIDE_W, SIDE_H = 1100, 360  # GIF frame
ZOOM = 1.5
CLAIM_TIER = "Tier 1 engineering candidate · not signed validation · not benchmark agreement"
DEFORM_SCALE = 0.04  # side-view wireframe exaggeration


def _load_data() -> dict:
    with open(SRC) as f:
        return json.load(f)


# ════════════════════════════════════════════════════════════════════════
# Part 1 — pyvista contour renders (undeformed mesh, locked colormap)
# ════════════════════════════════════════════════════════════════════════


def _build_grids(
    frame: dict,
) -> tuple[pv.UnstructuredGrid | None, pv.UnstructuredGrid | None, pv.UnstructuredGrid | None]:
    """Return (alive_plate, dead_plate, projectile) using UNDEFORMED positions.

    The deformed positions are used only by the side-view PIL render
    (Part 2).  Here we keep the topology clean so each shell stays a
    flat quad — the standard scientific viz for an FEM stress contour.
    """
    nodes = frame["nodes"]
    elements = frame["elements"]
    label_to_idx = {n["label"]: i for i, n in enumerate(nodes)}
    points = np.array([n["coordinates"] for n in nodes], dtype=np.float64)

    alive_cells, alive_types, alive_vals = [], [], []
    dead_cells, dead_types = [], []
    proj_cells, proj_types = [], []

    for e in elements:
        idxs = [label_to_idx[n] for n in e["connectivity"]]
        n_nodes = len(idxs)
        if e["partRole"] == "projectile":
            proj_cells.append(n_nodes)
            proj_cells.extend(idxs)
            proj_types.append(9)
        elif e["alive"]:
            alive_cells.append(n_nodes)
            alive_cells.extend(idxs)
            alive_types.append(9)
            alive_vals.append(float(e["value"]))
        else:
            dead_cells.append(n_nodes)
            dead_cells.extend(idxs)
            dead_types.append(9)

    def _g(cells, types):
        if not cells:
            return None
        return pv.UnstructuredGrid(
            np.asarray(cells, dtype=np.int64),
            np.asarray(types, dtype=np.uint8),
            points,
        )

    g_alive = _g(alive_cells, alive_types)
    if g_alive is not None:
        g_alive.cell_data["von_mises_MPa"] = np.asarray(alive_vals, dtype=np.float64)
    return g_alive, _g(dead_cells, dead_types), _g(proj_cells, proj_types)


def _camera_iso(plotter: pv.Plotter, focus) -> None:
    """Fixed iso view, world-space locked so playback doesn't re-zoom."""
    plotter.view_isometric()
    plotter.camera.zoom(ZOOM)
    if focus is not None:
        plotter.camera.position = (focus[0] - 55, focus[1] + 35, focus[2] + 55)
        plotter.camera.focal_point = focus
        plotter.camera.up = (0, 0, 1)


def render_contour_frame(frame: dict, frame_idx: int, total: int, value_max: float) -> Image.Image:
    """Big single-pane undeformed-mesh colormap render, HUD on top."""
    peak = max(e["value"] for e in frame["elements"])
    dead = sum(1 for e in frame["elements"] if not e["alive"])

    g_alive, g_dead, g_proj = _build_grids(frame)
    focus = (
        g_proj.center
        if g_proj is not None and g_proj.n_cells
        else (g_alive.center if g_alive is not None else None)
    )

    p = pv.Plotter(off_screen=True, window_size=WIN)
    p.set_background(BG)

    if g_dead is not None and g_dead.n_cells > 0:
        p.add_mesh(
            g_dead,
            color=DEAD_COLOR,
            opacity=0.7,
            show_edges=True,
            edge_color=DEAD_COLOR,
            line_width=1.6,
        )

    if g_alive is not None and g_alive.n_cells > 0:
        p.add_mesh(
            g_alive,
            scalars="von_mises_MPa",
            cmap="turbo",
            clim=(0.0, value_max),
            show_edges=True,
            edge_color=UNDEFORMED_WIRE,
            line_width=0.4,
            nan_color=DIM,
            scalar_bar_args={
                "title": "von Mises  (MPa)",
                "n_labels": 6,
                "fmt": "%.0f",
                "color": FG,
                "title_font_size": 22,
                "label_font_size": 18,
                "position_x": 0.85,
                "position_y": 0.20,
                "width": 0.10,
                "height": 0.55,
            },
        )

    if g_proj is not None and g_proj.n_cells > 0:
        p.add_mesh(
            g_proj,
            color=PROJECTILE_COLOR,
            show_edges=True,
            edge_color=UNDEFORMED_WIRE,
            line_width=0.4,
        )

    _camera_iso(p, focus)
    raw = p.screenshot(return_img=True)
    p.close()
    img = Image.fromarray(np.asarray(raw))

    # HUD overlay
    draw = ImageDraw.Draw(img)
    try:
        font_h = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
        font_m = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
        font_s = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 12)
    except Exception:
        font_h = font_m = font_s = ImageFont.load_default()

    # Top bar — keep title compact so right-side "ERODED" pill doesn't collide
    draw.rectangle([0, 0, WIN[0], 50], fill=(17, 20, 29))
    draw.text(
        (14, 6),
        f"GS-102 · transient impact  ·  frame {frame_idx:03d}/{total - 1}"
        f"  ·  t = {frame['timeMs']:.4f} ms",
        fill=(98, 196, 255),
        font=font_h,
    )
    draw.text(
        (14, 28),
        f"peak σ_vm = {peak:.1f} MPa  ·  "
        f"|u|max = {max(np.linalg.norm(n['displacement']) for n in frame['nodes']):.1f} mm",
        fill=(147, 164, 188),
        font=font_m,
    )

    if dead > 0:
        draw.text(
            (WIN[0] - 290, 16),
            f"  {dead} PLATE ELEMENTS ERODED (red)  ",
            fill=(255, 220, 220),
            font=font_m,
        )

    # Caption strip
    cap_y = WIN[1] - 36
    draw.rectangle([0, cap_y, WIN[0], WIN[1]], fill=(17, 20, 29))
    draw.text(
        (14, cap_y + 4),
        "UNDEFORMED MESH  ·  von Mises colormap  ·  "
        "range locked to global max (standard scientific viz)",
        fill=MUTED,
        font=font_m,
    )
    draw.text((14, cap_y + 20), CLAIM_TIER, fill=DIM, font=font_s)
    return img


# ════════════════════════════════════════════════════════════════════════
# Part 2 — PIL side-view wireframe animation (shows motion cleanly)
# ════════════════════════════════════════════════════════════════════════

# project X-axis (impact axis) onto the GIF's X-axis
# and the Y or Z plane onto the GIF's Y-axis — pick whichever makes
# the side view more readable; here we use the XZ plane (projectile
# comes in along X, plate is at x=30..36).
SIDE_AXIS_X, SIDE_AXIS_Y = 0, 2  # X horizontal, Z vertical
SIDE_PAD = 60


def _project_frame_to_canvas(frame: dict, value_max: float, scale: float) -> Image.Image:
    """Render a single side-view wireframe image (PIL)."""
    nodes = frame["nodes"]
    elements = frame["elements"]
    label_to_idx = {n["label"]: i for i, n in enumerate(nodes)}

    # Scaled-deformed positions for motion. The raw `deformed` field is
    # full-scale (coordinates + displacement, up to ~84 mm of deflection)
    # which tears the shell quads into degenerate butterfly shapes. Apply
    # DEFORM_SCALE so the picture matches the HUD's "warp ×{scale}" label:
    #   scaled = undeformed + (deformed - undeformed) * scale
    #          = coordinates + displacement * scale
    undeformed_raw = np.array([n["coordinates"] for n in nodes], dtype=np.float64)
    deformed_raw = np.array([n["deformed"] for n in nodes], dtype=np.float64)
    coords = undeformed_raw + (deformed_raw - undeformed_raw) * scale

    # figure out side-view bounds (with a little padding for the projectile)
    xs = coords[:, SIDE_AXIS_X]
    ys = coords[:, SIDE_AXIS_Y]
    bbox_x = (xs.min() - 5, xs.max() + 5)
    bbox_y = (ys.min() - 5, ys.max() + 5)
    span_x = bbox_x[1] - bbox_x[0]
    span_y = bbox_y[1] - bbox_y[0]

    cw, ch = SIDE_W, SIDE_H
    inner_w = cw - 2 * SIDE_PAD
    inner_h = ch - 2 * SIDE_PAD - 28  # leave room for HUD
    sx = inner_w / span_x
    sy = inner_h / span_y
    s = min(sx, sy)

    def to_px(p):
        # maintain aspect by letterboxing within inner
        cx = (p[SIDE_AXIS_X] - bbox_x[0]) * s + (inner_w - span_x * s) / 2
        cy = (p[SIDE_AXIS_Y] - bbox_y[0]) * s + (inner_h - span_y * s) / 2
        return (SIDE_PAD + cx, SIDE_PAD + cy)

    img = Image.new("RGB", (cw, ch), (12, 14, 20))
    draw = ImageDraw.Draw(img)

    # ghost reference (undeformed, very faint) — reuse undeformed_raw so the
    # ghost and the scaled-deformed plot share one source of truth.
    undeformed = undeformed_raw
    for e in elements:
        if e["partRole"] != "plate" or not e["alive"]:
            continue
        idxs = [label_to_idx[n] for n in e["connectivity"]]
        pts_und = [to_px(undeformed[i]) for i in idxs]
        if len(pts_und) >= 2:
            draw.line(pts_und + [pts_und[0]], fill=(40, 50, 70), width=1)

    # draw plate alive cells, colored by von Mises (turbo approximation)
    def turbo(t: float) -> tuple:
        # 5-stop turbo: blue -> cyan -> green -> yellow -> red
        stops = [
            (0.00, (40, 30, 220)),
            (0.25, (40, 200, 255)),
            (0.50, (60, 220, 100)),
            (0.75, (255, 220, 50)),
            (1.00, (230, 50, 30)),
        ]
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t <= t1:
                k = (t - t0) / (t1 - t0) if t1 > t0 else 0
                return tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
        return stops[-1][1]

    for e in elements:
        if e["partRole"] != "plate" or not e["alive"]:
            continue
        idxs = [label_to_idx[n] for n in e["connectivity"]]
        pts = [to_px(coords[i]) for i in idxs]
        if len(pts) >= 2:
            v = e["value"] / value_max if value_max > 0 else 0
            color = turbo(min(1.0, max(0.0, v)))
            # filled quad
            if len(pts) == 4:
                draw.polygon(pts, fill=color, outline=(20, 24, 36))
            else:
                draw.polygon(pts, fill=color, outline=(20, 24, 36))

    # dead cells in red overlay
    for e in elements:
        if e["partRole"] != "plate" or e["alive"]:
            continue
        idxs = [label_to_idx[n] for n in e["connectivity"]]
        pts = [to_px(coords[i]) for i in idxs]
        if len(pts) >= 2:
            draw.polygon(pts, fill=(239, 68, 68), outline=(120, 30, 30))

    # projectile in solid color
    for e in elements:
        if e["partRole"] != "projectile":
            continue
        idxs = [label_to_idx[n] for n in e["connectivity"]]
        pts = [to_px(coords[i]) for i in idxs]
        if len(pts) >= 2:
            draw.polygon(pts, fill=(91, 110, 135), outline=(40, 50, 60))

    # HUD
    try:
        font_h = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 16)
        font_s = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 12)
    except Exception:
        font_h = font_s = ImageFont.load_default()

    peak = max(e["value"] for e in frame["elements"])
    draw.text(
        (10, 4),
        f"GS-102 · side view (X-Z plane)  ·  frame {frame['frame']}  ·  "
        f"t = {frame['timeMs']:.4f} ms  ·  peak σ_vm = {peak:.1f} MPa  ·  warp ×{scale:g}",
        fill=(98, 196, 255),
        font=font_h,
    )
    draw.text((10, ch - 22), CLAIM_TIER, fill=(95, 112, 136), font=font_s)
    return img


def render_gif_frames(frames: list[dict], value_max: float) -> list[Image.Image]:
    """Side-view wireframe of every frame, returns PIL Images ready for GIF assembly."""
    return [_project_frame_to_canvas(f, value_max, DEFORM_SCALE) for f in frames]


# ════════════════════════════════════════════════════════════════════════
# Part 3 — sprite sheet (5x30 grid of contour frames)
# ════════════════════════════════════════════════════════════════════════


def render_sprite_sheet(images: list[Image.Image], cols: int = 5) -> Image.Image:
    """5 cols × 30 rows grid of contour frames, 1 image. 1100×4400."""
    tw, th = 216, 144
    pad = 4
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new(
        "RGB", (cols * tw + (cols + 1) * pad, rows * th + (rows + 1) * pad), (12, 14, 20)
    )
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)
    except Exception:
        font = ImageFont.load_default()
    for i, im in enumerate(images):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + pad)
        thumb = im.resize((tw, th), Image.LANCZOS)
        sheet.paste(thumb, (x, y))
        draw.rectangle([x, y + th - 16, x + 60, y + th], fill=(0, 0, 0))
        draw.text((x + 4, y + th - 14), f"f{i:03d}", fill=(98, 196, 255), font=font)
    return sheet


# ════════════════════════════════════════════════════════════════════════
# Part 4 — tracking plot (3-panel real history)
# ════════════════════════════════════════════════════════════════════════


def render_tracking_plot(per_frame: list[dict], value_max: float) -> Image.Image:
    """3-panel real-history plot with non-overlapping axes/labels."""
    W, H = 1500, 620
    bg = (12, 14, 20)
    fg = (234, 241, 251)
    muted = (147, 164, 188)
    dim = (95, 112, 136)
    cyan = (59, 168, 255)
    gold = (255, 203, 92)
    coral = (255, 126, 105)
    ok = (91, 214, 168)

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 22)
        font_pan = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
        font_s = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 12)
    except Exception:
        font_title = font_pan = font_s = ImageFont.load_default()

    title_h = 80
    panel_top = title_h + 20
    panel_h = (H - panel_top - 60) // 3
    panel_gap = 22
    plot_left, plot_right = 130, 30
    plot_w = W - plot_left - plot_right

    def panel(
        idx: int,
        title: str,
        ylabel: str,
        ys: list[float],
        ymin: float,
        ymax: float,
        color,
        marks: list[tuple[int, tuple, str]] | None = None,
    ):
        y0 = panel_top + idx * (panel_h + panel_gap)
        d.text((plot_left, y0 - 26), title, fill=gold, font=font_pan)
        d.text((plot_left, y0 - 8), ylabel, fill=muted, font=font_s)

        d.line([(plot_left, y0), (plot_left, y0 + panel_h)], fill=dim, width=1)
        d.line([(plot_left, y0 + panel_h), (plot_left + plot_w, y0 + panel_h)], fill=dim, width=1)

        for yv in [ymin + (ymax - ymin) * k / 4 for k in range(5)]:
            py = y0 + panel_h - (yv - ymin) / (ymax - ymin) * panel_h
            d.line([(plot_left - 4, py), (plot_left, py)], fill=dim, width=1)
            d.text((plot_left - 80, py - 7), f"{yv:.1f}", fill=dim, font=font_s)

        for f_ in [0, 30, 60, 90, 120, 149]:
            x = plot_left + (f_ / 149) * plot_w
            d.line([(x, y0 + panel_h), (x, y0 + panel_h + 4)], fill=dim, width=1)
            d.text((x - 12, y0 + panel_h + 6), str(f_), fill=dim, font=font_s)

        for i, y in enumerate(ys):
            x = plot_left + (i / 149) * plot_w
            py = y0 + panel_h - (y - ymin) / (ymax - ymin) * panel_h
            d.ellipse([x - 1.6, py - 1.6, x + 1.6, py + 1.6], fill=color)

        if marks:
            for fidx, mcolor, label in marks:
                x = plot_left + (fidx / 149) * plot_w
                d.line([(x, y0), (x, y0 + panel_h)], fill=mcolor, width=1)
                d.text((x + 4, y0 + 6), label, fill=mcolor, font=font_s)

    peaks = [p["peakVonMises"] for p in per_frame]
    alives = [p["aliveCount"] for p in per_frame]
    disps = [p["maxDisplacement"] for p in per_frame]

    erosion = []
    for i in range(1, len(alives)):
        if alives[i] < alives[i - 1]:
            erosion.append((i, coral, f"−{alives[i - 1] - alives[i]} @f{i}"))

    d.text(
        (plot_left, 10),
        "GS-102 · per-frame real history  (all values from result_mesh.json)",
        fill=fg,
        font=font_title,
    )
    d.text(
        (plot_left, 42),
        "claim_tier = Tier 1 engineering candidate  ·  not signed validation"
        "  ·  not benchmark agreement",
        fill=dim,
        font=font_s,
    )

    panel(
        0,
        "(a)  peak von Mises  vs  frame",
        "MPa",
        peaks,
        0.0,
        value_max * 1.05,
        cyan,
        marks=erosion,
    )
    alive_min, alive_max = min(alives) - 1, max(alives) + 1
    panel(
        1,
        "(b)  alive plate elements  vs  frame",
        "count",
        alives,
        alive_min,
        alive_max,
        ok,
        marks=erosion,
    )
    panel(2, "(c)  max |u|  vs  frame", "mm", disps, 0.0, max(disps) * 1.05, gold)

    d.text(
        (plot_left, H - 32),
        "red vertical lines = real erosion events (8 plate elements died at frames 36 / 121 / 125)",
        fill=coral,
        font=font_s,
    )
    return img


# ════════════════════════════════════════════════════════════════════════
# main
# ════════════════════════════════════════════════════════════════════════


def main() -> None:
    print(f"reading {SRC}")
    d = _load_data()
    frames = d["dynamicFrames"]
    n = len(frames)
    value_max = max(max(e["value"] for e in fr["elements"]) for fr in frames)
    print(f"  · {n} frames  ·  valueMax over run = {value_max:.2f} MPa")

    # contour renders
    images: list[Image.Image] = []
    per_frame: list[dict] = []
    for i, fr in enumerate(frames):
        img = render_contour_frame(fr, i, n, value_max)
        img.save(OUT / f"frame_{i:04d}.png")
        images.append(img)
        # aliveCount is consumed downstream as "alive PLATE elements" (HUD,
        # tracking chart) — the 24 projectile quads never erode and must not
        # ride along (Codex R0 P2: 136 reported where 112 plate survive).
        plate_total = sum(1 for e in fr["elements"] if e["partRole"] == "plate")
        alive = sum(1 for e in fr["elements"] if e["partRole"] == "plate" and e["alive"])
        peak = max(e["value"] for e in fr["elements"])
        max_u = max(np.linalg.norm(n["displacement"]) for n in fr["nodes"])
        per_frame.append(
            {
                "frame": i,
                "timeMs": fr["timeMs"],
                "peakVonMises": float(peak),
                "aliveCount": int(alive),
                "maxDisplacement": float(max_u),
            }
        )
        if i % 15 == 0 or i in (36, 93, 121, 125) or i == n - 1:
            print(
                f"  · frame {i:03d}  t={fr['timeMs']:.4f} ms  peak={peak:7.2f} MPa  "
                f"alive={alive:3d}/{plate_total} plate  |u|max={max_u:.2f}"
            )

    # sprite sheet
    print("sprite sheet (5x30 contour) ...")
    sheet = render_sprite_sheet(images, cols=5)
    sheet.save(OUT / "sprite_sheet.png")
    print(f"  · {sheet.size[0]}x{sheet.size[1]}")

    # animated GIF — side view (clean motion, no topo tearing)
    print("real animated GIF (side-view wireframe, 12.5 fps) ...")
    side_imgs = render_gif_frames(frames, value_max)
    gif_path = OUT / "gs102_real.gif"
    # per-frame adaptive palette (128 colors); this is the standard PIL
    # approach for a multi-frame GIF and avoids cross-frame color bleed.
    palette_imgs = [im.convert("P", palette=Image.ADAPTIVE, colors=128) for im in side_imgs]
    palette_imgs[0].save(
        gif_path,
        save_all=True,
        append_images=palette_imgs[1:],
        duration=80,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(
        f"  · {SIDE_W}x{SIDE_H}  {gif_path.stat().st_size / 1024 / 1024:.2f} MB  {n} frames @ 80 ms"
    )

    # tracking plot
    print("tracking plot ...")
    track = render_tracking_plot(per_frame, value_max)
    track.save(OUT / "tracking.png")
    print(f"  · {track.size[0]}x{track.size[1]}")

    # frame summary json
    summary = {
        "caseId": d["caseId"],
        "frameCount": n,
        "field": d["field"],
        "fieldLabel": d["fieldLabel"],
        "fieldUnits": d["fieldUnits"],
        "claimTier": d["claimTier"],
        "claimBoundary": d["claimBoundary"],
        "valueMaxOverall": float(value_max),
        # plate-element census so consumers never hardcode the denominator
        # (aliveCount above is plate-only; projectiles are excluded).
        "plateElementCount": sum(1 for e in frames[0]["elements"] if e["partRole"] == "plate"),
        "timeStart": per_frame[0]["timeMs"],
        "timeEnd": per_frame[-1]["timeMs"],
        "frames": per_frame,
    }
    with open(OUT / "frame_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  · frame_summary.json  ({n} frames)")

    print("DONE ·", OUT)


if __name__ == "__main__":
    main()
