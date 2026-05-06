#!/usr/bin/env python3
"""Validate signed golden-sample registry metadata for ADR-011 HF3."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SIGNED_SAMPLE_RE = re.compile(r"^GS-\d{3}$")
FP_REF_RE = re.compile(r"^FP-\d{3}$")

REQUIRED_METADATA_FIELDS = ("case_id", "case_name", "analysis_type", "status")
ALLOWED_STATUSES = {"active", "pending_review", "insufficient_evidence", "deprecated"}


@dataclass(frozen=True)
class RegistryValidation:
    root: Path
    sample_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def sample_count(self) -> int:
        return len(self.sample_ids)


def _golden_root(root: Path) -> Path:
    if root.name == "golden_samples":
        return root
    return root / "golden_samples"


def discover_sample_dirs(root: Path) -> list[Path]:
    """Return signed golden-sample directories only.

    Directories such as ``GS-100-radioss-smoke`` and
    ``GS-101-demo-unsigned`` are intentionally excluded because their ADRs
    register them as smoke/demo fixtures, not signed validation samples.
    """

    golden_root = _golden_root(root)
    if not golden_root.exists():
        return []
    return sorted(
        path
        for path in golden_root.iterdir()
        if SIGNED_SAMPLE_RE.fullmatch(path.name) and not path.is_symlink() and path.is_dir()
    )


def validate_registry(root: str | Path) -> RegistryValidation:
    root_path = Path(root)
    golden_root = _golden_root(root_path)
    errors: list[str] = []
    warnings: list[str] = []

    if not golden_root.exists():
        return RegistryValidation(
            root=root_path,
            errors=[f"{_display(golden_root)}: missing golden_samples registry directory"],
        )

    sample_dirs = discover_sample_dirs(root_path)
    sample_ids = [path.name for path in sample_dirs]
    for path in sorted(golden_root.iterdir()):
        if not SIGNED_SAMPLE_RE.fullmatch(path.name):
            continue
        if path.is_symlink():
            errors.append(f"{path.name}: signed sample directory must not be a symlink")
        elif not path.is_dir():
            errors.append(f"{path.name}: signed sample entry must be a directory")

    if not sample_dirs:
        errors.append(f"{_display(golden_root)}: no signed GS-### sample directories found")

    for sample_dir in sample_dirs:
        sample_errors, sample_warnings = validate_sample_dir(sample_dir)
        errors.extend(sample_errors)
        warnings.extend(sample_warnings)

    return RegistryValidation(
        root=root_path,
        sample_ids=sample_ids,
        errors=errors,
        warnings=warnings,
    )


def validate_sample_dir(sample_dir: Path) -> tuple[list[str], list[str]]:
    sample_id = sample_dir.name
    errors: list[str] = []
    warnings: list[str] = []

    readme_path = sample_dir / "README.md"
    readme_text = ""
    if not readme_path.exists():
        errors.append(f"{sample_id}: missing README.md")
    else:
        readme_text = readme_path.read_text(encoding="utf-8").strip()
        if not readme_text:
            errors.append(f"{sample_id}: README.md must not be empty")

    metadata_path = sample_dir / "expected_results.json"
    metadata: dict[str, Any] | None = None
    if not metadata_path.exists():
        errors.append(f"{sample_id}: missing expected_results.json")
    else:
        metadata = _load_metadata(metadata_path, sample_id, errors)

    if metadata is not None:
        _validate_metadata(sample_id, metadata, readme_text, errors, warnings)

    if not _has_validation_artifact(sample_dir):
        errors.append(
            f"{sample_id}: must include at least one .inp or theory .py artifact "
            "as validation evidence"
        )

    return errors, warnings


def _load_metadata(
    metadata_path: Path,
    sample_id: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{sample_id}: expected_results.json is invalid JSON: {exc.msg}")
        return None

    if not isinstance(data, dict):
        errors.append(f"{sample_id}: expected_results.json must be a JSON object")
        return None
    return data


def _validate_metadata(
    sample_id: str,
    metadata: dict[str, Any],
    readme_text: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    for field_name in REQUIRED_METADATA_FIELDS:
        value = metadata.get(field_name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{sample_id}: missing required metadata field {field_name}")

    case_id = metadata.get("case_id")
    if isinstance(case_id, str) and case_id != sample_id:
        errors.append(f"{sample_id}: case_id must match directory name")

    status = metadata.get("status")
    if isinstance(status, str) and status not in ALLOWED_STATUSES:
        errors.append(
            f"{sample_id}: status must be one of {', '.join(sorted(ALLOWED_STATUSES))}"
        )

    if status == "insufficient_evidence":
        _validate_insufficient_evidence(sample_id, metadata, readme_text, errors, warnings)


def _validate_insufficient_evidence(
    sample_id: str,
    metadata: dict[str, Any],
    readme_text: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    fp_ref = metadata.get("failure_pattern_ref")
    if not isinstance(fp_ref, str) or not fp_ref.strip():
        errors.append(f"{sample_id}: insufficient_evidence requires failure_pattern_ref")
    elif not FP_REF_RE.fullmatch(fp_ref):
        errors.append(f"{sample_id}: failure_pattern_ref must match FP-<id>")
    elif readme_text and fp_ref not in readme_text:
        warnings.append(f"{sample_id}: README.md should mention {fp_ref}")

    status_reason = metadata.get("status_reason")
    if not isinstance(status_reason, str) or not status_reason.strip():
        errors.append(f"{sample_id}: insufficient_evidence requires status_reason")


def _has_validation_artifact(sample_dir: Path) -> bool:
    for path in sample_dir.iterdir():
        if path.is_file() and path.suffix.lower() == ".inp":
            return True
        if path.is_file() and path.suffix == ".py" and "theory" in path.stem.lower():
            return True
    return False


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path.cwd(),
        type=Path,
        help="Repository root or golden_samples directory to validate.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = validate_registry(args.root)

    if result.ok:
        print(
            "HF3 golden-sample registry validation passed: "
            f"{result.sample_count} signed sample(s): {', '.join(result.sample_ids)}"
        )
        for warning in result.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        return 0

    print("HF3 golden-sample registry validation failed:", file=sys.stderr)
    for error in result.errors:
        print(f"- {error}", file=sys.stderr)
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
