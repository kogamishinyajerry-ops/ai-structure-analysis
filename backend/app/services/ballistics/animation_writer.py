"""Render a Tier 1 candidate ballistic side-view animation as a GIF.

Tier 1 engineering candidate. Not signed validation. Not benchmark
agreement. The animation is *illustrative only* — its purpose is to
let a reviewer eyeball the projectile/plate kinematics that the
JSON spine summarizes numerically. The frames are NOT a CFD/FEA
field-data visualization; they are a side-view kinematic sketch
driven by the same V₀ / vR / plate-geometry the extractor consumes.

Pure PIL implementation (no matplotlib / pyvista / numpy required at
runtime — matplotlib's compiled bindings are broken in some envs of
this repo, and the visualization is simple enough that ImageDraw
primitives suffice).

Allowed wording (per ADR-023):
  * Tier 1 engineering candidate
  * not signed validation
  * not benchmark agreement
  * candidate residual velocity / perforation marker

Forbidden wording in any rendered text:
  * "validated against ..."
  * "benchmark agreement" (without preceding negation)
  * "signed validation" (without preceding negation)
  * "perforation completed"
  * "bullet-through-steel complete"
  * "validated physics"
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .metric_extraction import BallisticTimeSample

CLAIM_BOUNDARY = "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"


@dataclass(frozen=True)
class BallisticAnimationInput:
    """Structured input for ``write_ballistic_animation``.

    All distances in metres, velocities in m/s. ``samples`` must be
    non-empty; if only the start + end sample is supplied, the writer
    builds a piecewise-kinematic interpolation around the plate
    impact (pre-impact at the head sample's velocity, deceleration
    across the plate, post-impact at the tail sample's velocity).
    """

    case_id: str
    samples: Sequence[BallisticTimeSample]
    plate_back_face_x_m: float
    plate_thickness_m: float
    projectile_diameter_m: float = 0.020
    impact_axis: str = "x"


# Canvas geometry (pixels). Chosen so the 12 mm plate + 20 mm
# projectile diameter render at sensible scale across a 0.16 m x
# axis without crowding the velocity / time annotations.
_CANVAS_W = 1100
_CANVAS_H = 360
_MARGIN_X = 60
_AXIS_Y = 240  # vertical centerline of projectile/plate

_X_VIEW_MIN_M = -0.10
_X_VIEW_MAX_M = 0.15

_BG_COLOR = (250, 250, 252)
_PLATE_COLOR = (90, 110, 140)
_PLATE_PERFORATED_COLOR = (190, 120, 90)
_PROJECTILE_COLOR = (60, 60, 60)
_PROJECTILE_TRAIL_COLOR = (190, 190, 190)
_AXIS_COLOR = (200, 200, 200)
_TEXT_COLOR = (30, 30, 30)
_BANNER_COLOR = (215, 70, 70)

_DEFAULT_FRAMES = 30
_DEFAULT_FRAME_DURATION_MS = 60  # ~16.6 fps
_TRAIL_LENGTH = 6


def write_ballistic_animation(
    inp: BallisticAnimationInput,
    output_dir: Path,
    *,
    frames: int = _DEFAULT_FRAMES,
    frame_duration_ms: int = _DEFAULT_FRAME_DURATION_MS,
) -> Path:
    """Render the animation GIF + animation_manifest.json into ``output_dir``.

    Returns the path to ``animation_manifest.json``. Both files land
    in ``output_dir`` (caller is responsible for selecting
    ``project_state/graph_executor/<case>/ballistic/``).

    Tier 1 candidate; not signed validation; not benchmark agreement.
    """
    if not inp.samples:
        raise ValueError("BallisticAnimationInput.samples must not be empty")
    if frames < 2:
        raise ValueError("frames must be >= 2")
    if inp.plate_thickness_m <= 0:
        raise ValueError("plate_thickness_m must be > 0")

    output_dir.mkdir(parents=True, exist_ok=True)
    gif_path = output_dir / "candidate_animation.gif"
    manifest_path = output_dir / "animation_manifest.json"

    head, tail = inp.samples[0], inp.samples[-1]
    axis = _axis_idx(inp.impact_axis)
    v0 = head.velocity_m_per_s[axis]
    vr = tail.velocity_m_per_s[axis]
    plate_front = inp.plate_back_face_x_m - inp.plate_thickness_m
    plate_back = inp.plate_back_face_x_m
    proj_radius_m = inp.projectile_diameter_m / 2.0

    # Build a single physics-consistent timeline driven by V₀/vR + plate
    # geometry. Pre-impact and crossing durations are derived from
    # kinematics; post-impact is capped so the impact event occupies a
    # readable fraction of the GIF (otherwise post-flight at vR would
    # dominate frame budget).
    timeline = _build_timeline(
        v0=v0,
        vr=vr,
        x_start=head.position_m[axis],
        plate_front=plate_front,
        plate_back=plate_back,
    )
    t0 = head.t_s
    t_total_animation = timeline.t_total

    pil_frames: list[Image.Image] = []
    trail: list[float] = []  # x-positions in metres
    perforated_at_frame: int | None = None

    for f in range(frames):
        u = f / (frames - 1)
        t_internal = u * t_total_animation
        x_m, v_now = _position_and_velocity_at(t_internal, timeline)
        t_display = t0 + t_internal
        trail.append(x_m)
        if len(trail) > _TRAIL_LENGTH:
            trail = trail[-_TRAIL_LENGTH:]

        proj_back_edge = x_m - proj_radius_m
        plate_perforated = proj_back_edge >= plate_back
        if plate_perforated and perforated_at_frame is None:
            perforated_at_frame = f

        frame = _render_frame(
            t_s=t_display,
            x_m=x_m,
            v_now_m_per_s=v_now,
            v0=v0,
            vr=vr,
            plate_front_m=plate_front,
            plate_back_m=plate_back,
            proj_radius_m=proj_radius_m,
            trail_xs_m=trail,
            perforated=plate_perforated,
            case_id=inp.case_id,
            frame_index=f,
            frame_count=frames,
        )
        pil_frames.append(frame)

    # Save animated GIF. PIL's loop=0 means infinite loop; duration
    # in ms per frame.
    pil_frames[0].save(
        gif_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True,
    )

    manifest = {
        "schema_version": "fm04a-ballistic-animation-manifest.v1",
        "claim_boundary": CLAIM_BOUNDARY,
        "claim_impact": (
            "Tier 1 candidate kinematic visualization; not benchmark agreement; "
            "not signed validation; illustrative only — does not visualize "
            "field data (stress / strain / velocity field)"
        ),
        "case_id": inp.case_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "renderer": "PIL ImageDraw side-view kinematic sketch",
        "frame_count": frames,
        "frame_duration_ms": frame_duration_ms,
        "frame_size_px": [_CANVAS_W, _CANVAS_H],
        "x_view_extent_m": [_X_VIEW_MIN_M, _X_VIEW_MAX_M],
        "geometry": {
            "plate_front_m": plate_front,
            "plate_back_m": plate_back,
            "plate_thickness_m": inp.plate_thickness_m,
            "projectile_diameter_m": inp.projectile_diameter_m,
            "impact_axis": inp.impact_axis,
        },
        "kinematics": {
            "v0_m_per_s": v0,
            "vr_m_per_s": vr,
            "t_total_animation_s": t_total_animation,
            "t_pre_impact_s": timeline.t_pre,
            "t_crossing_s": timeline.t_cross,
            "t_post_impact_s": timeline.t_post,
            "perforated_at_frame": perforated_at_frame,
        },
        "artifact": {
            "kind": "ballistic_animation_gif",
            "file_name": gif_path.name,
            "size_bytes": gif_path.stat().st_size,
            "sha256": _sha256(gif_path),
        },
        "limitations": [
            "side-view kinematic sketch only; not a field-data visualization",
            "projectile/plate motion is interpolated from V₀ / vR / plate "
            "geometry — not extracted from a real OpenRadioss .anim or .h3d",
            "not signed validation",
            "not benchmark agreement",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
# Kinematic model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Timeline:
    """Physics-internal timeline for the kinematic sketch.

    Three phases stitched together so the impact event occupies a
    readable fraction of frame budget. Post-impact is capped at
    ``2 * (t_pre + t_cross)`` so unbounded post-flight at vR doesn't
    dominate the GIF.
    """

    v0: float
    vr: float
    x_start: float
    plate_front: float
    plate_back: float
    t_pre: float
    t_cross: float
    t_post: float

    @property
    def t_total(self) -> float:
        return self.t_pre + self.t_cross + self.t_post


def _build_timeline(
    *,
    v0: float,
    vr: float,
    x_start: float,
    plate_front: float,
    plate_back: float,
) -> _Timeline:
    v0_eff = max(v0, 1.0)
    v_avg_cross = max((v0 + vr) / 2.0, 1.0)

    d_pre = max(plate_front - x_start, 0.0)
    d_cross = max(plate_back - plate_front, 1e-6)

    t_pre = d_pre / v0_eff
    t_cross = d_cross / v_avg_cross
    # Cap post-impact phase to keep the impact event visually prominent.
    t_post = min(2.0 * (t_pre + t_cross), max(t_cross * 8.0, 1e-5))
    return _Timeline(
        v0=v0,
        vr=vr,
        x_start=x_start,
        plate_front=plate_front,
        plate_back=plate_back,
        t_pre=t_pre,
        t_cross=t_cross,
        t_post=t_post,
    )


def _position_and_velocity_at(t: float, tl: _Timeline) -> tuple[float, float]:
    """Position + instantaneous velocity at internal time ``t`` along ``tl``."""
    if t < tl.t_pre:
        return tl.x_start + tl.v0 * t, tl.v0
    t_in_cross = t - tl.t_pre
    if t_in_cross < tl.t_cross:
        # Linear deceleration: v(τ) = v0 + (vr - v0) * τ / t_cross
        frac = t_in_cross / tl.t_cross
        v_now = tl.v0 + (tl.vr - tl.v0) * frac
        # Mean velocity over [0, t_in_cross] under linear v
        v_mean = tl.v0 + (tl.vr - tl.v0) * frac / 2.0
        return tl.plate_front + v_mean * t_in_cross, v_now
    t_in_post = t - tl.t_pre - tl.t_cross
    return tl.plate_back + tl.vr * t_in_post, tl.vr


def _axis_idx(axis: str) -> int:
    if axis not in {"x", "y", "z"}:
        raise ValueError(f"impact_axis must be x/y/z, got {axis!r}")
    return {"x": 0, "y": 1, "z": 2}[axis]


# ---------------------------------------------------------------------------
# Frame rendering (PIL only)
# ---------------------------------------------------------------------------


def _render_frame(
    *,
    t_s: float,
    x_m: float,
    v_now_m_per_s: float,
    v0: float,
    vr: float,
    plate_front_m: float,
    plate_back_m: float,
    proj_radius_m: float,
    trail_xs_m: list[float],
    perforated: bool,
    case_id: str,
    frame_index: int,
    frame_count: int,
) -> Image.Image:
    img = Image.new("RGB", (_CANVAS_W, _CANVAS_H), _BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _load_font(13)
    big_font = _load_font(16)
    banner_font = _load_font(11)

    # Centerline + tick marks
    draw.line(
        [(_MARGIN_X, _AXIS_Y), (_CANVAS_W - _MARGIN_X, _AXIS_Y)],
        fill=_AXIS_COLOR,
        width=1,
    )
    for tick_m in (-0.08, -0.04, 0.0, 0.04, 0.08, 0.12):
        tx = _x_to_px(tick_m)
        draw.line([(tx, _AXIS_Y - 4), (tx, _AXIS_Y + 4)], fill=_AXIS_COLOR, width=1)
        draw.text(
            (tx - 14, _AXIS_Y + 8),
            f"{tick_m * 1000:.0f} mm",
            fill=(140, 140, 140),
            font=font,
        )

    # Plate
    plate_color = _PLATE_PERFORATED_COLOR if perforated else _PLATE_COLOR
    px_front = _x_to_px(plate_front_m)
    px_back = _x_to_px(plate_back_m)
    plate_top = _AXIS_Y - 60
    plate_bot = _AXIS_Y + 60
    draw.rectangle(
        [(px_front, plate_top), (px_back, plate_bot)],
        fill=plate_color,
        outline=(40, 50, 70),
    )
    draw.text(
        (px_front, plate_top - 18),
        "Weldox 460E plate (12 mm)",
        fill=_TEXT_COLOR,
        font=font,
    )

    # Projectile trail (faded)
    proj_radius_px = max(int(proj_radius_m * _x_scale_px_per_m()), 6)
    for i, tx_m in enumerate(trail_xs_m[:-1]):
        tx_px = _x_to_px(tx_m)
        alpha_color = _PROJECTILE_TRAIL_COLOR
        draw.ellipse(
            [
                (tx_px - proj_radius_px, _AXIS_Y - proj_radius_px),
                (tx_px + proj_radius_px, _AXIS_Y + proj_radius_px),
            ],
            outline=alpha_color,
            width=1,
        )
        _ = i  # kept for future per-frame fade weighting

    # Projectile (current)
    cx_px = _x_to_px(x_m)
    draw.ellipse(
        [
            (cx_px - proj_radius_px, _AXIS_Y - proj_radius_px),
            (cx_px + proj_radius_px, _AXIS_Y + proj_radius_px),
        ],
        fill=_PROJECTILE_COLOR,
        outline=(0, 0, 0),
    )
    # Velocity arrow ahead of projectile
    arrow_len = max(int(v_now_m_per_s / 8.0), 12)
    ax_start = cx_px + proj_radius_px + 4
    ax_end = ax_start + arrow_len
    draw.line(
        [(ax_start, _AXIS_Y), (ax_end, _AXIS_Y)],
        fill=(40, 100, 180),
        width=2,
    )
    draw.polygon(
        [
            (ax_end, _AXIS_Y),
            (ax_end - 6, _AXIS_Y - 4),
            (ax_end - 6, _AXIS_Y + 4),
        ],
        fill=(40, 100, 180),
    )

    # Top-left HUD
    hud_lines = [
        f"GS-102-candidate  |  case: {case_id}",
        f"frame {frame_index + 1} / {frame_count}",
        f"t = {t_s * 1e6:.1f} us",
        f"x = {x_m * 1e3:.2f} mm   v = {v_now_m_per_s:.1f} m/s",
        f"V0 = {v0:.0f} m/s   vR (candidate) = {vr:.0f} m/s",
        ("perforation marker: perforated_candidate" if perforated else "perforation marker: still"),
    ]
    for i, line in enumerate(hud_lines):
        draw.text((_MARGIN_X, 20 + i * 18), line, fill=_TEXT_COLOR, font=big_font)

    # Bottom Tier 1 banner
    banner = (
        "Tier 1 engineering candidate  |  not signed validation  |  "
        "not benchmark agreement  |  side-view kinematic sketch — illustrative only"
    )
    draw.text((_MARGIN_X, _CANVAS_H - 24), banner, fill=_BANNER_COLOR, font=banner_font)

    return img


def _load_font(size: int) -> ImageFont.ImageFont:
    """Best-effort font loader.

    PIL ships with a small default bitmap font that ignores ``size``.
    On macOS we try a system TTF first so HUD/banner text is readable.
    Falling back to the default is harmless (just smaller text).
    """
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


def _x_to_px(x_m: float) -> int:
    span_m = _X_VIEW_MAX_M - _X_VIEW_MIN_M
    span_px = _CANVAS_W - 2 * _MARGIN_X
    px = int(_MARGIN_X + (x_m - _X_VIEW_MIN_M) / span_m * span_px)
    return max(0, min(_CANVAS_W - 1, px))


def _x_scale_px_per_m() -> float:
    span_m = _X_VIEW_MAX_M - _X_VIEW_MIN_M
    span_px = _CANVAS_W - 2 * _MARGIN_X
    return span_px / span_m


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "BallisticAnimationInput",
    "write_ballistic_animation",
    "CLAIM_BOUNDARY",
]
