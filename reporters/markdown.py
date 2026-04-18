"""Markdown report generator for approval-ready FEA summaries."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

VERDICT_BADGES = {
    "accept": "✅",
    "accept with note": "🟡",
    "reject": "❌",
    "needs review": "⚠️",
    "re-run": "🔁",
    "pass": "✅",
    "fail": "❌",
    "review": "⚠️",
}


def _metric_label(field_result: dict[str, Any]) -> str:
    metric = field_result.get("metric") or field_result.get("field") or "field"
    if metric == "von_mises":
        return "von_mises"
    return str(metric)


def _reference_match(metric_label: str, refs: dict[str, float]) -> tuple[str, float | None]:
    candidates = [metric_label]
    if metric_label == "von_mises":
        candidates.append("stress")
    for candidate in candidates:
        if candidate in refs:
            return candidate, refs[candidate]
    return metric_label, None


def _format_metric_value(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.6g}"


def generate_report(results: dict[str, Any], output_dir: Path) -> Path:
    """Generate a Markdown analysis report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.md"

    case_id = results.get("case_id", "UNKNOWN")
    description = results.get("description", "")
    verdict = str(results.get("verdict", "Needs Review"))
    fields = results.get("fields", [])
    refs = results.get("reference_values", {})
    wall_time = results.get("wall_time_s")
    manifest_path = results.get("manifest_path")
    mesh_quality = results.get("mesh_quality")
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    verdict_badge = VERDICT_BADGES.get(verdict.lower(), "❓")
    lines: list[str] = [
        f"# FEA Analysis Report — {case_id}",
        "",
        f"> Generated: {timestamp}",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Case ID**: `{case_id}`",
        f"- **Description**: {description or 'N/A'}",
        f"- **Verdict**: {verdict_badge} **{verdict}**",
    ]
    if wall_time is not None:
        lines.append(f"- **Solve Wall Time**: {wall_time:.2f} s")
    if manifest_path:
        lines.append(f"- **Manifest**: `{manifest_path}`")
    lines.append("")

    if mesh_quality:
        lines.extend(
            [
                "## 2. Mesh Quality",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Min Jacobian | {mesh_quality.get('min_jacobian', 'N/A')} |",
                f"| Max Aspect Ratio | {mesh_quality.get('max_aspect_ratio', 'N/A')} |",
                "",
            ]
        )

    lines.extend(
        [
            "## 3. Approval Metrics",
            "",
        ]
    )
    if fields:
        lines.extend(
            [
                "| Metric | Max Magnitude | Max Node | Min Magnitude | Min Node |",
                "|--------|---------------|----------|---------------|----------|",
            ]
        )
        for field_result in fields:
            metric_label = _metric_label(field_result)
            max_value = field_result.get("max_magnitude")
            min_value = field_result.get("min_magnitude")
            lines.append(
                "| "
                f"{metric_label} | "
                f"{_format_metric_value(max_value)} | "
                f"{field_result.get('max_node')} | "
                f"{_format_metric_value(min_value)} | "
                f"{field_result.get('min_node')} |"
            )
        lines.append("")
    else:
        lines.extend(["_No field data available._", ""])

    if refs:
        lines.extend(
            [
                "## 4. Reference Comparison",
                "",
                "| Quantity | Reference | Computed | Δ (%) |",
                "|----------|-----------|----------|-------|",
            ]
        )
        for field_result in fields:
            metric_label = _metric_label(field_result)
            ref_key, ref_value = _reference_match(metric_label, refs)
            if ref_value is None:
                continue
            computed = field_result.get("max_magnitude")
            if computed is None or ref_value == 0:
                lines.append(f"| {ref_key} | {ref_value:.6g} | N/A | — |")
                continue
            delta = abs(computed - ref_value) / abs(ref_value) * 100.0
            lines.append(f"| {ref_key} | {ref_value:.6g} | {computed:.6g} | {delta:.1f}% |")
        lines.append("")

    lines.extend(
        [
            "## 5. Narrative",
            "",
            "The parsed FRD outputs were transformed into approval-grade metrics for review. "
            "Displacement is summarized by vector magnitude, and stress-based approval uses the "
            "derived von Mises scalar where tensor components are available.",
            "",
            "---",
            f"*Report generated by AI-FEA Engine · {case_id}*",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written -> %s", report_path)
    return report_path
