"""Golden Sample theory-vs-FEA validator (ADR-008 N-1 / P1-03).

P1-03 replaces P0 era's FEA-vs-FEA self-referential oracle. This module
compares real CalculiX output against a machine-readable theoretical
reference block (``validation_refs_v2``) in ``expected_results.json``
and enforces a per-metric tolerance (default 5% per PRD v0.2 §3.2).

The validator is intentionally small and dependency-free (numpy only):
it is meant to be called from both the pytest harness
(``tests/test_golden_sample_validation.py``) and from ad-hoc diagnostic
scripts.

``validation_refs_v2`` schema (added in P1-03):

    {
        "validation_refs_v2": {
            "default_tolerance_pct": 5.0,
            "metrics": [
                {
                    "id": "free_end_deflection_uy",
                    "source": "disp",
                    "reduction": "avg_magnitude_at_nodes",
                    "nodes": [11, 22, 33, 44],
                    "component": "UY",
                    "reference": 0.7619,
                    "unit": "mm",
                    "tolerance_pct": 5.0,
                    "reference_theory": "Euler-Bernoulli δ=PL³/(3EI)"
                },
                ...
            ]
        }
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from tools.frd_parser import parse_frd

_COMPONENT_INDEX = {
    "UX": 0,
    "UY": 1,
    "UZ": 2,
    "SXX": 0,
    "SYY": 1,
    "SZZ": 2,
    "SXY": 3,
    "SYZ": 4,
    "SZX": 5,
}


@dataclass
class MetricResult:
    metric_id: str
    reference: float
    computed: float
    error_pct: float
    tolerance_pct: float
    passed: bool
    unit: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "reference": self.reference,
            "computed": self.computed,
            "error_pct": round(self.error_pct, 4),
            "tolerance_pct": self.tolerance_pct,
            "passed": self.passed,
            "unit": self.unit,
            "detail": self.detail,
        }


@dataclass
class ValidationResult:
    case_id: str
    frd_path: str
    metrics: list[MetricResult]

    @property
    def passed(self) -> bool:
        return all(m.passed for m in self.metrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "frd_path": self.frd_path,
            "overall_passed": self.passed,
            "metrics": [m.to_dict() for m in self.metrics],
        }

    def summary_lines(self) -> list[str]:
        lines = [f"Golden-sample validation for {self.case_id}"]
        lines.append(f"  FRD: {self.frd_path}")
        lines.append(f"  Overall: {'PASS' if self.passed else 'FAIL'}")
        for m in self.metrics:
            verdict = "PASS" if m.passed else "FAIL"
            lines.append(
                f"  [{verdict}] {m.metric_id}: "
                f"computed={m.computed:.6g} {m.unit} vs "
                f"ref={m.reference:.6g} {m.unit} "
                f"(err={m.error_pct:+.2f}% / tol={m.tolerance_pct:.1f}%)"
            )
        return lines


def _iter_components(
    values: dict[int, np.ndarray],
    nodes: Iterable[int],
    component: str,
) -> list[float]:
    idx = _COMPONENT_INDEX.get(component.upper())
    if idx is None:
        raise ValueError(f"Unknown component {component!r}")
    out: list[float] = []
    for n in nodes:
        v = values.get(int(n))
        if v is None:
            continue
        out.append(float(v[idx]))
    return out


def _reduce(samples: list[float], reduction: str) -> float:
    if not samples:
        raise ValueError("No samples to reduce (empty node list or missing field).")
    reduction = reduction.lower()
    arr = np.asarray(samples, dtype=float)
    if reduction == "mean":
        return float(arr.mean())
    if reduction == "avg_magnitude_at_nodes":
        return float(np.mean(np.abs(arr)))
    if reduction == "max_magnitude_at_nodes":
        return float(np.max(np.abs(arr)))
    if reduction == "min":
        return float(arr.min())
    if reduction == "max":
        return float(arr.max())
    if reduction == "sum":
        return float(arr.sum())
    raise ValueError(f"Unknown reduction {reduction!r}")


def _compute_metric(parsed: dict[str, Any], spec: dict[str, Any]) -> float:
    source = spec["source"].lower()
    field = parsed["fields"].get(source)
    if field is None:
        raise KeyError(f"FRD has no field named {source!r}")
    values: dict[int, np.ndarray] = field["values"]

    reduction = spec.get("reduction", "avg_magnitude_at_nodes")

    if reduction == "von_mises_max":
        vms: list[float] = []
        for s in values.values():
            sxx, syy, szz, sxy, syz, szx = (float(x) for x in s[:6])
            vms.append(
                float(
                    np.sqrt(
                        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                        + 3 * (sxy**2 + syz**2 + szx**2)
                    )
                )
            )
        return max(vms) if vms else 0.0

    nodes = spec.get("nodes")
    if not nodes:
        raise ValueError("Metric spec requires 'nodes' unless reduction is a field-wide scalar.")
    component = spec.get("component", "UY")
    samples = _iter_components(values, nodes, component)
    return _reduce(samples, reduction)


def validate_frd(
    frd_path: Path,
    validation_refs: dict[str, Any],
    *,
    case_id: str = "UNKNOWN",
) -> ValidationResult:
    """Validate a CalculiX FRD against a validation_refs_v2 block."""
    parsed = parse_frd(Path(frd_path))
    default_tol = float(validation_refs.get("default_tolerance_pct", 5.0))
    metrics_out: list[MetricResult] = []

    for spec in validation_refs.get("metrics", []):
        metric_id = spec["id"]
        reference = float(spec["reference"])
        tol = float(spec.get("tolerance_pct", default_tol))
        unit = spec.get("unit", "")

        try:
            computed = _compute_metric(parsed, spec)
        except Exception as exc:  # noqa: BLE001 — record diagnostic
            metrics_out.append(
                MetricResult(
                    metric_id=metric_id,
                    reference=reference,
                    computed=float("nan"),
                    error_pct=float("inf"),
                    tolerance_pct=tol,
                    passed=False,
                    unit=unit,
                    detail=f"compute error: {exc}",
                )
            )
            continue

        if reference == 0.0:
            err_pct = abs(computed) * 100.0
        else:
            err_pct = (abs(computed) - abs(reference)) / abs(reference) * 100.0
        passed = abs(err_pct) <= tol

        metrics_out.append(
            MetricResult(
                metric_id=metric_id,
                reference=reference,
                computed=computed,
                error_pct=err_pct,
                tolerance_pct=tol,
                passed=passed,
                unit=unit,
                detail=spec.get("reference_theory", ""),
            )
        )

    return ValidationResult(
        case_id=case_id,
        frd_path=str(frd_path),
        metrics=metrics_out,
    )


def validate_case_dir(
    case_dir: Path,
    frd_path: Path,
) -> ValidationResult:
    """Load validation_refs_v2 from ``{case_dir}/expected_results.json``."""
    import json

    er = json.loads((case_dir / "expected_results.json").read_text(encoding="utf-8"))
    refs = er.get("validation_refs_v2")
    if not refs:
        raise KeyError(
            f"{case_dir}/expected_results.json is missing the "
            "'validation_refs_v2' block (P1-03 schema). "
            "This case has not been upgraded to theory-vs-FEA validation yet."
        )
    return validate_frd(frd_path, refs, case_id=er.get("case_id", case_dir.name))
