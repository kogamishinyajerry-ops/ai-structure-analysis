#!/usr/bin/env python3
"""HF3 golden-sample registry schema validation.

The check is intentionally read-only over ``golden_samples/**``. It classifies
each ``GS-*`` directory into one of the explicit registry scopes:

* ``signed`` - a validation benchmark with a traceable source packet.
* ``smoke`` - adapter/runtime smoke fixture, not a validation benchmark.
* ``demo-unsigned`` - end-to-end demonstration fixture, not physics-signed.
* ``insufficient_evidence`` - previously proposed benchmark that cannot be
  used as a golden standard as configured.

Anything outside these scopes fails closed. This prevents smoke/demo fixtures
from silently entering the regression lane as signed golden standards and makes
HF3 ("no GS -> no test") mechanically checkable without modifying the frozen
sample artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCOPE_SIGNED = "signed"
SCOPE_SMOKE = "smoke"
SCOPE_DEMO_UNSIGNED = "demo-unsigned"
SCOPE_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
SCOPE_UNKNOWN = "unknown"

REGISTRY_SCOPES = frozenset(
    {
        SCOPE_SIGNED,
        SCOPE_SMOKE,
        SCOPE_DEMO_UNSIGNED,
        SCOPE_INSUFFICIENT_EVIDENCE,
    }
)
NON_SIGNED_SCOPES = frozenset({SCOPE_SMOKE, SCOPE_DEMO_UNSIGNED, SCOPE_INSUFFICIENT_EVIDENCE})
SIGNED_STATUSES = frozenset({"signed", "signed_golden", "golden_standard"})


@dataclass(frozen=True)
class GoldenSampleRecord:
    sample_id: str
    path: str
    scope: str
    signed: bool
    reason: str
    evidence_files: tuple[str, ...]


@dataclass(frozen=True)
class RegistryReport:
    root: str
    ok: bool
    signed_count: int
    records: tuple[GoldenSampleRecord, ...]
    violations: tuple[str, ...]


def _relative(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be a JSON object")
    return data


def _evidence_files(sample_dir: Path) -> tuple[str, ...]:
    files: list[str] = []
    for name in ("README.md", "expected_results.json", "validation_source.yaml"):
        if (sample_dir / name).exists():
            files.append(name)
    return tuple(files)


def classify_sample(sample_dir: Path) -> GoldenSampleRecord:
    """Classify one ``GS-*`` directory from local evidence."""
    sample_id = sample_dir.name
    readme = _read_text(sample_dir / "README.md")
    readme_l = readme.lower()
    expected_path = sample_dir / "expected_results.json"
    evidence = _evidence_files(sample_dir)

    if expected_path.exists():
        expected = _load_json(expected_path)
        status = str(expected.get("status", "")).strip().lower()

        if status == SCOPE_INSUFFICIENT_EVIDENCE:
            failure_ref = expected.get("failure_pattern_ref")
            reason = str(
                expected.get("status_reason") or "expected_results.json marks case insufficient"
            )
            if failure_ref:
                reason = f"{reason} ({failure_ref})"
            return GoldenSampleRecord(
                sample_id=sample_id,
                path=sample_dir.as_posix(),
                scope=SCOPE_INSUFFICIENT_EVIDENCE,
                signed=False,
                reason=reason,
                evidence_files=evidence,
            )

        if status in SIGNED_STATUSES:
            return GoldenSampleRecord(
                sample_id=sample_id,
                path=sample_dir.as_posix(),
                scope=SCOPE_SIGNED,
                signed=True,
                reason=f"expected_results.json status={status}",
                evidence_files=evidence,
            )

    if sample_id.endswith("-radioss-smoke") or "adapter smoke fixture" in readme_l:
        return GoldenSampleRecord(
            sample_id=sample_id,
            path=sample_dir.as_posix(),
            scope=SCOPE_SMOKE,
            signed=False,
            reason="OpenRadioss adapter smoke fixture; not a validation benchmark",
            evidence_files=evidence,
        )

    if sample_id.endswith("-demo-unsigned") or (
        "demo only" in readme_l and "not physics-signed" in readme_l
    ):
        return GoldenSampleRecord(
            sample_id=sample_id,
            path=sample_dir.as_posix(),
            scope=SCOPE_DEMO_UNSIGNED,
            signed=False,
            reason="functional demo fixture; not physics-signed",
            evidence_files=evidence,
        )

    return GoldenSampleRecord(
        sample_id=sample_id,
        path=sample_dir.as_posix(),
        scope=SCOPE_UNKNOWN,
        signed=False,
        reason="no recognized registry evidence",
        evidence_files=evidence,
    )


def iter_sample_dirs(root: Path) -> tuple[Path, ...]:
    if not root.exists():
        raise FileNotFoundError(f"golden-sample root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"golden-sample root is not a directory: {root}")
    return tuple(sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("GS-")))


def validate_records(records: tuple[GoldenSampleRecord, ...], root: Path) -> tuple[str, ...]:
    violations: list[str] = []
    if not records:
        violations.append(f"{root.as_posix()}: no GS-* sample directories found")

    for record in records:
        sample_path = Path(record.path)
        display_path = _relative(sample_path, root.parent)

        if record.scope not in REGISTRY_SCOPES:
            violations.append(
                f"{record.sample_id}: unknown registry scope; add explicit signed/smoke/"
                f"demo-unsigned/insufficient_evidence evidence before using this sample"
            )
            continue

        if record.scope in NON_SIGNED_SCOPES and record.signed:
            violations.append(
                f"{record.sample_id}: non-signed scope {record.scope} is marked signed"
            )

        if record.scope == SCOPE_SIGNED:
            required = {"README.md", "expected_results.json", "validation_source.yaml"}
            missing = sorted(required.difference(record.evidence_files))
            if missing:
                violations.append(
                    f"{record.sample_id}: signed sample missing required evidence files: "
                    f"{', '.join(missing)}"
                )
            if "validation_source.yaml" not in record.evidence_files:
                violations.append(
                    f"{record.sample_id}: signed sample lacks validation_source.yaml; "
                    "cannot trace public benchmark source"
                )

        if (
            record.scope == SCOPE_INSUFFICIENT_EVIDENCE
            and "expected_results.json" not in record.evidence_files
        ):
            violations.append(
                f"{record.sample_id}: insufficient_evidence scope requires "
                "expected_results.json status"
            )

        if (
            record.scope in (SCOPE_SMOKE, SCOPE_DEMO_UNSIGNED)
            and "README.md" not in record.evidence_files
        ):
            violations.append(
                f"{record.sample_id}: {record.scope} fixture requires README.md evidence"
            )

        if not sample_path.exists():
            violations.append(f"{record.sample_id}: classified path disappeared: {display_path}")

    return tuple(violations)


def build_report(root: Path) -> RegistryReport:
    root = root.resolve()
    records = tuple(classify_sample(sample_dir) for sample_dir in iter_sample_dirs(root))
    violations = validate_records(records, root)
    signed_count = sum(1 for record in records if record.signed)
    return RegistryReport(
        root=root.as_posix(),
        ok=not violations,
        signed_count=signed_count,
        records=records,
        violations=violations,
    )


def _report_to_json(report: RegistryReport) -> str:
    payload = {
        "root": report.root,
        "ok": report.ok,
        "signed_count": report.signed_count,
        "records": [asdict(record) for record in report.records],
        "violations": list(report.violations),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _report_to_text(report: RegistryReport) -> str:
    lines = [
        f"HF3 golden-sample registry: {'PASS' if report.ok else 'FAIL'}",
        f"root: {report.root}",
        f"signed_count: {report.signed_count}",
        "records:",
    ]
    for record in report.records:
        signoff = "signed" if record.signed else "not-signed"
        lines.append(f"  - {record.sample_id}: {record.scope} ({signoff})")
        lines.append(f"    reason: {record.reason}")
        if record.evidence_files:
            lines.append(f"    evidence: {', '.join(record.evidence_files)}")
    if report.violations:
        lines.append("violations:")
        for violation in report.violations:
            lines.append(f"  - {violation}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("golden_samples"),
        help="golden_samples root directory (default: golden_samples)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    args = parser.parse_args(argv)

    try:
        report = build_report(args.root)
    except (FileNotFoundError, NotADirectoryError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"HF3 registry check failed: {exc}\n")
        return 2

    output = _report_to_json(report) if args.format == "json" else _report_to_text(report)
    print(output)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
