#!/usr/bin/env python3
"""Prepare a GS-102 resin-plate visual candidate under project_state.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
The script reads a source GS-102 deck, keeps the projectile material untouched,
and writes a resin-like plate variant outside golden_samples/**.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CASE_DIR = (
    REPO_ROOT_DEFAULT / "golden_samples" / "GS-102-refined-candidate" / "data"
)
DEFAULT_OUTPUT_CASE_DIR = (
    REPO_ROOT_DEFAULT / "project_state" / "diagnostic_sources" / "GS-102-resin-plate-v1" / "data"
)
CLAIM_BOUNDARY = "Tier 1 engineering candidate; not signed validation; not benchmark agreement"


@dataclass(frozen=True)
class ResinVariantConfig:
    repo_root: Path
    source_case_dir: Path
    output_case_dir: Path


RESIN_MATERIAL_BLOCK = """/MAT/PLAS_JOHNS/2
generic_resin_plate_visual_candidate
#              RHO_I
              1.20E-6                   0
#                  E                  Nu     Iflag
                   3                  .35         0
# Generic resin-like visual candidate only. Values are uncalibrated and chosen
# to make a softer transparent/non-metallic plate response visible in Tier 1
# animation work, not to represent a signed material model.
#                  a                   b                   n           EPS_p_max            SIG_max0
                .075                .015                 .20                1E30                   0
#                  c           EPS_DOT_0       ICC   Fsmooth               F_cut               Chard
                   0                .001         0         0                   0                   0
#                  m              T_melt              rhoC_p                 T_r
                   0                   0                   0                 293
# Failure card intentionally omitted for this visual cloud candidate so resin
# plate elements keep carrying solver stress/plastic-strain output throughout
# the animation. This is not a calibrated resin fracture model.
"""


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


def make_resin_plate_deck(deck_text: str) -> str:
    """Replace only material 2 and its failure card with a resin visual candidate."""

    pattern = re.compile(
        r"/MAT/PLAS_JOHNS/2\n.*?/FAIL/JOHNSON/2\n.*?(?=\n#-  2\. NODES)",
        flags=re.DOTALL,
    )
    patched, count = pattern.subn(RESIN_MATERIAL_BLOCK.rstrip(), deck_text, count=1)
    if count != 1:
        raise ValueError("could not replace plate /MAT/PLAS_JOHNS/2 block")
    patched = patched.replace(
        "# GS-102-refined-candidate / FM-04a Tier 1 ballistic candidate (REFINED mesh)",
        "# GS-102-resin-plate-v1 / FM-04a Tier 1 resin visual candidate (REFINED mesh)",
    )
    patched = patched.replace(
        "#   * Refined mesh demonstrates JC damage element-deletion kinematics in the\n"
        "#     impact zone. Still NOT validated against Borvik 2002; NOT benchmark-quality.",
        "#   * Refined mesh demonstrates solver kinematics for a generic resin-like\n"
        "#     plate visual candidate. Still NOT validated; NOT benchmark-quality.",
    )
    patched = patched.replace(
        "#   * Materials, JC params, BCS clamp, contact, INIVEL all carried over from\n"
        "#     GS-102-candidate verbatim.",
        "#   * Projectile, BCS, contact, and INIVEL topology are carried over from\n"
        "#     GS-102-candidate. The plate material is replaced by an uncalibrated\n"
        "#     generic resin-like candidate under project_state/.",
    )
    patched = patched.replace(
        "GS-102-refined-candidate Tier 1 perforation demo (Borvik 2002 params, NOT validated)",
        "GS-102-resin-plate-v1 Tier 1 visual candidate (generic resin, NOT validated)",
    )
    patched = patched.replace(
        "# /INIVEL — V0 = 150 m/s (handgun-class), tuned so the spall debris\n"
        "#   stays in a viewable range for the demo bounding box. Real bullet\n"
        "#   speeds (>=285 m/s) work too but blow plate fragments out to ~200 mm\n"
        "#   which makes the GIF visually unreadable.\n"
        "#   In kg/mm/ms units: 150 m/s = 150 mm/ms.",
        "# /INIVEL - projectile speed is patched by\n"
        "#   scripts/gs102_transient_candidate_pipeline.py for each runtime case.\n"
        "#   In kg/mm/ms units: 1 m/s = 1 mm/ms.",
    )
    patched = patched.replace(
        "plate_weldox_460E",
        "plate_resin_visual_candidate",
    )
    return patched


def prepare_resin_variant(config: ResinVariantConfig) -> dict:
    _assert_safe_output_path(config.output_case_dir, config.repo_root)

    source_starter = config.source_case_dir / "model_00_0000.rad"
    source_engine = config.source_case_dir / "model_00_0001.rad"
    if not source_starter.exists() or not source_engine.exists():
        raise FileNotFoundError(
            f"expected starter and engine decks under {config.source_case_dir}"
        )

    config.output_case_dir.mkdir(parents=True, exist_ok=True)
    output_starter = config.output_case_dir / "model_00_0000.rad"
    output_engine = config.output_case_dir / "model_00_0001.rad"

    source_text = source_starter.read_text(encoding="utf-8")
    output_starter.write_text(make_resin_plate_deck(source_text), encoding="utf-8")
    shutil.copyfile(source_engine, output_engine)

    manifest = {
        "claim_boundary": CLAIM_BOUNDARY,
        "variant": "GS-102-resin-plate-v1",
        "material_claim": "generic resin-like visual candidate; uncalibrated",
        "projectile_material": "unchanged projectile_steel_hardened_candidate",
        "plate_material": {
            "name": "generic_resin_plate_visual_candidate",
            "rho_i_kg_per_mm3": 1.20e-6,
            "youngs_modulus_deck_units": 3.0,
            "poissons_ratio": 0.35,
            "johnson_cook_a_deck_units": 0.075,
            "johnson_cook_b_deck_units": 0.015,
            "johnson_cook_n": 0.20,
            "eps_p_max": "1E30",
            "failure_card": "omitted to keep cloud-carrying plate elements alive",
        },
        "source_case_dir": str(config.source_case_dir.relative_to(config.repo_root)),
        "output_case_dir": str(config.output_case_dir.relative_to(config.repo_root)),
        "source_starter_sha256": _sha256(source_starter),
        "output_starter_sha256": _sha256(output_starter),
        "source_engine_sha256": _sha256(source_engine),
        "output_engine_sha256": _sha256(output_engine),
    }
    manifest_path = config.output_case_dir.parent / "resin_plate_variant_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path.relative_to(config.repo_root))
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--source-case-dir", default=str(DEFAULT_SOURCE_CASE_DIR))
    parser.add_argument("--output-case-dir", default=str(DEFAULT_OUTPUT_CASE_DIR))
    return parser.parse_args(argv)


def _config_from_args(args: argparse.Namespace) -> ResinVariantConfig:
    repo_root = Path(args.repo_root).resolve()
    return ResinVariantConfig(
        repo_root=repo_root,
        source_case_dir=Path(args.source_case_dir).resolve(),
        output_case_dir=Path(args.output_case_dir).resolve(),
    )


def main(argv: list[str] | None = None) -> int:
    config = _config_from_args(_parse_args(argv))
    manifest = prepare_resin_variant(config)
    print("GS-102 resin plate variant prepared")
    print(CLAIM_BOUNDARY)
    print(manifest["manifest_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
