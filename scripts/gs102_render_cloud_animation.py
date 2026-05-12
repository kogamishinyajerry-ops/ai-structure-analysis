#!/usr/bin/env python3
"""Render a high-resolution GS-102 stress/pressure-proxy cloud animation.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
The pressure cloud is a visual proxy derived from OpenRadioss solid stress:
abs((sxx + syy + szz) / 3). It is not a calibrated pressure measurement.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import shutil
import sys
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
CLAIM_BOUNDARY = "Tier 1 engineering candidate; not signed validation; not benchmark agreement"
ANIM_RE = re.compile(r"A\d{3,4}(?:\.gz)?$")


@dataclass(frozen=True)
class CloudRenderConfig:
    repo_root: Path
    case_id: str
    run_data_dir: Path
    output_dir: Path
    width: int
    height: int
    frame_duration_ms: int
    field: str


@dataclass(frozen=True)
class FrameData:
    source: str
    timestep: float
    coords: np.ndarray
    node_indexes: np.ndarray
    element_ids: np.ndarray
    part_ids: np.ndarray
    alive: np.ndarray
    stress: np.ndarray | None
    plastic_strain: np.ndarray | None


def _ensure_backend_path(repo_root: Path) -> None:
    backend = repo_root / "backend"
    for candidate in (str(backend), str(repo_root)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def _relative_parts(path: Path, repo_root: Path) -> tuple[str, ...]:
    try:
        return path.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        return path.resolve().parts


def _assert_safe_output_path(path: Path, repo_root: Path) -> None:
    parts = _relative_parts(path, repo_root)
    if "golden_samples" in parts:
        raise ValueError(f"refuses to write inside golden_samples/**: {path}")
    if "project_state" not in parts:
        raise ValueError(f"visualization output must live under project_state/: {path}")


def discover_animation_files(run_data_dir: Path) -> tuple[Path, ...]:
    files = [p for p in run_data_dir.iterdir() if p.is_file() and ANIM_RE.search(p.name)]
    return tuple(sorted(files, key=lambda p: p.name))


def _ungzip_if_needed(src: Path) -> Path:
    if src.suffix != ".gz":
        return src
    with tempfile.NamedTemporaryFile(suffix=".A001", delete=False) as tmp_file:
        tmp = Path(tmp_file.name)
    with gzip.open(src, "rb") as fin, tmp.open("wb") as fout:
        shutil.copyfileobj(fin, fout)
    return tmp


def _extract_frame(reader: Any, source: str) -> FrameData:
    arrays = reader.arrays
    coords = np.asarray(arrays["node_coordinates"], dtype=float)
    node_indexes = np.asarray(arrays["element_solid_node_indexes"], dtype=int)
    if node_indexes.ndim != 2:
        raise ValueError(f"{source} has invalid element_solid_node_indexes shape")

    element_count = node_indexes.shape[0]
    element_ids = np.asarray(
        arrays.get("element_solid_ids", np.arange(1, element_count + 1)),
        dtype=int,
    )
    part_ids = np.asarray(arrays.get("element_solid_part_ids", np.zeros(element_count)), dtype=int)
    alive = np.asarray(arrays.get("element_solid_is_alive", np.ones(element_count)), dtype=bool)
    stress = arrays.get("element_solid_stress")
    plastic_strain = arrays.get("element_solid_plastic_strain")
    timestep_raw = arrays.get("timesteps", 0.0)

    return FrameData(
        source=source,
        timestep=float(np.asarray(timestep_raw).reshape(-1)[0]) if np.size(timestep_raw) else 0.0,
        coords=coords,
        node_indexes=node_indexes,
        element_ids=element_ids,
        part_ids=part_ids,
        alive=alive,
        stress=np.asarray(stress, dtype=float) if stress is not None else None,
        plastic_strain=(
            np.asarray(plastic_strain, dtype=float) if plastic_strain is not None else None
        ),
    )


def read_frames(repo_root: Path, anim_files: Sequence[Path]) -> list[FrameData]:
    _ensure_backend_path(repo_root)
    from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

    frames: list[FrameData] = []
    for src in anim_files:
        path = _ungzip_if_needed(src)
        try:
            frames.append(_extract_frame(RadiossReader(str(path)), str(src)))
        finally:
            if path != src:
                path.unlink(missing_ok=True)
    return frames


def element_field_values(frame: FrameData, field: str) -> np.ndarray:
    if field in {"pressure_proxy", "pressure_delta"}:
        if frame.stress is None or frame.stress.shape[1] < 3:
            return np.zeros(len(frame.node_indexes), dtype=float)
        hydro = (frame.stress[:, 0] + frame.stress[:, 1] + frame.stress[:, 2]) / 3.0
        pressure = np.abs(hydro)
        if field == "pressure_delta":
            plate_alive = np.logical_and(_plate_mask(frame), frame.alive)
            baseline = float(np.median(pressure[plate_alive])) if np.any(plate_alive) else 0.0
            return np.abs(pressure - baseline)
        return pressure
    if field == "von_mises":
        if frame.stress is None or frame.stress.shape[1] < 6:
            return np.zeros(len(frame.node_indexes), dtype=float)
        sxx, syy, szz, sxy, syz, sxz = [frame.stress[:, i] for i in range(6)]
        vm = np.sqrt(
            0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
            + 3.0 * (sxy**2 + syz**2 + sxz**2)
        )
        return np.asarray(vm, dtype=float)
    if field == "plastic_strain":
        if frame.plastic_strain is None:
            return np.zeros(len(frame.node_indexes), dtype=float)
        return np.asarray(frame.plastic_strain, dtype=float).reshape(-1)
    raise ValueError(f"unsupported field: {field}")


def global_field_limits(frames: Sequence[FrameData], field: str) -> tuple[float, float]:
    values: list[float] = []
    for frame in frames:
        plate = _plate_mask(frame)
        alive = np.logical_and(plate, frame.alive)
        frame_values = element_field_values(frame, field)
        for value in frame_values[alive]:
            if math.isfinite(float(value)) and float(value) > 0.0:
                values.append(float(value))
    if not values:
        return (0.0, 1.0)
    low = float(np.percentile(values, 2))
    high = float(np.percentile(values, 98))
    if high <= low:
        high = max(values)
        low = 0.0
    if high <= low:
        high = low + 1.0
    return low, high


def _projectile_mask(frame: FrameData) -> np.ndarray:
    if np.any(frame.part_ids == 1):
        return frame.part_ids == 1
    return np.arange(len(frame.node_indexes)) < 8


def _plate_mask(frame: FrameData) -> np.ndarray:
    if np.any(frame.part_ids == 2):
        return frame.part_ids == 2
    return ~_projectile_mask(frame)


def _field_label(field: str) -> str:
    if field == "pressure_proxy":
        return "pressure proxy: |mean normal stress|"
    if field == "pressure_delta":
        return "pressure proxy delta from frame median"
    if field == "von_mises":
        return "von Mises stress"
    if field == "plastic_strain":
        return "plastic strain"
    return field


def _cloud_color(value: float) -> tuple[int, int, int]:
    stops = [
        (0.00, (18, 25, 74)),
        (0.15, (35, 104, 189)),
        (0.35, (33, 180, 202)),
        (0.52, (85, 205, 95)),
        (0.70, (244, 211, 67)),
        (0.86, (239, 100, 45)),
        (1.00, (178, 24, 43)),
    ]
    v = max(0.0, min(1.0, float(value)))
    for idx in range(1, len(stops)):
        left_v, left_c = stops[idx - 1]
        right_v, right_c = stops[idx]
        if v <= right_v:
            span = right_v - left_v
            t = 0.0 if span <= 0 else (v - left_v) / span
            return tuple(
                int(round(left_c[channel] + (right_c[channel] - left_c[channel]) * t))
                for channel in range(3)
            )
    return stops[-1][1]


def _normalize(value: float, limits: tuple[float, float]) -> float:
    low, high = limits
    shifted = max(0.0, float(value) - low)
    span = max(1e-12, high - low)
    return math.log1p(9.0 * shifted / span) / math.log1p(9.0)


def _bbox_xy(frames: Sequence[FrameData]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for frame in frames:
        xs.extend(float(x) for x in frame.coords[:, 0])
        ys.extend(float(y) for y in frame.coords[:, 1])
    if not xs:
        return (0.0, 1.0, 0.0, 1.0)
    return (min(xs), max(xs), min(ys), max(ys))


def _make_projector(
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
) -> tuple[Any, float]:
    x0, x1, y0, y1 = bbox
    dx = max(1e-9, x1 - x0)
    dy = max(1e-9, y1 - y0)
    pad_left = 120
    pad_right = 130
    pad_top = 115
    pad_bottom = 145
    scale = min((width - pad_left - pad_right) / dx, (height - pad_top - pad_bottom) / dy)
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    canvas_cx = (pad_left + width - pad_right) / 2.0
    canvas_cy = (pad_top + height - pad_bottom) / 2.0

    def project(point: Sequence[float]) -> tuple[int, int]:
        x, y = float(point[0]), float(point[1])
        px = canvas_cx + (x - cx) * scale
        py = canvas_cy - (y - cy) * scale
        return (int(round(px)), int(round(py)))

    return project, scale


def _convex_hull(points: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    unique = sorted(set(points))
    if len(unique) <= 2:
        return unique

    def cross(o: tuple[int, int], a: tuple[int, int], b: tuple[int, int]) -> int:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[int, int]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[int, int]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def _element_polygon(frame: FrameData, elem_index: int, project: Any) -> list[tuple[int, int]]:
    points = [project(frame.coords[node_index]) for node_index in frame.node_indexes[elem_index]]
    return _convex_hull(points)


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    bbox: tuple[float, float, float, float],
    project: Any,
    width: int,
    height: int,
) -> None:
    x0, x1, y0, y1 = bbox
    for x in np.linspace(x0, x1, 6):
        p0 = project((x, y0, 0.0))
        p1 = project((x, y1, 0.0))
        draw.line([p0, p1], fill=(224, 226, 232), width=1)
    for y in np.linspace(y0, y1, 5):
        p0 = project((x0, y, 0.0))
        p1 = project((x1, y, 0.0))
        draw.line([p0, p1], fill=(224, 226, 232), width=1)
    draw.rectangle((18, 18, width - 18, height - 18), outline=(210, 214, 222), width=2)


def _draw_colorbar(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    width: int,
    height: int,
    limits: tuple[float, float],
    label: str,
) -> None:
    x0 = 130
    x1 = width - 260
    y0 = height - 82
    y1 = height - 56
    for x in range(x0, x1):
        t = (x - x0) / max(1, x1 - x0 - 1)
        draw.line([(x, y0), (x, y1)], fill=_cloud_color(t))
    draw.rectangle((x0, y0, x1, y1), outline=(70, 70, 80), width=1)
    draw.text((x0, y1 + 8), f"{limits[0]:.3g}", fill=(35, 35, 42), font=font)
    draw.text((x1 - 60, y1 + 8), f"{limits[1]:.3g}", fill=(35, 35, 42), font=font)
    draw.text((x0, y0 - 26), label, fill=(35, 35, 42), font=font)


def _render_one_frame(
    frame: FrameData,
    *,
    frame_index: int,
    frame_count: int,
    case_id: str,
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    field: str,
    limits: tuple[float, float],
) -> Image.Image:
    image = Image.new("RGB", (width, height), (247, 248, 251))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    project, _ = _make_projector(bbox, width, height)
    values = element_field_values(frame, field)
    projectile = _projectile_mask(frame)
    plate = _plate_mask(frame)

    _draw_grid(draw, bbox, project, width, height)

    for elem_index in np.where(plate)[0]:
        polygon = _element_polygon(frame, int(elem_index), project)
        if len(polygon) < 3:
            continue
        if bool(frame.alive[elem_index]):
            color = _cloud_color(_normalize(float(values[elem_index]), limits))
            draw.polygon(polygon, fill=color, outline=(42, 43, 52))
        else:
            draw.polygon(polygon, fill=(85, 76, 83), outline=(185, 70, 72))
            draw.line([polygon[0], polygon[len(polygon) // 2]], fill=(235, 130, 110), width=2)

    # Draw projectile last, independent of the pressure field, so the complete
    # bullet remains visible when it passes through the plate projection.
    for elem_index in np.where(projectile)[0]:
        polygon = _element_polygon(frame, int(elem_index), project)
        if len(polygon) < 3:
            continue
        draw.polygon(polygon, fill=(28, 29, 34), outline=(242, 242, 236))
        draw.line(polygon + [polygon[0]], fill=(255, 211, 99), width=2)

    draw.text((48, 36), case_id, fill=(22, 24, 30), font=title_font)
    draw.text(
        (48, 62),
        f"frame {frame_index + 1}/{frame_count}  t={frame.timestep:.6g} ms",
        fill=(36, 38, 44),
        font=font,
    )
    alive_plate = int(np.sum(np.logical_and(plate, frame.alive)))
    total_plate = int(np.sum(plate))
    draw.text(
        (48, 86),
        f"resin visual candidate, plate alive elements {alive_plate}/{total_plate}",
        fill=(36, 38, 44),
        font=font,
    )
    draw.text(
        (width - 500, 36),
        "Tier 1 only: not signed validation, not benchmark agreement",
        fill=(170, 45, 50),
        font=font,
    )
    draw.text(
        (width - 500, 62),
        "cloud = stress-derived visual proxy, not calibrated pressure",
        fill=(170, 45, 50),
        font=font,
    )
    _draw_colorbar(draw, font, width, height, limits, _field_label(field))
    return image


def render_cloud_animation(config: CloudRenderConfig) -> dict:
    _assert_safe_output_path(config.output_dir, config.repo_root)
    anim_files = discover_animation_files(config.run_data_dir)
    if not anim_files:
        raise FileNotFoundError(f"no OpenRadioss A-files found under {config.run_data_dir}")
    frames = read_frames(config.repo_root, anim_files)
    if not frames:
        raise RuntimeError("no frames were readable")

    bbox = _bbox_xy(frames)
    limits = global_field_limits(frames, config.field)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    gif_path = config.output_dir / f"{config.case_id}_{config.field}_cloud_hires.gif"
    poster_path = config.output_dir / f"{config.case_id}_{config.field}_cloud_midframe.png"
    manifest_path = config.output_dir / f"{config.case_id}_{config.field}_cloud_manifest.json"
    pil_frames = [
        _render_one_frame(
            frame,
            frame_index=idx,
            frame_count=len(frames),
            case_id=config.case_id,
            bbox=bbox,
            width=config.width,
            height=config.height,
            field=config.field,
            limits=limits,
        )
        for idx, frame in enumerate(frames)
    ]
    mid = len(pil_frames) // 2
    pil_frames[mid].save(poster_path)
    pil_frames[0].save(
        gif_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=config.frame_duration_ms,
        loop=0,
        optimize=True,
    )

    manifest = {
        "schema_version": "gs102-cloud-animation-manifest.v1",
        "claim_boundary": CLAIM_BOUNDARY,
        "case_id": config.case_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "run_data_dir": str(config.run_data_dir.relative_to(config.repo_root)),
        "output_dir": str(config.output_dir.relative_to(config.repo_root)),
        "field": config.field,
        "field_label": _field_label(config.field),
        "field_source": (
            "element_solid_stress"
            if config.field != "plastic_strain"
            else "element_solid_plastic_strain"
        ),
        "pressure_proxy_definition": "abs((sxx + syy + szz) / 3)",
        "pressure_delta_definition": (
            "abs(pressure_proxy - frame_median_alive_plate_pressure_proxy)"
        ),
        "frame_count": len(frames),
        "frame_duration_ms": config.frame_duration_ms,
        "frame_size_px": [config.width, config.height],
        "normalization": {
            "method": "log1p robust 2nd-to-98th percentile over alive plate elements",
            "low": limits[0],
            "high": limits[1],
        },
        "rendering_notes": [
            "XY side projection of real OpenRadioss A-file frames",
            "projectile part is drawn last so the full bullet remains visible",
            "plate material is the project_state resin visual candidate source",
        ],
        "limitations": [
            "pressure cloud is an uncalibrated stress-derived proxy",
            "2D XY projection hides out-of-plane structure",
            "not signed validation",
            "not benchmark agreement",
        ],
        "artifacts": {
            "gif": {
                "path": str(gif_path.relative_to(config.repo_root)),
                "size_bytes": gif_path.stat().st_size,
                "sha256": _sha256(gif_path),
            },
            "poster": {
                "path": str(poster_path.relative_to(config.repo_root)),
                "size_bytes": poster_path.stat().st_size,
                "sha256": _sha256(poster_path),
            },
        },
        "per_frame": [
            {
                "source": frame.source,
                "timestep": frame.timestep,
                "plate_alive": int(np.sum(np.logical_and(_plate_mask(frame), frame.alive))),
                "plate_total": int(np.sum(_plate_mask(frame))),
                "projectile_alive": int(
                    np.sum(np.logical_and(_projectile_mask(frame), frame.alive))
                ),
                "projectile_total": int(np.sum(_projectile_mask(frame))),
            }
            for frame in frames
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "gif": gif_path,
        "poster": poster_path,
        "manifest": manifest_path,
        "frame_count": len(frames),
        "field_limits": limits,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--run-data-dir", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--frame-duration-ms", type=int, default=50)
    parser.add_argument(
        "--field",
        choices=("pressure_proxy", "pressure_delta", "von_mises", "plastic_strain"),
        default="pressure_delta",
    )
    return parser.parse_args(argv)


def _config_from_args(args: argparse.Namespace) -> CloudRenderConfig:
    repo_root = Path(args.repo_root).resolve()
    case_id = str(args.case_id)
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else repo_root / "project_state" / "visualizations" / case_id
    )
    return CloudRenderConfig(
        repo_root=repo_root,
        case_id=case_id,
        run_data_dir=Path(args.run_data_dir).resolve(),
        output_dir=output_dir,
        width=int(args.width),
        height=int(args.height),
        frame_duration_ms=int(args.frame_duration_ms),
        field=str(args.field),
    )


def main(argv: list[str] | None = None) -> int:
    config = _config_from_args(_parse_args(argv))
    artifacts = render_cloud_animation(config)
    print(f"Rendered {artifacts['frame_count']} frames")
    print(CLAIM_BOUNDARY)
    for name in ("gif", "poster", "manifest"):
        print(f"{name}: {artifacts[name].relative_to(config.repo_root)}")
    print(f"field_limits: {artifacts['field_limits'][0]:.6g}, {artifacts['field_limits'][1]:.6g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
