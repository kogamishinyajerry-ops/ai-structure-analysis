from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MESH_LEVEL_SETTINGS: dict[str, dict[str, float]] = {
    "coarse": {
        "size_divisor": 16.0,
        "global_min_factor": 0.60,
        "field_min_factor": 0.55,
        "distance_scale": 0.20,
    },
    "medium": {
        "size_divisor": 24.0,
        "global_min_factor": 0.45,
        "field_min_factor": 0.40,
        "distance_scale": 0.16,
    },
    "fine": {
        "size_divisor": 36.0,
        "global_min_factor": 0.32,
        "field_min_factor": 0.28,
        "distance_scale": 0.12,
    },
    "very_fine": {
        "size_divisor": 52.0,
        "global_min_factor": 0.22,
        "field_min_factor": 0.20,
        "distance_scale": 0.09,
    },
}
THIN_WALL_THRESHOLD_M = 5e-4

try:
    import gmsh  # type: ignore[import-not-found, import-untyped]

    GMSH_AVAILABLE = True
except ImportError:
    gmsh = None
    GMSH_AVAILABLE = False


def normalize_mesh_level(value: Any) -> str:
    """Normalize free-form mesh level values to a supported preset name."""
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        aliases = {
            "veryfine": "very_fine",
            "extra_fine": "very_fine",
            "ultra_fine": "very_fine",
            "x_fine": "very_fine",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized in MESH_LEVEL_SETTINGS:
            return normalized
    return "medium"


def load_geometry_metadata(geometry_path: Path) -> dict[str, Any]:
    """Load the geometry sidecar emitted by the Geometry Agent if present."""
    meta_path = geometry_path.with_name("geometry_meta.json")
    if not meta_path.exists():
        return {}

    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Geometry metadata at %s is not valid JSON; ignoring it.", meta_path)
        return {}


def build_field_config(params: dict[str, Any], geometry_meta: dict[str, Any]) -> dict[str, Any]:
    """Build an adaptive meshing configuration from plan + geometry metadata."""
    mesh_level = normalize_mesh_level(params.get("mesh_level"))
    level_settings = MESH_LEVEL_SETTINGS[mesh_level]
    bounding_box_mm = geometry_meta.get("bounding_box_mm") or []
    dims_m = [float(value) / 1000.0 for value in bounding_box_mm if float(value) > 0.0]

    requested_global_size = params.get("global_size")
    if requested_global_size is not None:
        characteristic_length_m = max(float(requested_global_size), 1e-6)
        global_max_size = characteristic_length_m
    else:
        characteristic_length_m = max(dims_m) if dims_m else 1.0
        global_max_size = max(characteristic_length_m / level_settings["size_divisor"], 1e-6)

    global_min_size = max(global_max_size * level_settings["global_min_factor"], 1e-6)
    field_min_size = max(global_max_size * level_settings["field_min_factor"], 1e-6)
    min_feature_size_m = geometry_meta.get("min_feature_size_m")
    thin_wall_threshold_m = float(params.get("thin_wall_threshold_m", THIN_WALL_THRESHOLD_M))
    thin_wall_detected = (
        isinstance(min_feature_size_m, (int, float))
        and float(min_feature_size_m) < thin_wall_threshold_m
    )

    thin_wall_size = None
    if thin_wall_detected:
        thin_wall_size = max(float(min_feature_size_m) / 3.0, 1e-6)
        global_min_size = min(global_min_size, thin_wall_size)
        field_min_size = min(field_min_size, thin_wall_size)

    distance_scale = float(params.get("field_distance_scale", level_settings["distance_scale"]))
    distance_min = max(field_min_size, characteristic_length_m * distance_scale * 0.25)
    distance_max = max(distance_min * 3.0, characteristic_length_m * distance_scale)

    return {
        "mesh_level": mesh_level,
        "characteristic_length_m": characteristic_length_m,
        "global_min_size": global_min_size,
        "global_max_size": global_max_size,
        "field_min_size": field_min_size,
        "field_max_size": global_max_size,
        "distance_min": distance_min,
        "distance_max": distance_max,
        "thin_wall_detected": thin_wall_detected,
        "thin_wall_threshold_m": thin_wall_threshold_m,
        "thin_wall_size": thin_wall_size,
        "min_feature_size_m": min_feature_size_m,
        "element_order": params.get("element_order", "quadratic"),
    }


def _write_mesh_metadata(
    output_dir: Path,
    field_config: dict[str, Any],
    geometry_meta: dict[str, Any],
    *,
    generation_mode: str,
    field_ids: dict[str, int | None] | None = None,
) -> Path:
    """Persist the adaptive meshing decision as a sidecar artifact."""
    meta_path = output_dir / "mesh_meta.json"
    payload = {
        "generation_mode": generation_mode,
        "field_config": field_config,
        "field_ids": field_ids or {},
        "geometry_summary": {
            "bounding_box_mm": geometry_meta.get("bounding_box_mm"),
            "min_feature_size_m": geometry_meta.get("min_feature_size_m"),
        },
    }
    meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return meta_path


def _import_geometry(geometry_path: Path) -> None:
    """Import STEP geometry into gmsh using OCC when available."""
    if gmsh is None:
        return

    if hasattr(gmsh.model, "occ") and hasattr(gmsh.model.occ, "importShapes"):
        gmsh.model.occ.importShapes(str(geometry_path))
        gmsh.model.occ.synchronize()
        return

    gmsh.merge(str(geometry_path))
    if hasattr(gmsh.model, "occ") and hasattr(gmsh.model.occ, "synchronize"):
        gmsh.model.occ.synchronize()


def _entity_tags(dim: int) -> list[int]:
    """Return gmsh entity tags for a given topological dimension."""
    if gmsh is None or not hasattr(gmsh.model, "getEntities"):
        return []

    return [tag for current_dim, tag in gmsh.model.getEntities(dim) if current_dim == dim]


def _apply_background_fields(field_config: dict[str, Any]) -> dict[str, int | None]:
    """Attach a Distance + Threshold field stack for adaptive meshing."""
    if gmsh is None:
        return {
            "distance": None,
            "threshold": None,
            "thin_wall_threshold": None,
            "background": None,
        }

    surface_tags = _entity_tags(2)
    volume_tags = _entity_tags(3)
    source_tags = surface_tags or volume_tags
    source_key = "FacesList" if surface_tags else "VolumesList"

    field_api = gmsh.model.mesh.field
    distance_id = field_api.add("Distance")
    if source_tags:
        field_api.setNumbers(distance_id, source_key, source_tags)

    threshold_id = field_api.add("Threshold")
    field_api.setNumber(threshold_id, "IField", distance_id)
    field_api.setNumber(threshold_id, "LcMin", field_config["field_min_size"])
    field_api.setNumber(threshold_id, "LcMax", field_config["field_max_size"])
    field_api.setNumber(threshold_id, "DistMin", field_config["distance_min"])
    field_api.setNumber(threshold_id, "DistMax", field_config["distance_max"])

    background_fields = [threshold_id]
    thin_wall_threshold_id: int | None = None
    if field_config["thin_wall_detected"] and field_config["thin_wall_size"] is not None:
        thin_wall_threshold_id = field_api.add("Threshold")
        field_api.setNumber(thin_wall_threshold_id, "IField", distance_id)
        field_api.setNumber(thin_wall_threshold_id, "LcMin", field_config["thin_wall_size"])
        field_api.setNumber(thin_wall_threshold_id, "LcMax", field_config["field_min_size"])
        field_api.setNumber(thin_wall_threshold_id, "DistMin", field_config["distance_min"] / 2.0)
        field_api.setNumber(thin_wall_threshold_id, "DistMax", field_config["distance_min"])
        background_fields.append(thin_wall_threshold_id)

    if len(background_fields) == 1:
        background_id = background_fields[0]
    else:
        background_id = field_api.add("Min")
        field_api.setNumbers(background_id, "FieldsList", background_fields)

    field_api.setAsBackgroundMesh(background_id)
    return {
        "distance": distance_id,
        "threshold": threshold_id,
        "thin_wall_threshold": thin_wall_threshold_id,
        "background": background_id,
    }


def generate_mesh(geometry_path: Path, params: dict[str, Any], output_dir: Path) -> Path:
    """Generate a finite-element mesh from a STEP geometry file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "model.inp"
    geometry_meta = load_geometry_metadata(geometry_path)
    field_config = build_field_config(params, geometry_meta)

    if not GMSH_AVAILABLE:
        logger.warning("Gmsh is not available natively. Returning a dummy mesh.")
        out_path.write_text(
            "*HEADING\n"
            "** Dummy fallback mesh\n"
            "*NODE\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 0.0, 1.0, 0.0\n"
            "4, 0.0, 0.0, 1.0\n"
            "*ELEMENT, TYPE=C3D4\n"
            "1, 1, 2, 3, 4\n",
            encoding="utf-8",
        )
        _write_mesh_metadata(output_dir, field_config, geometry_meta, generation_mode="fallback")
        return out_path

    element_order = 2 if field_config["element_order"] == "quadratic" else 1

    try:
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 0)
        _import_geometry(geometry_path)

        gmsh.option.setNumber("Mesh.MeshSizeMin", field_config["global_min_size"])
        gmsh.option.setNumber("Mesh.MeshSizeMax", field_config["global_max_size"])
        gmsh.option.setNumber("Mesh.ElementOrder", element_order)
        gmsh.option.setNumber("Mesh.Format", 39)
        field_ids = _apply_background_fields(field_config)

        dimension = 3 if _entity_tags(3) else 2
        gmsh.model.mesh.generate(dimension)
        if element_order == 2:
            gmsh.model.mesh.setOrder(2)

        gmsh.write(str(out_path))
        _write_mesh_metadata(
            output_dir,
            field_config,
            geometry_meta,
            generation_mode="gmsh",
            field_ids=field_ids,
        )
    except Exception as exc:
        logger.error("Gmsh meshing failed: %s", exc)
        raise
    finally:
        if GMSH_AVAILABLE:
            gmsh.finalize()

    return out_path
