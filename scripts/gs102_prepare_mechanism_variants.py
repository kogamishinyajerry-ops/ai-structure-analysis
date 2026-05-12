#!/usr/bin/env python3
"""Prepare project_state-only GS-102 mechanism diagnostic source decks.

Tier 1 engineering-candidate diagnostics only. These generated sources are
runtime inputs for sensitivity probes; they are not signed validation decks.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CASE_DIR = (
    REPO_ROOT_DEFAULT / "golden_samples" / "GS-102-refined-candidate" / "data"
)
DEFAULT_OUTPUT_ROOT = REPO_ROOT_DEFAULT / "project_state" / "diagnostic_sources"


@dataclass(frozen=True)
class TextReplacement:
    file_name: str
    old: str
    new: str
    rationale: str


@dataclass(frozen=True)
class MechanismVariant:
    key: str
    label: str
    replacements: tuple[TextReplacement, ...]


DEFAULT_VARIANTS: tuple[MechanismVariant, ...] = (
    MechanismVariant(
        key="cfl_080",
        label="lower /DT/NODA/CST CFL from 0.90 to 0.80",
        replacements=(
            TextReplacement(
                file_name="model_00_0001.rad",
                old="0.9 0.0",
                new="0.8 0.0",
                rationale="diagnose explicit time-step stability-window sensitivity",
            ),
        ),
    ),
    MechanismVariant(
        key="cfl_085",
        label="lower /DT/NODA/CST CFL from 0.90 to 0.85",
        replacements=(
            TextReplacement(
                file_name="model_00_0001.rad",
                old="0.9 0.0",
                new="0.85 0.0",
                rationale="diagnose local CFL convergence below baseline",
            ),
        ),
    ),
    MechanismVariant(
        key="cfl_095",
        label="raise /DT/NODA/CST CFL from 0.90 to 0.95",
        replacements=(
            TextReplacement(
                file_name="model_00_0001.rad",
                old="0.9 0.0",
                new="0.95 0.0",
                rationale="diagnose local CFL convergence above baseline",
            ),
        ),
    ),
    MechanismVariant(
        key="cfl_100",
        label="raise /DT/NODA/CST CFL from 0.90 to 1.00",
        replacements=(
            TextReplacement(
                file_name="model_00_0001.rad",
                old="0.9 0.0",
                new="1.0 0.0",
                rationale="diagnose explicit time-step upper stability-window sensitivity",
            ),
        ),
    ),
    MechanismVariant(
        key="anim_dt_0005",
        label="halve /ANIM/DT output cadence from 0.001 ms to 0.0005 ms",
        replacements=(
            TextReplacement(
                file_name="model_00_0001.rad",
                old="0.0  0.001",
                new="0.0  0.0005",
                rationale="diagnose output-sampling sensitivity of crossing evidence",
            ),
        ),
    ),
    MechanismVariant(
        key="plate_epspmax_045",
        label="raise plate EPS_p_max from 0.30 to 0.45",
        replacements=(
            TextReplacement(
                file_name="model_00_0000.rad",
                old=(
                    "                 490                 383                 .45"
                    "                 0.3                   0"
                ),
                new=(
                    "                 490                 383                 .45"
                    "                0.45                   0"
                ),
                rationale="diagnose plate deletion-strain sensitivity",
            ),
        ),
    ),
    MechanismVariant(
        key="contact_fric_005",
        label="raise Type7 contact FRIC from 0.00 to 0.05",
        replacements=(
            TextReplacement(
                file_name="model_00_0000.rad",
                old=(
                    "                   0                   0                  .1"
                    "                   0                   0"
                ),
                new=(
                    "                   0                 .05                  .1"
                    "                   0                   0"
                ),
                rationale="diagnose projectile-plate friction/contact sensitivity",
            ),
        ),
    ),
    MechanismVariant(
        key="cfl_045",
        label="lower /DT/NODA/CST CFL from 0.90 to 0.45",
        replacements=(
            TextReplacement(
                file_name="model_00_0001.rad",
                old="0.9 0.0",
                new="0.45 0.0",
                rationale="diagnose explicit time-step sensitivity",
            ),
        ),
    ),
)


def prepare_mechanism_variants(
    *,
    repo_root: Path,
    source_case_dir: Path,
    output_root: Path,
    variant_keys: Sequence[str] | None = None,
) -> list[Path]:
    variants = _select_variants(variant_keys)
    _assert_project_state_output(output_root, repo_root)
    source_starter = source_case_dir / "model_00_0000.rad"
    source_engine = source_case_dir / "model_00_0001.rad"
    if not source_starter.exists() or not source_engine.exists():
        raise FileNotFoundError(f"missing source decks under {source_case_dir}")

    prepared: list[Path] = []
    for variant in variants:
        variant_dir = output_root / f"GS-102-v365-{variant.key}" / "data"
        _assert_project_state_output(variant_dir, repo_root)
        variant_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_starter, variant_dir / "model_00_0000.rad")
        shutil.copyfile(source_engine, variant_dir / "model_00_0001.rad")
        applied = _apply_variant(variant_dir, variant)
        (variant_dir.parent / "diagnostic_variant.json").write_text(
            json.dumps(
                {
                    "variant_key": variant.key,
                    "label": variant.label,
                    "claim_boundary": (
                        "tier1_engineering_candidate; not_signed_validation; "
                        "not_benchmark_agreement"
                    ),
                    "source_case_dir": _rel(source_case_dir, repo_root),
                    "generated_case_dir": _rel(variant_dir, repo_root),
                    "replacements": applied,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        prepared.append(variant_dir)
    return prepared


def _select_variants(variant_keys: Sequence[str] | None) -> tuple[MechanismVariant, ...]:
    if not variant_keys:
        return DEFAULT_VARIANTS
    by_key = {variant.key: variant for variant in DEFAULT_VARIANTS}
    missing = [key for key in variant_keys if key not in by_key]
    if missing:
        raise ValueError(f"unknown variant key(s): {', '.join(missing)}")
    return tuple(by_key[key] for key in variant_keys)


def _apply_variant(variant_dir: Path, variant: MechanismVariant) -> list[dict[str, str]]:
    applied: list[dict[str, str]] = []
    for replacement in variant.replacements:
        target = variant_dir / replacement.file_name
        text = target.read_text(encoding="utf-8")
        count = text.count(replacement.old)
        if count != 1:
            raise ValueError(
                f"{variant.key}: expected one match for {replacement.file_name}, got {count}"
            )
        target.write_text(text.replace(replacement.old, replacement.new), encoding="utf-8")
        applied.append(
            {
                "file_name": replacement.file_name,
                "old": replacement.old,
                "new": replacement.new,
                "rationale": replacement.rationale,
            }
        )
    return applied


def _assert_project_state_output(path: Path, repo_root: Path) -> None:
    try:
        parts = path.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        parts = path.resolve().parts
    if "golden_samples" in parts:
        raise ValueError(f"refuses to write inside golden_samples/**: {path}")
    if "project_state" not in parts:
        raise ValueError(f"diagnostic sources must live under project_state/: {path}")


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT))
    parser.add_argument("--source-case-dir", default=str(DEFAULT_SOURCE_CASE_DIR))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--variant", action="append", dest="variant_keys")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    prepared = prepare_mechanism_variants(
        repo_root=repo_root,
        source_case_dir=Path(args.source_case_dir).resolve(),
        output_root=Path(args.output_root).resolve(),
        variant_keys=args.variant_keys,
    )
    for path in prepared:
        print(f"prepared: {_rel(path, repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
