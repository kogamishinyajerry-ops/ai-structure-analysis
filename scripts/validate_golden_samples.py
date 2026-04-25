"""Golden-sample registry schema validator (FF-08 / HF3).

Validates the structure of `golden_samples/<id>/` against a fixed
contract derived from ADR-011 §HF3 + Golden Rule #5 ("no GS → no test")
and from the empirical FailurePatterns FP-001/002/003.

Required structure:

    golden_samples/<id>/
    ├── README.md                     (required, non-empty)
    ├── expected_results.json         (required, valid JSON, required top-level keys)
    ├── <id>.inp                      (CalculiX input — at least ONE of
    │                                  inp/theory script must exist)
    └── *_theory.py | *_theoretical.py  (theoretical reference)

Required top-level keys in expected_results.json:

    case_id              must equal directory name
    case_name            non-empty string
    analysis_type        from known set (static_analysis | modal_analysis |
                         thermal_structural | nonlinear_static)

Optional top-level keys:

    status               from {"active", "insufficient_evidence", "deprecated"}
                         per FP-001/002/003 recommendations.
                         Defaults to "active" when absent.
    case_description     dict (free-form)

Usage:
    python3 scripts/validate_golden_samples.py
        validates all directories matching golden_samples/GS-*/
    python3 scripts/validate_golden_samples.py golden_samples/GS-001
        validates single sample
    python3 scripts/validate_golden_samples.py --json
        emits JSON instead of human report

Exit codes:
    0 — all validated samples pass
    1 — at least one violation
    2 — usage / IO error
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

KNOWN_ANALYSIS_TYPES = frozenset(
    {
        "static_analysis",
        "modal_analysis",
        "thermal_structural",
        "nonlinear_static",
        "buckling_analysis",
        "dynamic_analysis",
    }
)

KNOWN_STATUSES = frozenset(
    {
        "active",
        "insufficient_evidence",
        "deprecated",
        "pending_review",
    }
)


@dataclass
class SampleValidation:
    sample_id: str
    sample_dir: str
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = "unknown"
    has_inp: bool = False
    has_theory_script: bool = False


def _is_theory_script(p: Path) -> bool:
    return (
        p.suffix == ".py"
        and (
            "theory" in p.name.lower()
            or "theoretical" in p.name.lower()
            or "analytical" in p.name.lower()
        )
    )


def validate_sample(sample_dir: Path) -> SampleValidation:
    sample_id = sample_dir.name
    result = SampleValidation(sample_id=sample_id, sample_dir=str(sample_dir))

    if not sample_dir.is_dir():
        result.violations.append(f"sample_dir is not a directory: {sample_dir}")
        return result

    # README.md
    readme = sample_dir / "README.md"
    if not readme.is_file():
        result.violations.append("missing README.md")
    elif readme.stat().st_size == 0:
        result.violations.append("README.md is empty")

    # expected_results.json
    expected = sample_dir / "expected_results.json"
    if not expected.is_file():
        result.violations.append("missing expected_results.json")
        return result  # without this we can't validate anything else

    try:
        with expected.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result.violations.append(f"expected_results.json is not valid JSON: {e.msg}")
        return result

    if not isinstance(data, dict):
        result.violations.append("expected_results.json top-level must be an object")
        return result

    # case_id
    declared_id = data.get("case_id")
    if not declared_id:
        result.violations.append("expected_results.json: missing required `case_id`")
    elif declared_id != sample_id:
        result.violations.append(
            f"expected_results.json: `case_id` ({declared_id!r}) "
            f"does not match directory name ({sample_id!r})"
        )

    # case_name
    case_name = data.get("case_name")
    if not isinstance(case_name, str) or not case_name.strip():
        result.violations.append("expected_results.json: missing or empty `case_name`")

    # analysis_type
    analysis_type = data.get("analysis_type")
    if not isinstance(analysis_type, str) or not analysis_type.strip():
        result.violations.append("expected_results.json: missing or empty `analysis_type`")
    elif analysis_type not in KNOWN_ANALYSIS_TYPES:
        result.violations.append(
            f"expected_results.json: `analysis_type` ({analysis_type!r}) "
            f"not in known set {sorted(KNOWN_ANALYSIS_TYPES)}"
        )

    # status (optional, defaults to active)
    status = data.get("status", "active")
    result.status = status
    if status not in KNOWN_STATUSES:
        result.violations.append(
            f"expected_results.json: `status` ({status!r}) "
            f"not in known set {sorted(KNOWN_STATUSES)}"
        )

    # At least one of: <id>.inp, *theory*.py
    inp_path = sample_dir / f"{sample_id.lower()}.inp"
    has_inp = inp_path.is_file()
    if not has_inp:
        # Fallback: any .inp in the directory
        has_inp = any(p.suffix == ".inp" for p in sample_dir.iterdir())
    result.has_inp = has_inp

    has_theory = any(_is_theory_script(p) for p in sample_dir.iterdir())
    result.has_theory_script = has_theory

    if not has_inp and not has_theory:
        result.violations.append(
            "missing both .inp file and theory script — "
            "at least one is required (Golden Rule #5)"
        )

    # Cross-cut: if status is "insufficient_evidence", must have explanation
    # in README mentioning a FailurePattern
    if status == "insufficient_evidence" and readme.is_file():
        readme_text = readme.read_text(errors="replace")
        if "FP-" not in readme_text:
            result.warnings.append(
                "status=insufficient_evidence but README does not reference "
                "any FailurePattern (FP-NNN). Per FP-001/002/003, the "
                "evidence/attribution should be cross-linked."
            )

    return result


def discover_samples(root: Path) -> list[Path]:
    """Find all golden_samples/GS-*/ directories."""
    samples_root = root / "golden_samples" if root.name != "golden_samples" else root
    if not samples_root.is_dir():
        return []
    return sorted(p for p in samples_root.iterdir() if p.is_dir() and p.name.startswith("GS-"))


def to_json(results: list[SampleValidation]) -> str:
    return json.dumps(
        [
            {
                "sample_id": r.sample_id,
                "sample_dir": r.sample_dir,
                "status": r.status,
                "has_inp": r.has_inp,
                "has_theory_script": r.has_theory_script,
                "violations": r.violations,
                "warnings": r.warnings,
            }
            for r in results
        ],
        ensure_ascii=False,
        indent=2,
    )


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Validate golden_samples/<id>/ structure per ADR-011 §HF3 + FF-08."
    )
    parser.add_argument(
        "samples",
        nargs="*",
        type=Path,
        help="explicit sample dirs to validate (default: all golden_samples/GS-*/)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output instead of human report")
    parser.add_argument(
        "--root",
        type=Path,
        default=repo_root,
        help=f"repo root (default: {repo_root})",
    )
    args = parser.parse_args(argv[1:])

    if args.samples:
        sample_dirs = [s.resolve() for s in args.samples]
    else:
        sample_dirs = discover_samples(args.root)

    if not sample_dirs:
        sys.stderr.write("ERROR: no golden samples found\n")
        return 2

    results = [validate_sample(d) for d in sample_dirs]

    if args.json:
        print(to_json(results))
    else:
        for r in results:
            status_label = "OK" if not r.violations else "FAIL"
            print(f"[{status_label}] {r.sample_id} ({r.status})")
            print(f"        dir: {r.sample_dir}")
            print(f"        has_inp: {r.has_inp}, has_theory: {r.has_theory_script}")
            for v in r.violations:
                print(f"        VIOLATION: {v}")
            for w in r.warnings:
                print(f"        warn: {w}")
        ok = sum(1 for r in results if not r.violations)
        print()
        print(f"Summary: {ok}/{len(results)} OK, {len(results) - ok} violations")

    return 1 if any(r.violations for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
