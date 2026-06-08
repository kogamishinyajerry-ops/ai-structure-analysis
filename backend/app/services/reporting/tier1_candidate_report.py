"""Tier 1 candidate report packet builder (FM-04a Phase 2 E).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Single-shot builder that turns a completed Tier 1 candidate run into a
structured `Tier1CandidateReport` packet with:

* Header (case id, generation timestamp, claim tier, claim boundary).
* Inputs (starter / engine deck relpaths, projectile velocity, optional
  generator script reference).
* Solver evidence (cycles, frame count, deletion events).
* Ballistic metrics (perforation marker, residual velocity, crossing).
* Energy audit (Phase 2 A): closed_aggregate / partial_candidate /
  unavailable status + all 5 legacy energy keys + aggregate internal
  energy + external work + balance error percentage.
* Convergence study (Phase 2 B): combined verdict + per-axis stability.
* Visualization artifact references (blueprint, animation manifest,
  result-mesh playback files).
* Artifact hashes (every file referenced gets a SHA-256 entry).
* Assumptions + limitations + Tier 1 banner.

The packet renders to both Markdown and DOCX. The DOCX writer uses
`python-docx`, which is already a project dependency (used by the
existing report exporter).

Forbidden wording: ``benchmark agreement``, ``signed validation``,
``perforation completed``, ``bullet-through-steel complete``,
``validated physics``. The builder asserts the rendered packet stays
clean against these positive claims; the only acceptable mentions are
the explicit ``not <claim>`` disclaimer forms.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_BOUNDARY = (
    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
)
TIER1_BANNER = (
    "Tier 1 engineering candidate; not signed validation; not benchmark agreement."
)

DEFAULT_ASSUMPTIONS: tuple[str, ...] = (
    "Projectile + plate material parameters per ADR-024 (lite) cite from "
    "Borvik 2002 Part II Table 2.",
    "Candidate run uses the deck registered under `golden_samples/*-candidate/`; "
    "no `^GS-\\d{3}$` signed registry entry is referenced.",
    "Per-term plastic / contact / hourglass energy breakdown is aggregated into "
    "OpenRadioss `I-ENERGY` until `/TH/PART` or `/TH/MAT` cards are added.",
    "Values reported in the OpenRadioss deck unit system (kg/mm/ms in the "
    "GS-102-candidate family); reviewers must trust deck units or attach an "
    "explicit unit-conversion note.",
)
DEFAULT_LIMITATIONS: tuple[str, ...] = (
    "Not signed validation. Not benchmark agreement. Not perforation completion.",
    "No `benchmark_comparison_candidate.json` exists; comparison vs experimental "
    "data is deferred to FM-04b P7.",
    "No sealed packet (SHA freeze + manifest of manifests); FM-04b P8 covers that.",
    "No independent reviewer signoff; FM-04b P8 / ADR-011 cover that gate.",
)


@dataclass(frozen=True)
class ArtifactHash:
    relpath: str
    sha256: str | None
    bytes_count: int | None


@dataclass(frozen=True)
class Tier1CandidateReport:
    case_id: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    inputs: dict[str, Any]
    solver_evidence: dict[str, Any]
    ballistic_metrics: dict[str, Any]
    energy_audit: dict[str, Any]
    convergence_study: dict[str, Any]
    visualization: dict[str, Any]
    artifact_hashes: list[ArtifactHash]
    assumptions: list[str]
    limitations: list[str]
    notes: str | None = None


@dataclass
class Tier1CandidateReportInputs:
    """Builder inputs.

    All paths are absolute or repo-rooted. Optional fields may be ``None``
    when the corresponding evidence is not yet produced; the builder
    surfaces ``status: "unavailable"`` blocks rather than failing.
    """

    case_id: str
    ballistic_metrics_path: Path
    convergence_study_path: Path | None = None
    blueprint_image_path: Path | None = None
    animation_manifest_path: Path | None = None
    result_mesh_path: Path | None = None
    starter_deck_relpath: str | None = None
    engine_deck_relpath: str | None = None
    generator_script_relpath: str | None = None
    notes: str | None = None
    additional_assumptions: Sequence[str] = field(default_factory=tuple)
    repo_root: Path | None = None


def build_tier1_candidate_report(
    inputs: Tier1CandidateReportInputs,
) -> Tier1CandidateReport:
    """Build the structured Tier 1 candidate report packet.

    Reads the ballistic_metrics.json sidecar (required) and the optional
    convergence_study.json sidecar; assembles inputs + solver_evidence +
    ballistic_metrics + energy_audit + convergence_study + visualization
    + artifact_hashes + assumptions + limitations sections; preserves the
    Tier 1 claim boundary throughout.
    """
    if not inputs.ballistic_metrics_path.is_file():
        raise FileNotFoundError(
            f"ballistic_metrics.json not found at {inputs.ballistic_metrics_path}"
        )

    metrics = json.loads(inputs.ballistic_metrics_path.read_text(encoding="utf-8"))
    convergence_payload: dict[str, Any] | None = None
    if inputs.convergence_study_path is not None and inputs.convergence_study_path.is_file():
        convergence_payload = json.loads(
            inputs.convergence_study_path.read_text(encoding="utf-8")
        )

    repo_root = inputs.repo_root or Path.cwd()

    inputs_section = _build_inputs_section(metrics, inputs)
    solver_section = _build_solver_section(metrics)
    metrics_section = _build_metrics_section(metrics)
    energy_section = _build_energy_section(metrics)
    convergence_section = _build_convergence_section(convergence_payload)
    visualization_section = _build_visualization_section(inputs, repo_root)

    artifact_files: list[Path] = [inputs.ballistic_metrics_path]
    for optional in (
        inputs.convergence_study_path,
        inputs.blueprint_image_path,
        inputs.animation_manifest_path,
        inputs.result_mesh_path,
    ):
        if optional is not None and optional.is_file():
            artifact_files.append(optional)
    artifact_hashes = [_hash_artifact(path, repo_root) for path in artifact_files]

    assumptions = list(DEFAULT_ASSUMPTIONS) + list(inputs.additional_assumptions)
    limitations = list(DEFAULT_LIMITATIONS)

    report = Tier1CandidateReport(
        case_id=inputs.case_id,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        inputs=inputs_section,
        solver_evidence=solver_section,
        ballistic_metrics=metrics_section,
        energy_audit=energy_section,
        convergence_study=convergence_section,
        visualization=visualization_section,
        artifact_hashes=artifact_hashes,
        assumptions=assumptions,
        limitations=limitations,
        notes=inputs.notes,
    )
    _assert_no_overclaim(report)
    return report


def render_tier1_report_markdown(report: Tier1CandidateReport) -> str:
    """Render the Tier 1 report as a structured markdown document."""
    lines: list[str] = []
    lines.append(f"# Tier 1 Candidate Report — {report.case_id}")
    lines.append("")
    lines.append(f"> {TIER1_BANNER}")
    lines.append(f"> Generated (UTC): {report.generated_at_utc}")
    lines.append(f"> Claim tier: {report.claim_tier}")
    lines.append(f"> Claim boundary: `{report.claim_boundary}`")
    lines.append("")

    _emit_section(lines, "Inputs", report.inputs)
    _emit_section(lines, "Solver evidence", report.solver_evidence)
    _emit_section(lines, "Ballistic metrics", report.ballistic_metrics)
    _emit_section(lines, "Energy audit (Phase 2 A)", report.energy_audit)
    _emit_section(lines, "Convergence study (Phase 2 B)", report.convergence_study)
    _emit_section(lines, "Visualization artifacts", report.visualization)

    lines.append("## Artifact hashes")
    lines.append("")
    if report.artifact_hashes:
        lines.append("| Path | SHA-256 | Bytes |")
        lines.append("|---|---|---|")
        for h in report.artifact_hashes:
            lines.append(
                f"| `{h.relpath}` | `{h.sha256 or 'missing'}` | "
                f"{h.bytes_count if h.bytes_count is not None else 'n/a'} |"
            )
    else:
        lines.append("No artifact hashes recorded.")
    lines.append("")

    lines.append("## Assumptions")
    lines.append("")
    for item in report.assumptions:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for item in report.limitations:
        lines.append(f"- {item}")
    lines.append("")

    if report.notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(report.notes)
        lines.append("")

    lines.append("## Claim boundary")
    lines.append("")
    lines.append(f"`{report.claim_boundary}`")
    lines.append("")
    lines.append("Tier 1 evidence; not signed validation; not benchmark agreement.")
    lines.append("")

    return "\n".join(lines)


def render_tier1_report_docx_bytes(report: Tier1CandidateReport) -> bytes:
    """Render the Tier 1 report as a DOCX byte string."""
    # python-docx is already a top-level project dep; importing inline keeps
    # the module importable in test environments that skip the dep.
    from io import BytesIO

    from docx import Document  # noqa: PLC0415
    from docx.shared import Pt  # noqa: PLC0415

    doc = Document()
    title = doc.add_heading(f"Tier 1 Candidate Report — {report.case_id}", level=0)
    title.alignment = 0
    doc.add_paragraph(TIER1_BANNER).runs[0].italic = True
    info = doc.add_paragraph()
    info.add_run(
        f"Generated (UTC): {report.generated_at_utc}\nClaim tier: {report.claim_tier}\n"
        f"Claim boundary: {report.claim_boundary}"
    ).font.size = Pt(10)

    for heading, payload in (
        ("Inputs", report.inputs),
        ("Solver evidence", report.solver_evidence),
        ("Ballistic metrics", report.ballistic_metrics),
        ("Energy audit (Phase 2 A)", report.energy_audit),
        ("Convergence study (Phase 2 B)", report.convergence_study),
        ("Visualization artifacts", report.visualization),
    ):
        doc.add_heading(heading, level=1)
        _emit_docx_kv_table(doc, payload)

    doc.add_heading("Artifact hashes", level=1)
    if report.artifact_hashes:
        table = doc.add_table(rows=1, cols=3)
        hdr = table.rows[0].cells
        hdr[0].text = "Path"
        hdr[1].text = "SHA-256"
        hdr[2].text = "Bytes"
        for h in report.artifact_hashes:
            row = table.add_row().cells
            row[0].text = h.relpath
            row[1].text = h.sha256 or "missing"
            row[2].text = str(h.bytes_count) if h.bytes_count is not None else "n/a"
    else:
        doc.add_paragraph("No artifact hashes recorded.")

    doc.add_heading("Assumptions", level=1)
    for item in report.assumptions:
        doc.add_paragraph(item, style="List Bullet")
    doc.add_heading("Limitations", level=1)
    for item in report.limitations:
        doc.add_paragraph(item, style="List Bullet")

    if report.notes:
        doc.add_heading("Notes", level=1)
        doc.add_paragraph(report.notes)

    doc.add_heading("Claim boundary", level=1)
    doc.add_paragraph(report.claim_boundary)
    doc.add_paragraph(
        "Tier 1 evidence; not signed validation; not benchmark agreement."
    )

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def write_tier1_report_artifacts(
    report: Tier1CandidateReport,
    output_dir: Path | str,
) -> dict[str, Path]:
    """Write `<case-id>_Tier1_candidate_report.{md,docx}` under output_dir.

    Refuses output paths under `golden_samples/**`. Returns a mapping
    with keys ``markdown`` and ``docx``.
    """
    out_dir = Path(output_dir)
    _assert_not_in_golden_samples(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{report.case_id}_Tier1_candidate_report.md"
    docx_path = out_dir / f"{report.case_id}_Tier1_candidate_report.docx"
    md_path.write_text(render_tier1_report_markdown(report), encoding="utf-8")
    docx_path.write_bytes(render_tier1_report_docx_bytes(report))
    return {"markdown": md_path, "docx": docx_path}


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _build_inputs_section(
    metrics: dict[str, Any], inputs: Tier1CandidateReportInputs
) -> dict[str, Any]:
    extraction = metrics.get("extraction_metadata", {})
    return {
        "case_id": metrics.get("case_id", inputs.case_id),
        "starter_deck_relpath": inputs.starter_deck_relpath or "not declared",
        "engine_deck_relpath": inputs.engine_deck_relpath or "not declared",
        "generator_script_relpath": inputs.generator_script_relpath or "not declared",
        "projectile_initial_velocity_m_per_s": metrics.get(
            "projectile_initial_velocity_m_per_s"
        ),
        "projectile_mass_kg": extraction.get("projectile_mass_kg"),
        "plate_back_face_axis_value_m": extraction.get("plate_back_face_axis_value_m"),
        "plate_thickness_m": extraction.get("plate_thickness_m"),
        "impact_axis": extraction.get("impact_axis", "x"),
        "claim_impact": extraction.get(
            "claim_impact",
            "Tier 1 candidate inputs only; not signed validation; not benchmark agreement",
        ),
    }


def _build_solver_section(metrics: dict[str, Any]) -> dict[str, Any]:
    block = metrics.get("solver_evidence") or {}
    return {
        "status": block.get("status", "unavailable"),
        "starter_error_count": block.get("starter_error_count"),
        "starter_warning_count": block.get("starter_warning_count"),
        "engine_normal_termination": block.get("engine_normal_termination"),
        "engine_cycle_count": block.get("engine_cycle_count"),
        "animation_frame_count": block.get("animation_frame_count"),
        "live_solid_count": block.get("live_solid_count"),
        "total_solid_count": block.get("total_solid_count"),
        "deleted_element_count": block.get("deleted_element_count"),
        "claim_impact": block.get(
            "claim_impact",
            "Tier 1 solver evidence only; not signed validation; "
            "not benchmark agreement.",
        ),
    }


def _build_metrics_section(metrics: dict[str, Any]) -> dict[str, Any]:
    crossing = metrics.get("crossing_evidence") or {}
    return {
        "perforation_marker": metrics.get("perforation_marker"),
        "projectile_initial_velocity_m_per_s": metrics.get(
            "projectile_initial_velocity_m_per_s"
        ),
        "residual_velocity_candidate_m_per_s": metrics.get(
            "residual_velocity_candidate_m_per_s"
        ),
        "crossing_status": crossing.get("status"),
        "front_face_crossed": crossing.get("front_face_crossed"),
        "back_face_crossed": crossing.get("back_face_crossed"),
        "first_back_face_crossing_t_s": crossing.get("first_back_face_crossing_t_s"),
        "claim_boundary": metrics.get("claim_boundary", CLAIM_BOUNDARY),
    }


def _build_energy_section(metrics: dict[str, Any]) -> dict[str, Any]:
    audit = metrics.get("energy_audit") or metrics.get("partial_energy_audit") or {}
    return {
        "status": audit.get("status", "unavailable"),
        "initial_kinetic_energy_j": audit.get("initial_kinetic_energy_j"),
        "residual_kinetic_energy_j": audit.get("residual_kinetic_energy_j"),
        "aggregate_internal_energy_j": audit.get("aggregate_internal_energy_j"),
        "external_work_j": audit.get("external_work_j"),
        "plastic_dissipation_j": audit.get("plastic_dissipation_j"),
        "contact_friction_j": audit.get("contact_friction_j"),
        "hourglass_energy_j": audit.get("hourglass_energy_j"),
        "energy_balance_error_pct": audit.get("energy_balance_error_pct"),
        "breakdown_status": audit.get("breakdown_status", "unavailable"),
        "missing_terms": audit.get("missing_terms", []),
        "unit_system_note": audit.get(
            "unit_system_note",
            "OpenRadioss deck unit system; reviewers must verify deck units.",
        ),
        "claim_impact": audit.get(
            "claim_impact",
            "Energy audit unavailable for this Tier 1 candidate run; "
            "not signed validation; not benchmark agreement.",
        ),
    }


def _build_convergence_section(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if payload is None:
        return {
            "status": "unavailable",
            "combined_verdict": "insufficient_data",
            "mesh_sweep_stability": "unknown",
            "dt_sweep_stability": "unknown",
            "row_count": 0,
            "tolerance_pct": None,
            "claim_impact": (
                "No convergence study attached; Tier 1 convergence evidence "
                "is not available; not signed validation; not benchmark "
                "agreement."
            ),
        }
    mesh_sweep = payload.get("mesh_sweep") or {}
    dt_sweep = payload.get("dt_sweep") or {}
    return {
        "status": "available",
        "combined_verdict": payload.get("combined_verdict", "insufficient_data"),
        "mesh_sweep_stability": mesh_sweep.get("candidate_stability", "unknown"),
        "dt_sweep_stability": dt_sweep.get("candidate_stability", "unknown"),
        "row_count": payload.get("row_count", 0),
        "tolerance_pct": payload.get("tolerance_pct"),
        "claim_impact": payload.get(
            "claim_impact",
            "Tier 1 convergence study evidence only; not signed validation; "
            "not benchmark agreement.",
        ),
    }


def _build_visualization_section(
    inputs: Tier1CandidateReportInputs, repo_root: Path
) -> dict[str, Any]:
    def rel(path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return str(path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            return str(path)

    return {
        "blueprint_image_relpath": rel(inputs.blueprint_image_path),
        "animation_manifest_relpath": rel(inputs.animation_manifest_path),
        "result_mesh_relpath": rel(inputs.result_mesh_path),
        "claim_impact": (
            "Visualization artifacts are Tier 1 candidate evidence; "
            "not signed validation; not benchmark agreement."
        ),
    }


def _hash_artifact(path: Path, repo_root: Path) -> ArtifactHash:
    if not path.is_file():
        return ArtifactHash(relpath=_relpath(path, repo_root), sha256=None, bytes_count=None)
    raw = path.read_bytes()
    return ArtifactHash(
        relpath=_relpath(path, repo_root),
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes_count=len(raw),
    )


def _relpath(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _emit_section(lines: list[str], heading: str, payload: dict[str, Any]) -> None:
    lines.append(f"## {heading}")
    lines.append("")
    if not payload:
        lines.append("No data attached.")
        lines.append("")
        return
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for key, value in payload.items():
        lines.append(f"| `{key}` | {_md_value(value)} |")
    lines.append("")


def _md_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("|", "\\|")
    return text


def _emit_docx_kv_table(doc: Any, payload: dict[str, Any]) -> None:
    if not payload:
        doc.add_paragraph("No data attached.")
        return
    table = doc.add_table(rows=1, cols=2)
    hdr = table.rows[0].cells
    hdr[0].text = "Field"
    hdr[1].text = "Value"
    for key, value in payload.items():
        row = table.add_row().cells
        row[0].text = key
        row[1].text = _md_value(value)


def _assert_no_overclaim(report: Tier1CandidateReport) -> None:
    """Refuse to emit a packet that contains forbidden positive claims."""
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(
        {
            "header": [
                report.case_id,
                report.claim_tier,
                report.claim_boundary,
                report.notes or "",
            ],
            "sections": [
                report.inputs,
                report.solver_evidence,
                report.ballistic_metrics,
                report.energy_audit,
                report.convergence_study,
                report.visualization,
            ],
            "assumptions": report.assumptions,
            "limitations": report.limitations,
        },
        default=str,
    ).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"Tier 1 candidate report contains forbidden positive claim: {token!r}"
            )


def _assert_not_in_golden_samples(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "golden_samples":
            raise ValueError(
                "Tier 1 candidate report refuses writes under golden_samples/**; "
                "use reports/ or project_state/<...>/ instead"
            )
