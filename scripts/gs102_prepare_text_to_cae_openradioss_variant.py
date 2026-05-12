#!/usr/bin/env python3
"""Prepare a Text-to-CAE-style GS-102 OpenRadioss candidate source.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
This script adapts the public Text-to-CAE bullet-plate parameter shape into a
repo-local OpenRadioss source deck under project_state/**. It intentionally
keeps the current GS-102 refined demo geometry unless a future mesh generator
implements the full 150 x 150 x 8 mm Text-to-CAE geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CASE_DIR = (
    REPO_ROOT_DEFAULT / "golden_samples" / "GS-102-refined-candidate" / "data"
)
DEFAULT_OUTPUT_CASE_DIR = (
    REPO_ROOT_DEFAULT
    / "project_state"
    / "diagnostic_sources"
    / "GS-102-text-to-cae-openradioss-v1"
    / "data"
)
CLAIM_BOUNDARY = "Tier 1 engineering candidate; not signed validation; not benchmark agreement"

TEXT_TO_CAE_DEFAULTS: dict[str, Any] = {
    "plate_length_mm": 150.0,
    "plate_width_mm": 150.0,
    "plate_thickness_mm": 8.0,
    "plate_material": "armor_steel_candidate",
    "bullet_diameter_mm": 7.62,
    "bullet_length_mm": 28.0,
    "bullet_nose_length_mm": 8.0,
    "bullet_mass_g": 9.6,
    "impact_velocity_mps": 830.0,
    "impact_time_s": 8.0e-5,
    "plate_seed_mm": 1.25,
    "bullet_seed_mm": 0.65,
    "rigid_projectile": True,
    "output_frames": 240,
    "friction_coefficient": 0.16,
}


@dataclass(frozen=True)
class TextToCaeVariantConfig:
    repo_root: Path
    source_case_dir: Path
    output_case_dir: Path
    parameters_json: Path | None


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
        raise ValueError(f"variant output must live under project_state/: {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounded_float(payload: Mapping[str, Any], name: str, lower: float, upper: float) -> float:
    try:
        value = float(payload.get(name, TEXT_TO_CAE_DEFAULTS[name]))
    except Exception:
        value = float(TEXT_TO_CAE_DEFAULTS[name])
    return min(max(value, lower), upper)


def _bounded_int(payload: Mapping[str, Any], name: str, lower: int, upper: int) -> int:
    return int(round(_bounded_float(payload, name, float(lower), float(upper))))


def load_text_to_cae_parameters(parameters_json: Path | None) -> dict[str, Any]:
    payload = dict(TEXT_TO_CAE_DEFAULTS)
    if parameters_json is not None and parameters_json.exists():
        loaded = json.loads(parameters_json.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"parameters JSON must be an object: {parameters_json}")
        payload.update(loaded)

    bullet_diameter = _bounded_float(payload, "bullet_diameter_mm", 4.0, 20.0)
    bullet_length = _bounded_float(
        payload,
        "bullet_length_mm",
        bullet_diameter * 2.0,
        bullet_diameter * 8.0,
    )
    bullet_nose = _bounded_float(
        payload,
        "bullet_nose_length_mm",
        bullet_diameter * 0.4,
        bullet_length * 0.55,
    )

    return {
        "plate_length_mm": _bounded_float(payload, "plate_length_mm", 80.0, 350.0),
        "plate_width_mm": _bounded_float(payload, "plate_width_mm", 80.0, 350.0),
        "plate_thickness_mm": _bounded_float(payload, "plate_thickness_mm", 3.0, 30.0),
        "plate_material": str(payload.get("plate_material", "armor_steel_candidate")),
        "bullet_diameter_mm": bullet_diameter,
        "bullet_length_mm": bullet_length,
        "bullet_nose_length_mm": bullet_nose,
        "bullet_mass_g": _bounded_float(payload, "bullet_mass_g", 1.0, 80.0),
        "impact_velocity_mps": _bounded_float(payload, "impact_velocity_mps", 50.0, 1800.0),
        "impact_time_s": _bounded_float(payload, "impact_time_s", 1.0e-5, 5.0e-4),
        "plate_seed_mm": _bounded_float(payload, "plate_seed_mm", 0.35, 4.0),
        "bullet_seed_mm": _bounded_float(payload, "bullet_seed_mm", 0.2, 2.0),
        "rigid_projectile": bool(payload.get("rigid_projectile", True)),
        "output_frames": _bounded_int(payload, "output_frames", 40, 600),
        "friction_coefficient": _bounded_float(payload, "friction_coefficient", 0.0, 0.6),
    }


def patch_starter_for_text_to_cae(deck_text: str, parameters: Mapping[str, Any]) -> str:
    patched = deck_text.replace(
        "# GS-102-refined-candidate / FM-04a Tier 1 ballistic candidate (REFINED mesh)",
        "# GS-102-text-to-cae-openradioss-v1 / Tier 1 Text-to-CAE intent adapter",
    )
    patched = patched.replace(
        "#   * Refined mesh demonstrates JC damage element-deletion kinematics in the\n"
        "#     impact zone. Still NOT validated against Borvik 2002; NOT benchmark-quality.",
        "#   * This adapter maps Text-to-CAE-style velocity/time/frame intent onto\n"
        "#     the current GS-102 refined demo mesh. It is NOT full-size geometry,\n"
        "#     NOT validated, and NOT benchmark-quality.",
    )
    patched = patched.replace(
        "#   * Materials, JC params, BCS clamp, contact, INIVEL all carried over from\n"
        "#     GS-102-candidate verbatim.",
        "#   * Current implementation maps velocity, run time, and frame cadence;\n"
        "#     plate/projectile dimensions are recorded in the manifest until a\n"
        "#     full geometry/mesh generator is implemented.",
    )
    patched = patched.replace(
        "GS-102-refined-candidate Tier 1 perforation demo (Borvik 2002 params, NOT validated)",
        "GS-102 Text-to-CAE OpenRadioss Tier 1 candidate (NOT validated)",
    )
    patched = patched.replace(
        "gs102_refined_candidate",
        "gs102_text_to_cae_openradioss_v1",
        1,
    )

    velocity = float(parameters["impact_velocity_mps"])
    velocity_line = f"{velocity:20.12g}{0:20.12g}{0:20.12g}{100:10d}{0:10d}"
    pattern = re.compile(
        r"^(?P<prefix>\s*)[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?"
        r"\s+0\s+0\s+100\s+0\s*$",
        re.MULTILINE,
    )
    patched, count = pattern.subn(velocity_line, patched, count=1)
    if count != 1:
        raise ValueError("could not find /INIVEL projectile velocity line to patch")
    return patched


def patch_engine_for_text_to_cae(engine_text: str, parameters: Mapping[str, Any]) -> str:
    run_time_ms = float(parameters["impact_time_s"]) * 1000.0
    output_frames = max(1, int(parameters["output_frames"]))
    frame_dt_ms = run_time_ms / float(output_frames)

    patched = engine_text.replace(
        "# GS-102-refined-candidate / FM-04a Tier 1 perforation demo engine deck",
        "# GS-102-text-to-cae-openradioss-v1 / Tier 1 Text-to-CAE intent adapter engine deck",
    ).replace(
        "/RUN/gs102_refined_candidate/1/",
        "/RUN/gs102_text_to_cae_openradioss_v1/1/",
    )

    patched, run_count = re.subn(
        r"(/RUN/[^\n]+\n)\s*[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?",
        rf"\g<1>  {run_time_ms:.12g}",
        patched,
        count=1,
    )
    if run_count != 1:
        raise ValueError("could not patch OpenRadioss /RUN end time")

    patched, anim_count = re.subn(
        r"(/ANIM/DT\n)\s*[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?\s+[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?",
        rf"\g<1>0.0  {frame_dt_ms:.12g}",
        patched,
        count=1,
    )
    if anim_count != 1:
        raise ValueError("could not patch OpenRadioss /ANIM/DT interval")

    patched = re.sub(
        r"# Frame cadence:.*?(?=/ANIM/DT)",
        (
            "# Frame cadence mapped from Text-to-CAE-style parameters:\n"
            f"#   impact_time_s={float(parameters['impact_time_s']):.12g}, "
            f"output_frames={output_frames}, frame_dt_ms={frame_dt_ms:.12g}.\n"
            "#   Geometry still uses the current GS-102 refined demo mesh until\n"
            "#   a full Text-to-CAE geometry/mesh generator is implemented.\n"
        ),
        patched,
        count=1,
        flags=re.DOTALL,
    )
    return patched


def prepare_text_to_cae_openradioss_variant(config: TextToCaeVariantConfig) -> dict[str, Any]:
    _assert_safe_output_path(config.output_case_dir, config.repo_root)
    parameters = load_text_to_cae_parameters(config.parameters_json)

    source_starter = config.source_case_dir / "model_00_0000.rad"
    source_engine = config.source_case_dir / "model_00_0001.rad"
    if not source_starter.exists() or not source_engine.exists():
        raise FileNotFoundError(
            f"expected starter and engine decks under {config.source_case_dir}"
        )

    config.output_case_dir.mkdir(parents=True, exist_ok=True)
    output_starter = config.output_case_dir / "model_00_0000.rad"
    output_engine = config.output_case_dir / "model_00_0001.rad"
    output_starter.write_text(
        patch_starter_for_text_to_cae(
            source_starter.read_text(encoding="utf-8"),
            parameters,
        ),
        encoding="utf-8",
    )
    output_engine.write_text(
        patch_engine_for_text_to_cae(
            source_engine.read_text(encoding="utf-8"),
            parameters,
        ),
        encoding="utf-8",
    )

    # Preserve any sibling includes in future deck variants without assuming
    # only the two base files exist.
    for source_path in config.source_case_dir.iterdir():
        if source_path.name in {"model_00_0000.rad", "model_00_0001.rad"}:
            continue
        if source_path.is_file():
            shutil.copyfile(source_path, config.output_case_dir / source_path.name)

    manifest = {
        "claim_boundary": CLAIM_BOUNDARY,
        "recipe_id": "openradioss_bullet_plate_candidate.v1",
        "variant": "GS-102-text-to-cae-openradioss-v1",
        "source_inspiration": "Cai-aa/text-to-cae models/text-to-cae-bullet-plate",
        "parameters": parameters,
        "mapped_parameters": [
            "impact_velocity_mps",
            "impact_time_s",
            "output_frames",
        ],
        "intent_only_parameters": [
            "plate_length_mm",
            "plate_width_mm",
            "plate_thickness_mm",
            "plate_material",
            "bullet_diameter_mm",
            "bullet_length_mm",
            "bullet_nose_length_mm",
            "bullet_mass_g",
            "plate_seed_mm",
            "bullet_seed_mm",
            "rigid_projectile",
            "friction_coefficient",
        ],
        "geometry_adapter_status": (
            "fallback_gs102_refined_demo_mesh; full Text-to-CAE dimensions are "
            "recorded but not yet remeshed"
        ),
        "open_source_stack": {
            "geometry_mesh": "current structured GS-102 deck generator; Gmsh planned",
            "solver": "OpenRadioss",
            "result_reader": "Vortex-Radioss",
            "viewer_export": "repo-native animation now; result_mesh.json planned",
        },
        "source_case_dir": str(config.source_case_dir.relative_to(config.repo_root)),
        "output_case_dir": str(config.output_case_dir.relative_to(config.repo_root)),
        "source_starter_sha256": _sha256(source_starter),
        "output_starter_sha256": _sha256(output_starter),
        "source_engine_sha256": _sha256(source_engine),
        "output_engine_sha256": _sha256(output_engine),
    }
    manifest_path = config.output_case_dir.parent / "text_to_cae_openradioss_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path.relative_to(config.repo_root))
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--source-case-dir", default=str(DEFAULT_SOURCE_CASE_DIR))
    parser.add_argument("--output-case-dir", default=str(DEFAULT_OUTPUT_CASE_DIR))
    parser.add_argument(
        "--parameters-json",
        default="",
        help="Text-to-CAE-style cae_parameters.json; defaults are used when omitted",
    )
    return parser.parse_args(argv)


def _config_from_args(args: argparse.Namespace) -> TextToCaeVariantConfig:
    repo_root = Path(args.repo_root).resolve()
    parameters_json = Path(args.parameters_json).resolve() if args.parameters_json else None
    return TextToCaeVariantConfig(
        repo_root=repo_root,
        source_case_dir=Path(args.source_case_dir).resolve(),
        output_case_dir=Path(args.output_case_dir).resolve(),
        parameters_json=parameters_json,
    )


def main(argv: list[str] | None = None) -> int:
    config = _config_from_args(_parse_args(argv))
    manifest = prepare_text_to_cae_openradioss_variant(config)
    print("GS-102 Text-to-CAE OpenRadioss source prepared")
    print(CLAIM_BOUNDARY)
    print(manifest["manifest_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
