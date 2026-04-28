"""Layer-4 report draft generator — RFC-001 §3 + ADR-012.

Wires the full Layer 1 → 3 stack into a single function that produces:
  * an ``EvidenceBundle`` whose items each cite a value derived from
    the solver result file (per ADR-012 every claim must trace to an
    ``evidence_id``);
  * a ``ReportSpec`` whose section content references those evidence
    IDs.

The MVP wedge — chemical / power design-institute static-strength
report — needs at minimum the maximum von Mises stress and the maximum
displacement magnitude. Everything beyond that (safety factor against
material yield, regulatory citations, deformation visualisations)
layers on top of these two core derivations.

Design constraints honoured:
  * ADR-001 — derivations live in ``app.domain.stress_derivatives``,
    not in any Layer-1 adapter.
  * ADR-003 — unit system flows from the reader's ``FieldMetadata``
    untouched. We never guess.
  * ADR-012 — every value placed in the report carries an
    ``evidence_id``; the EvidenceBundle is the audit trail.

What this module does NOT do (deferred to W4+ per RFC §6.4):
  * Standards-citation lookup (GB 50017 / ASME VIII Div 2 etc.).
  * Section template rendering — we emit Markdown-shaped strings,
    DOCX export will land in a separate ``services.report.exporter``.
  * LLM-generated narrative — RFC §2.3 ADR-010 forbids RAG / chat
    in the MVP report path.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Optional, Sequence, Tuple, Union

import numpy as np
import numpy.typing as npt


# Accept either a plain Python int sequence or a numpy ndarray. The
# narrower form ``npt.NDArray[np.integer[npt.NBitBase]]`` looks
# correct but mypy's generic-invariance rejects concrete subtypes
# like ``np.int64`` (Codex R2 PR #77 MEDIUM). Using ``npt.NDArray[Any]``
# accepts any-dtype arrays; runtime coercion via ``int()`` at the use
# site validates each element. Trade-off: we lose the static "must be
# integer dtype" check, but Codex confirmed runtime accepts a wide
# enough surface that the static narrowing wasn't load-bearing.
_IntArrayLike = Union[Sequence[int], "npt.NDArray[Any]"]
_FloatArrayLike = Union[Sequence[float], "npt.NDArray[Any]"]

from app.core.types import (
    CanonicalField,
    FieldData,
    FieldLocation,
    Material,
    ReaderHandle,
    SupportsElementDeletion,
    UnitSystem,
)
from app.domain.ballistics import (
    displacement_history,
    eroded_history,
    perforation_event_step,
)
from app.domain.stress_derivatives import von_mises
from app.domain.stress_linearization import (
    linearize_through_thickness,
    resample_to_uniform,
)
from app.models import (
    AnalyticalEvidence,
    EvidenceBundle,
    EvidenceItem,
    EvidenceType,
    ReferenceEvidence,
    ReportSection,
    ReportSpec,
    SimulationEvidence,
)
from app.services.report.allowable_stress import (
    AllowableStress,
    CodeStandard,
    compute_allowable_stress,
)
from app.services.report.boundary_summary import (
    BCSummary,
    load_boundary_conditions_yaml,
    summarize_boundary_conditions,
)
from app.services.report.model_overview import (
    ELEMENT_TYPE_GROUPS,
    GROUP_OTHER,
    ModelOverview,
    summarize_model,
)
from app.services.report.verdict import (
    DEFAULT_THRESHOLD,
    Verdict,
    compute_verdict,
)


__all__ = [
    "generate_ballistic_penetration_summary",
    "generate_static_strength_summary",
    "generate_lifting_lug_summary",
    "generate_pressure_vessel_local_stress_summary",
]


@dataclass(frozen=True)
class _SummaryLabels:
    """Per-template label set for the max-field summary engine.

    Centralising labels in one frozen dataclass keeps the public
    generators tiny and makes it impossible to forget a string when
    adding a new template-specific producer.
    """

    template_id: str
    title: str
    section_title: str
    bundle_title_prefix: str
    disp_evidence_id: str
    disp_evidence_title: str
    disp_bullet_label: str
    vm_evidence_id: str
    vm_evidence_title: str
    vm_bullet_label: str


def _unit_label_for_system(system: UnitSystem, dim: str) -> str:
    """Pick the canonical unit label for ``dim`` under ``system``.

    Adapters expose ``UnitSystem`` (closed-set per RFC §4.3); the
    report needs a string for the human reader. ``UNKNOWN`` returns
    a literal ``"unknown"`` rather than guessing — the wizard pins
    this before draft generation, so seeing ``unknown`` in a draft
    means an upstream contract leaked.
    """
    table: dict[UnitSystem, dict[str, str]] = {
        UnitSystem.SI: {"length": "m", "stress": "Pa", "force": "N"},
        UnitSystem.SI_MM: {"length": "mm", "stress": "MPa", "force": "N"},
        UnitSystem.ENGLISH: {"length": "in", "stress": "psi", "force": "lbf"},
        UnitSystem.UNKNOWN: {"length": "unknown", "stress": "unknown", "force": "unknown"},
    }
    return table[system][dim]


def _require_node_location(fd: FieldData, kind: str) -> None:
    """Layer-2 contract permits non-NODE fields (IP / centroid). The
    draft generator emits ``location="node N"`` strings, so it must
    refuse silently mislabelling a non-NODE field as a node value.
    A future Layer-3 projection helper can lift this guard.
    """
    if fd.metadata.location is not FieldLocation.NODE:
        raise ValueError(
            f"{kind} field is at {fd.metadata.location.value!r}; the W4-prep "
            "draft only supports NODE-located fields. Project to nodes "
            "via a Layer-3 helper before passing to the report draft."
        )


def _max_displacement(
    fd: Optional[FieldData], node_id_array: npt.NDArray[np.int64]
) -> Optional[Tuple[float, int]]:
    """Return ``(max_magnitude, node_id)`` of the max displacement.

    Magnitude = Euclidean norm of the (ux, uy, uz) vector.
    Returns ``None`` when no displacement field is available
    (per ADR-003 we do not fabricate). Raises ``ValueError`` when
    the field is not node-aligned (see ``_require_node_location``).
    """
    if fd is None:
        return None
    _require_node_location(fd, "displacement")
    arr = fd.values()  # shape (N, 3)
    if arr.size == 0:
        return None
    magnitudes = np.linalg.norm(arr, axis=1)
    idx = int(np.argmax(magnitudes))
    return float(magnitudes[idx]), int(node_id_array[idx])


def _max_von_mises(
    fd: Optional[FieldData], node_id_array: npt.NDArray[np.int64]
) -> Optional[Tuple[float, int]]:
    """Return ``(max σ_vm, node_id)`` from a stress-tensor field."""
    if fd is None:
        return None
    _require_node_location(fd, "stress-tensor")
    tensor = fd.values()  # shape (N, 6)
    if tensor.size == 0:
        return None
    vm = von_mises(tensor)
    idx = int(np.argmax(vm))
    return float(vm[idx]), int(node_id_array[idx])


_EQUIPMENT_FOUNDATION_LABELS = _SummaryLabels(
    template_id="equipment_foundation_static",
    title="Static-strength summary",
    section_title="结构强度摘要 (Static-strength summary)",
    bundle_title_prefix="Evidence backing",
    disp_evidence_id="EV-DISP-MAX",
    disp_evidence_title="Maximum displacement magnitude",
    disp_bullet_label="最大位移",
    vm_evidence_id="EV-VM-MAX",
    vm_evidence_title="Maximum von Mises stress",
    vm_bullet_label="最大 von Mises 应力",
)


_LIFTING_LUG_LABELS = _SummaryLabels(
    template_id="lifting_lug",
    title="Lifting-lug strength assessment",
    section_title="吊耳强度评估 (Lifting-lug strength assessment)",
    bundle_title_prefix="Evidence backing",
    # Lug-specific evidence IDs so the bundle can carry both an
    # equipment-foundation report and a lug report without ID collision.
    disp_evidence_id="EV-LUG-DISP-MAX",
    disp_evidence_title="Maximum displacement at lifting lug under hoist load",
    disp_bullet_label="吊装工况下最大位移",
    vm_evidence_id="EV-LUG-VM-MAX",
    vm_evidence_title="Maximum von Mises stress at lifting lug under hoist load",
    vm_bullet_label="吊装工况下最大 von Mises 应力",
)


def _build_max_field_summary(
    reader: ReaderHandle,
    labels: _SummaryLabels,
    *,
    project_id: str,
    task_id: str,
    report_id: str,
    bundle_id: str,
    step_id: Optional[int],
    material: Optional[Material] = None,
    code: Optional[CodeStandard] = None,
    threshold: float = DEFAULT_THRESHOLD,
    temperature_C: float = 20.0,
    bc_yaml_path: Optional[Path] = None,
) -> Tuple[ReportSpec, EvidenceBundle]:
    """Shared engine for max-field summary reports.

    Common to both ``equipment_foundation_static`` and ``lifting_lug``
    templates: extract DISPLACEMENT + STRESS_TENSOR from the chosen
    solution state, mint two SimulationEvidence items, and emit a
    single bilingual section that cites both. The caller distinguishes
    by passing different :class:`_SummaryLabels`.

    A real lifting-lug check ideally restricts the search to the
    lug-shell weld region. The MVP wedge does not yet expose region
    selection at Layer 2/3, so the engineer is responsible for ensuring
    the FE model's max σ_vm location IS the lug region (or for sharing
    a region-selecting reader once that landed in W5+).
    """
    states = reader.solution_states
    if not states:
        raise ValueError(
            f"reader for task {task_id!r} has no solution states; "
            "nothing to summarise"
        )
    if step_id is None:
        step = states[-1]
    else:
        matches = [s for s in states if s.step_id == step_id]
        if not matches:
            raise ValueError(
                f"step_id={step_id!r} not present in reader for task "
                f"{task_id!r}; available: {[s.step_id for s in states]}"
            )
        step = matches[0]

    node_ids = reader.mesh.node_id_array

    disp_fd = reader.get_field(CanonicalField.DISPLACEMENT, step.step_id)
    stress_fd = reader.get_field(CanonicalField.STRESS_TENSOR, step.step_id)

    bundle = EvidenceBundle(
        bundle_id=bundle_id,
        task_id=task_id,
        title=f"{labels.bundle_title_prefix} {labels.title}",
    )

    section_lines: list[str] = []

    disp_pair = _max_displacement(disp_fd, node_ids)
    if disp_pair is not None:
        # disp_fd cannot be None here — _max_displacement returns None
        # for missing fields, so a non-None pair implies a non-None fd.
        assert disp_fd is not None
        max_u, node_u = disp_pair
        # Per-field unit_system (not reader.mesh.unit_system) so that
        # if a future adapter mixes units across fields the evidence
        # still pins each value to its own field's UnitSystem.
        unit_u = _unit_label_for_system(disp_fd.metadata.unit_system, "length")
        ev_u = EvidenceItem(
            evidence_id=labels.disp_evidence_id,
            evidence_type=EvidenceType.SIMULATION,
            title=labels.disp_evidence_title,
            description=None,
            data=SimulationEvidence(
                value=max_u,
                unit=unit_u,
                location=f"node {node_u}",
            ),
            field_metadata=disp_fd.metadata,
            derivation=None,
            source=disp_fd.metadata.source_solver,
            source_file=str(disp_fd.metadata.source_file),
        )
        bundle.add_evidence(ev_u)
        section_lines.append(
            f"- {labels.disp_bullet_label}: **{max_u:.6g} {unit_u}** "
            f"@ node {node_u}  *({labels.disp_evidence_id})*"
        )

    stress_pair = _max_von_mises(stress_fd, node_ids)
    stress_summary: Optional[Tuple[float, str]] = None  # (sigma_max, unit) for W6c.2
    if stress_pair is not None:
        assert stress_fd is not None  # see disp_fd comment above
        max_vm, node_vm = stress_pair
        unit_s = _unit_label_for_system(stress_fd.metadata.unit_system, "stress")
        ev_s = EvidenceItem(
            evidence_id=labels.vm_evidence_id,
            evidence_type=EvidenceType.SIMULATION,
            title=labels.vm_evidence_title,
            description=None,
            data=SimulationEvidence(
                value=max_vm,
                unit=unit_s,
                location=f"node {node_vm}",
            ),
            field_metadata=stress_fd.metadata,
            derivation=None,
            source=stress_fd.metadata.source_solver,
            source_file=str(stress_fd.metadata.source_file),
        )
        bundle.add_evidence(ev_s)
        section_lines.append(
            f"- {labels.vm_bullet_label}: **{max_vm:.6g} {unit_s}** "
            f"@ node {node_vm}  *({labels.vm_evidence_id})*"
        )
        stress_summary = (float(max_vm), unit_s)

    if not section_lines:
        # ADR-012: a section with no cited evidence_ids cannot ship.
        # Refuse rather than emit an uncited placeholder.
        raise ValueError(
            f"solution state {step.step_id!r} of task {task_id!r} exposes "
            "neither DISPLACEMENT nor STRESS_TENSOR; cannot generate a "
            f"{labels.template_id} draft with zero evidence (ADR-012)."
        )

    summary = ReportSection(
        title=labels.section_title,
        level=1,
        content="\n".join(section_lines),
    )
    sections: list[ReportSection] = [summary]

    # W6c.2 — § 许用应力 + § 评定结论. Both kwargs must be provided
    # together; passing only one is a caller bug. The W6c.2 verdict
    # needs both σ_y/σ_u (from material) AND the design code's safety
    # factors (from code) — silently falling through to the legacy
    # 1-section summary on partial input would hide a configuration
    # bug, exactly the silent-acceptance failure mode Codex R1 on
    # PR #100 flagged as MEDIUM.
    if (material is None) != (code is None):
        provided, missing = (
            ("material", "code") if material is not None else ("code", "material")
        )
        raise ValueError(
            f"W6c.2 verdict requires BOTH material+code; got {provided!r} "
            f"without {missing!r}. Pass both, or omit both to fall back "
            f"to the legacy 1-section summary."
        )
    if material is not None and code is not None:
        if stress_summary is None:
            raise ValueError(
                f"material+code were provided but solution state "
                f"{step.step_id!r} of task {task_id!r} exposes no "
                "STRESS_TENSOR; W6c.2 verdict requires σ_max. Drop the "
                "material+code kwargs to fall back to a stress-less "
                "summary, or fix the upstream solver result."
            )
        sigma_max_value, sigma_max_unit = stress_summary
        allowable, verdict, ev_allowable, ev_verdict = (
            _build_allowable_and_verdict_evidence(
                material=material,
                code=code,
                sigma_max_value=sigma_max_value,
                sigma_max_unit=sigma_max_unit,
                sigma_max_evidence_id=labels.vm_evidence_id,
                threshold=threshold,
                temperature_C=temperature_C,
            )
        )
        # Order matters: EV-ALLOWABLE-001 must be appended before EV-VERDICT-001
        # because the verdict's derivation references it (DAG check at append).
        bundle.add_evidence(ev_allowable)
        bundle.add_evidence(ev_verdict)
        sections.append(_build_allowable_section(allowable, sigma_max_unit))
        sections.append(_build_verdict_section(verdict, sigma_max_unit))

    # W6e.2 — § 模型概览. Always emitted (counts come straight from
    # the reader — no user action required). Self-contained: not
    # derived from σ_max or [σ]; the section is upstream context the
    # signing engineer cross-checks against the FE deck. Inserted
    # AFTER the strength / allowable / verdict trio (headlines-first
    # convention, matches W6c.2 / W6d.2) and BEFORE § 边界条件
    # because model topology is deck context that comes before the
    # loading the engineer applied.
    ev_model, model_section = _build_model_overview_evidence_and_section(reader)
    bundle.add_evidence(ev_model)
    sections.append(model_section)

    # W6d.2 — § 边界条件. Optional and self-contained (no derivation
    # link from / to other evidence): the BC list is upstream context,
    # not derived from σ_max or [σ]. ``BCSummaryError`` propagates
    # cleanly so an engineer sees malformed bc.yaml here, not at
    # DOCX render time.
    if bc_yaml_path is not None:
        ev_bc, bc_section = _build_boundary_conditions_evidence_and_section(
            bc_yaml_path
        )
        bundle.add_evidence(ev_bc)
        sections.append(bc_section)

    report = ReportSpec(
        report_id=report_id,
        project_id=project_id,
        title=labels.title,
        template_id=labels.template_id,
        sections=sections,
        generated_at=datetime.utcnow(),
        evidence_bundle_id=bundle.bundle_id,
    )
    return report, bundle


_ALLOWABLE_EVIDENCE_ID: Final[str] = "EV-ALLOWABLE-001"
_VERDICT_EVIDENCE_ID: Final[str] = "EV-VERDICT-001"


_SYMBOL_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


def _format_inputs_substitution(formula: str, inputs: Mapping[str, float]) -> str:
    """Render the substitution line shown in § 许用应力.

    Returns ``"min(sigma_y / 1.5, sigma_u / 3.0) = min(345 / 1.5, 470 / 3.0)"``-style
    by replacing each whole-word symbol present in ``inputs`` with its
    numeric value. Engineers cross-check this against the source clause;
    the renderer must NOT round any input — that's the kind of silent
    loss ADR-012 tries to prevent.

    Whole-word matching matters: a future YAML formula referencing both
    ``sigma_y`` and ``sigma_yield`` must not collapse to the wrong
    substitution. The regex anchors each replacement at word boundaries
    (``\\b``) and the substitution dict is consulted exactly once per
    matched token, so nothing is double-replaced even if a numeric
    value happens to spell another input key.

    Numeric formatting uses ``:g`` to strip trailing zeros — ``345.0``
    renders as ``345`` rather than ``345.0`` so the audit-line stays
    short, but precision is preserved (``2.5`` stays ``2.5``).
    """
    def _sub(match: re.Match[str]) -> str:
        token = match.group(1)
        if token in inputs:
            return f"{inputs[token]:g}"
        return token

    return _SYMBOL_TOKEN_RE.sub(_sub, formula)


def _build_allowable_and_verdict_evidence(
    material: Material,
    code: CodeStandard,
    sigma_max_value: float,
    sigma_max_unit: str,
    sigma_max_evidence_id: str,
    threshold: float,
    temperature_C: float,
) -> Tuple[AllowableStress, Verdict, EvidenceItem, EvidenceItem]:
    """Compute [σ] + verdict and mint the two AnalyticalEvidence items.

    Stitches together W6b (allowable_stress) + W6c (verdict). Neither
    library knows about ``EvidenceItem``; this helper is the boundary
    that turns their numeric outputs into bundle-ready evidence with
    the DAG link ``EV-VERDICT-001 → [<sigma_max evidence>, EV-ALLOWABLE-001]``.

    The helper does NOT touch the bundle — the caller adds the items
    in the correct order so the bundle's append-time DAG check
    sees ``EV-ALLOWABLE-001`` before ``EV-VERDICT-001``.

    The ``EvidenceItem.source`` for both items is set to the verbatim
    clause citation from :class:`AllowableStress` — the auditor reading
    the bundle JSON sees the standard's clause directly without
    having to follow ``data.formula`` back to the YAML.
    """
    allowable = compute_allowable_stress(material, code, temperature_C=temperature_C)
    verdict = compute_verdict(
        sigma_max=sigma_max_value,
        sigma_allow=allowable.sigma_allow,
        threshold=threshold,
    )
    source_label = allowable.code_clause

    # AnalyticalEvidence.inputs is Dict[str, float]; AllowableStress.inputs
    # is a MappingProxyType. Copy explicitly — pydantic's validator coerces
    # values, but we want the keys preserved verbatim.
    allowable_inputs: dict[str, float] = {k: float(v) for k, v in allowable.inputs.items()}
    ev_allowable = EvidenceItem(
        evidence_id=_ALLOWABLE_EVIDENCE_ID,
        evidence_type=EvidenceType.ANALYTICAL,
        title="许用应力 [σ] (per design code)",
        description=(
            f"{code} simplified room-temperature allowable stress, "
            f"{allowable.code_clause}"
        ),
        data=AnalyticalEvidence(
            value=float(allowable.sigma_allow),
            unit=sigma_max_unit,
            formula=allowable.formula_used,
            inputs=allowable_inputs,
        ),
        derivation=None,
        source=source_label,
        source_file=None,
    )

    # The verdict depends on BOTH the simulation σ_max and the allowable —
    # an honest derivation DAG, per ADR-012. Without this link the
    # auditor can't trace the SF back to the two numbers it came from.
    verdict_inputs: dict[str, float] = {k: float(v) for k, v in verdict.inputs}
    ev_verdict = EvidenceItem(
        evidence_id=_VERDICT_EVIDENCE_ID,
        evidence_type=EvidenceType.ANALYTICAL,
        title="结构强度评定 (PASS/FAIL verdict)",
        description=(
            f"SF = [σ] / σ_max = {verdict.safety_factor:.4g}; "
            f"threshold = {threshold:g}; verdict = {verdict.kind}"
        ),
        data=AnalyticalEvidence(
            value=float(verdict.safety_factor),
            unit="dimensionless",
            formula="SF = sigma_allow / sigma_max",
            inputs=verdict_inputs,
        ),
        derivation=[sigma_max_evidence_id, _ALLOWABLE_EVIDENCE_ID],
        source=source_label,
        source_file=None,
    )

    return allowable, verdict, ev_allowable, ev_verdict


def _build_allowable_section(
    allowable: AllowableStress, sigma_max_unit: str
) -> ReportSection:
    """Render the § 许用应力 section content per ADR-020 §5.

    Two lines: (1) substitution showing the formula evaluated with the
    actual σ_y / σ_u from the Material, and (2) the clause citation as
    a footnote. The DOCX template (W6c.2 in the wider sense) will pick
    up this section and embed both lines verbatim.

    The subscript notation matches the engineer-facing convention used
    throughout the wedge (σ_y, σ_u, [σ]) — consistent with the §
    materials section the W6a path already emits.
    """
    substitution = _format_inputs_substitution(allowable.formula_used, allowable.inputs)
    lines: list[str] = [
        f"- 许用应力公式: **{allowable.formula_used}**",
        f"- 代入: {substitution} = **{allowable.sigma_allow:.6g} {sigma_max_unit}**",
        f"- 引用条款: *{allowable.code_clause}*  *({_ALLOWABLE_EVIDENCE_ID})*",
    ]
    if allowable.is_simplified:
        lines.append(
            "- 注: 本计算依据简化算式（常温），未应用焊缝系数 E_j；"
            "工程师须在评定结论中显式说明 E_j 取值。"
        )
    return ReportSection(
        title="许用应力 (Allowable stress)",
        level=2,
        content="\n".join(lines),
    )


def _build_verdict_section(
    verdict: Verdict, sigma_max_unit: str
) -> ReportSection:
    """Render the § 评定结论 section content per RFC-001 §2 W6c.

    句式 (per the W6 roadmap):

      σ_max = {x:.6g} {unit} ≤ [σ] = {y:.6g} {unit},
      SF = {sf:.4g} ≥ threshold = {t:g} → 强度满足要求 (PASS)

    The PASS/FAIL string is **deterministic** — RFC-001 §2.4 rule 1
    forbids the LLM from generating verdict numbers, and rule 4
    requires a "[需工程师确认]" flag when an LLM rephrases the line.
    """
    inputs_dict = dict(verdict.inputs)
    sigma_max_value = inputs_dict["sigma_max"]
    sigma_allow_value = inputs_dict["sigma_allow"]
    threshold_value = inputs_dict["threshold"]

    # Pick relations from the actual numbers, not from kind. With
    # threshold=1.5, a FAIL can occur even when σ_max ≤ [σ] (e.g.
    # SF=1.2 < 1.5). Hard-coding ">" / "<" by kind would render a
    # factually wrong inequality in that case — exactly the kind of
    # silent untruth ADR-012 forbids in audit-trail content.
    if sigma_max_value < sigma_allow_value:
        relation = "<"
    elif sigma_max_value > sigma_allow_value:
        relation = ">"
    else:
        relation = "="
    if verdict.safety_factor > threshold_value:
        sf_relation = ">"
    elif verdict.safety_factor < threshold_value:
        sf_relation = "<"
    else:
        sf_relation = "="

    if verdict.kind == "PASS":
        verdict_text_zh = "强度满足要求"
        verdict_text_en = "PASS"
    else:
        verdict_text_zh = "强度不满足要求"
        verdict_text_en = "FAIL"

    sentence = (
        f"σ_max = {sigma_max_value:.6g} {sigma_max_unit} "
        f"{relation} [σ] = {sigma_allow_value:.6g} {sigma_max_unit}, "
        f"SF = {verdict.safety_factor:.4g} "
        f"{sf_relation} threshold = {threshold_value:g} "
        f"→ **{verdict_text_zh} ({verdict_text_en})**"
    )
    margin_line = (
        f"裕度 (margin) = {verdict.margin_pct:+.2f}%  "
        f"(safety_factor / threshold − 1)"
    )
    return ReportSection(
        title="评定结论 (Strength verdict)",
        level=2,
        content="\n".join(
            [
                f"- {sentence}  *({_VERDICT_EVIDENCE_ID})*",
                f"- {margin_line}",
            ]
        ),
    )


_MODEL_OVERVIEW_EVIDENCE_ID: Final[str] = "EV-MODEL-OVERVIEW-001"
_BC_EVIDENCE_ID: Final[str] = "EV-BC-001"


def _build_model_overview_evidence_and_section(
    reader: ReaderHandle,
) -> Tuple[EvidenceItem, ReportSection]:
    """Summarize mesh-level statistics and emit the § 模型概览 pair.

    Returns ``(evidence_item, section)`` ready for the caller to
    append in DAG-safe order (model overview is leaf — it has no
    derivation link to or from other evidence; the table is upstream
    context the engineer cross-checks against the FE deck).

    The evidence is a single ``ReferenceEvidence`` whose ``value`` is
    the total element count (or 0 when the adapter does not declare
    the W6e capability) and whose ``citation_anchor`` carries the
    canonical "node count + element count" string. Per-type detail
    lives in the section content; the evidence carries the audit
    pointer back to the solver result file.

    When the adapter does not declare ``SupportsElementInventory``,
    or declares it but reports ``None`` (e.g. CalculiX FRD with no
    -3 block — Codex R1 HIGH on PR #109's three-state contract),
    the section renders the "无单元清单 [需工程师确认]" placeholder.
    The evidence is still emitted so the auditor sees that the
    pipeline TRIED to populate the section rather than that the
    section was forgotten.
    """
    overview = summarize_model(reader)

    # Codex R2 LOW on PR #110: keep the human-readable ``description``
    # symmetric with ``citation_anchor`` so a UI / log that surfaces
    # description verbatim doesn't leak the synthetic ``elements=0``
    # sentinel from the unavailable branch.
    elements_text = (
        str(overview.total_elements) if overview.has_inventory else "unknown"
    )
    description = (
        f"Reader-derived mesh statistics: nodes={overview.total_nodes}, "
        f"elements={elements_text}, "
        f"has_inventory={overview.has_inventory}"
    )

    # ADR-003 (do-not-fabricate) — Codex R1 HIGH on PR #110:
    # when ``has_inventory`` is False the element count is unknown, not
    # zero. The library encodes the unknown state as ``total_elements=0``
    # but that 0 must not leak into a downstream consumer's evidence
    # payload. Anchor the evidence to the always-known node count
    # (Mesh Protocol guarantees node coordinates) and spell the missing
    # element count out as text in the citation_anchor.
    if overview.has_inventory:
        ev_value = float(overview.total_elements)
        ev_unit = "elements"
        anchor = (
            f"nodes={overview.total_nodes}, "
            f"elements={overview.total_elements}"
        )
    else:
        ev_value = float(overview.total_nodes)
        ev_unit = "nodes"
        anchor = (
            f"nodes={overview.total_nodes}, "
            f"elements=unknown (inventory unavailable)"
        )

    ev = EvidenceItem(
        evidence_id=_MODEL_OVERVIEW_EVIDENCE_ID,
        evidence_type=EvidenceType.REFERENCE,
        title="模型概览 (model overview)",
        description=description,
        data=ReferenceEvidence(
            value=ev_value,
            unit=ev_unit,
            source_document="solver result file",
            citation_anchor=anchor,
        ),
        derivation=None,
        source="reader.mesh + SupportsElementInventory",
        source_file=None,
    )

    section = _build_model_overview_section(overview)
    return ev, section


def _build_model_overview_section(overview: ModelOverview) -> ReportSection:
    """Render the § 模型概览 section content.

    Layout when inventory is available:

    1. Summary line: ``节点数 / 单元数 N (按类型: 四面体 X, 壳 Y, ...)``.
    2. One bullet per group label, sorted by count descending so the
       dominant element family is visible first.
    3. Citation footer: ``({_MODEL_OVERVIEW_EVIDENCE_ID})``.

    When inventory is unavailable (capability absent or returned
    ``None``), a single ``[需工程师确认] 无单元清单...`` line is
    emitted instead of the breakdown, and the engineer signing the
    DOCX must explicitly confirm the FE topology matches the model
    they ran.
    """
    lines: list[str] = []

    if not overview.has_inventory:
        lines.append(
            f"- 节点数 / Total nodes: **{overview.total_nodes}**  "
            f"*({_MODEL_OVERVIEW_EVIDENCE_ID})*"
        )
        lines.append(
            "- **[需工程师确认]** 无单元清单数据 — adapter does not "
            "expose SupportsElementInventory (or reported the "
            "underlying file did not include element data)."
        )
        return ReportSection(
            title="模型概览 (Model overview)",
            level=1,
            content="\n".join(lines),
        )

    lines.append(
        f"- 节点数 / Total nodes: **{overview.total_nodes}**  "
        f"*({_MODEL_OVERVIEW_EVIDENCE_ID})*"
    )
    lines.append(
        f"- 单元数 / Total elements: **{overview.total_elements}**  "
        f"*({_MODEL_OVERVIEW_EVIDENCE_ID})*"
    )

    if overview.total_elements == 0:
        # Capable adapter that confirmed zero elements — degenerate
        # but valid (e.g. node-only mesh used for coordinate-frame
        # checks). Distinguish from the "inventory unknown" branch
        # above by NOT showing the [需工程师确认] flag.
        return ReportSection(
            title="模型概览 (Model overview)",
            level=1,
            content="\n".join(lines),
        )

    # Sort by count descending so the dominant family leads. Ties
    # break by group-label sort order (already stable from
    # ``summarize_model``).
    sorted_groups = sorted(
        overview.group_counts.items(), key=lambda kv: (-kv[1], kv[0])
    )
    group_summary = ", ".join(f"{g}: {c}" for g, c in sorted_groups)
    lines.append(
        f"- 按类型分布 / Distribution by family: {group_summary}  "
        f"*({_MODEL_OVERVIEW_EVIDENCE_ID})*"
    )

    # If anything fell into GROUP_OTHER, surface the underlying
    # solver-native types so the engineer can decide whether to
    # extend ``ELEMENT_TYPE_GROUPS`` (W6e library) — silent bucketing
    # of unfamiliar types into "其他" would mask a real category
    # error in the FE deck.
    if GROUP_OTHER in overview.group_counts:
        other_types = sorted(
            t
            for t in overview.type_counts
            if ELEMENT_TYPE_GROUPS.get(t, GROUP_OTHER) == GROUP_OTHER
        )
        if other_types:
            lines.append(
                f"- ℹ 其他 / GROUP_OTHER includes solver-native types: "
                f"{', '.join(other_types)}  "
                f"*({_MODEL_OVERVIEW_EVIDENCE_ID})*"
            )

    return ReportSection(
        title="模型概览 (Model overview)",
        level=1,
        content="\n".join(lines),
    )


def _build_boundary_conditions_evidence_and_section(
    bc_yaml_path: Path,
) -> Tuple[EvidenceItem, ReportSection]:
    """Load ``bc.yaml``, summarise, and emit the § 边界条件 pair.

    Returns ``(evidence_item, section)`` ready for the caller to append
    in DAG-safe order. The evidence is a single ``ReferenceEvidence``
    pointing at the source file (the BC list is *user-supplied*, not
    derived from the simulation result), with ``value`` = number of
    BCs and ``unit`` = ``"conditions"``. Per-BC detail lives in the
    section content; the evidence carries the audit pointer back to
    the source ``bc.yaml``.

    Empty BC list (engineer uploaded an empty / placeholder file) is
    NOT silently skipped — the section is rendered with a
    ``[需工程师确认]`` placeholder line and the evidence still cites
    the empty source so the auditor sees that "an engineer touched
    this file" rather than "the wedge forgot the BCs".
    """
    bcs = load_boundary_conditions_yaml(bc_yaml_path)
    summary = summarize_boundary_conditions(bcs)

    ev = EvidenceItem(
        evidence_id=_BC_EVIDENCE_ID,
        evidence_type=EvidenceType.REFERENCE,
        title="边界条件清单 (boundary conditions)",
        description=(
            f"User-supplied bc.yaml: {len(bcs)} boundary condition(s); "
            f"unit systems: {', '.join(summary.unit_systems) or 'n/a'}"
        ),
        data=ReferenceEvidence(
            value=float(len(bcs)),
            unit="conditions",
            source_document=str(bc_yaml_path),
            citation_anchor="boundary_conditions[*]",
        ),
        derivation=None,
        source="user-supplied bc.yaml",
        source_file=str(bc_yaml_path),
    )

    section = _build_boundary_section(summary, bc_yaml_path)
    return ev, section


def _build_boundary_section(
    summary: BCSummary, source_path: Path
) -> ReportSection:
    """Render the § 边界条件 section content.

    Layout:

    1. Summary line: ``共 N 项 (固定: 2, 压力: 1)`` + warning if mixed.
    2. One bullet per BC: ``编号. 名称 (类型) @ 位置 — 分量 [单位]``.
    3. Citation footer: ``({_BC_EVIDENCE_ID})``.

    For empty input, a single ``[需工程师确认] 未提供边界条件...``
    line is emitted — the engineer signing the DOCX must see that
    the BCs were not captured rather than discover it during
    technical review.

    Mixed unit systems trigger an inline warning line — almost always
    a wizard bug; better to surface it at sign time than at audit time.
    """
    lines: list[str] = []

    if not summary.rows:
        lines.append(
            f"- **[需工程师确认]** 未提供边界条件数据 (bc.yaml at "
            f"{source_path!s} loaded zero entries)."
        )
        lines.append(f"  *({_BC_EVIDENCE_ID})*")
        return ReportSection(
            title="边界条件 (Boundary conditions)",
            level=1,
            content="\n".join(lines),
        )

    counts = dict(summary.counts_by_kind)
    total = sum(counts.values())
    counts_str = ", ".join(f"{k}: {v}" for k, v in counts.items())
    lines.append(
        f"- 共 **{total}** 项边界条件 ({counts_str})  *({_BC_EVIDENCE_ID})*"
    )

    if len(summary.unit_systems) > 1:
        lines.append(
            f"- ⚠ **混合单位系统** ({', '.join(summary.unit_systems)}) — "
            f"请工程师核对 bc.yaml 是否一致。"
        )

    for i, row in enumerate(summary.rows, start=1):
        lines.append(
            f"- {i}. **{row['name']}** ({row['kind']}) @ {row['target']} — "
            f"{row['components']} [{row['unit_system']}]"
        )

    return ReportSection(
        title="边界条件 (Boundary conditions)",
        level=1,
        content="\n".join(lines),
    )


def _override_labels(
    base: _SummaryLabels,
    template_id: Optional[str],
    title: Optional[str],
) -> _SummaryLabels:
    """Return ``base`` with optional ``template_id`` / ``title`` fields
    replaced. Either being ``None`` means "use the template default".

    Note: overriding ``template_id`` here produces a report whose
    section title and bullet labels are still keyed to ``base`` — i.e.
    the override is structural-id only, not full re-skinning. Callers
    using this for a custom template are responsible for confirming
    the section structure still matches that template's contract.
    """
    if template_id is None and title is None:
        return base
    overrides: dict[str, str] = {}
    if template_id is not None:
        overrides["template_id"] = template_id
    if title is not None:
        overrides["title"] = title
    return replace(base, **overrides)


def generate_static_strength_summary(
    reader: ReaderHandle,
    *,
    project_id: str,
    task_id: str,
    report_id: str,
    bundle_id: str,
    step_id: Optional[int] = None,
    template_id: Optional[str] = None,
    title: Optional[str] = None,
    material: Optional[Material] = None,
    code: Optional[CodeStandard] = None,
    threshold: float = DEFAULT_THRESHOLD,
    temperature_C: float = 20.0,
    bc_yaml_path: Optional[Path] = None,
) -> Tuple[ReportSpec, EvidenceBundle]:
    """Generate the minimum-viable static-strength report draft.

    Returns ``(report, bundle)`` such that every section in ``report``
    references at least one ``evidence_id`` that resolves inside
    ``bundle`` (ADR-012 invariant). The caller persists / exports
    these together; the exporter refuses to emit DOCX for any draft
    whose evidence references don't resolve.

    ``step_id`` selects which solution state to summarise. When
    ``None`` the *final* state is used (``solution_states[-1]``) — for
    static analyses this matches the converged result; the choice is
    deliberate, never silent. Pass ``step_id`` explicitly for
    multi-step / transient cases.

    ``template_id`` and ``title`` override the equipment-foundation
    defaults for callers that need a custom template_id or report
    title (e.g. a project-specific subclassing of the static-strength
    report). The section structure and evidence labels still come from
    the equipment-foundation template — overriding template_id alone
    will fail :func:`templates.validate_report` against any registered
    template_id other than ``equipment_foundation_static``.

    ``material`` + ``code`` opt the report into the W6c.2 strength
    verdict: when both are provided, the draft additionally renders
    § 许用应力 + § 评定结论 sections backed by ``EV-ALLOWABLE-001`` +
    ``EV-VERDICT-001`` analytical evidence (per ADR-020 / RFC-001 W6c).
    The verdict's ``derivation`` lists ``EV-VM-MAX`` + ``EV-ALLOWABLE-001``
    so the bundle DAG honestly shows the SF traces back to both the
    simulation σ_max and the standards-derived [σ]. ``threshold`` and
    ``temperature_C`` follow the W6b/W6c defaults (1.0 = regulatory
    floor; 20°C = room temperature within the simplified-formula
    validity window).

    Raises ``ValueError`` when the chosen state exposes neither
    ``DISPLACEMENT`` nor ``STRESS_TENSOR`` — emitting a section with no
    cited evidence would violate ADR-012. Also raises ``ValueError``
    when ``material+code`` are provided but the chosen state has no
    ``STRESS_TENSOR`` (the verdict needs σ_max).
    """
    labels = _override_labels(_EQUIPMENT_FOUNDATION_LABELS, template_id, title)
    return _build_max_field_summary(
        reader,
        labels,
        project_id=project_id,
        task_id=task_id,
        report_id=report_id,
        bundle_id=bundle_id,
        step_id=step_id,
        material=material,
        code=code,
        threshold=threshold,
        temperature_C=temperature_C,
        bc_yaml_path=bc_yaml_path,
    )


def generate_lifting_lug_summary(
    reader: ReaderHandle,
    *,
    project_id: str,
    task_id: str,
    report_id: str,
    bundle_id: str,
    step_id: Optional[int] = None,
    template_id: Optional[str] = None,
    title: Optional[str] = None,
    material: Optional[Material] = None,
    code: Optional[CodeStandard] = None,
    threshold: float = DEFAULT_THRESHOLD,
    temperature_C: float = 20.0,
    bc_yaml_path: Optional[Path] = None,
) -> Tuple[ReportSpec, EvidenceBundle]:
    """Generate a lifting-lug strength-assessment report draft.

    Same Layer-1→Layer-3 numerical work as
    :func:`generate_static_strength_summary` (max ||u||, max σ_vm) but
    branded for the ``lifting_lug`` template. The engineer is expected
    to have run the FE model under the hoisting load case (typically
    2× service per GB 50017 §11) — the generator does NOT scale loads;
    it reports what's in the result file.

    Region selection (lug-shell weld vs. whole model) is not yet
    available at Layer 2/3; until it is, the engineer must verify the
    reported max-σ_vm node lies within the lug region. RFC-002
    candidate: a region-aware reader / domain helper in W5+.

    ``template_id`` and ``title`` provide the same opt-in override as
    :func:`generate_static_strength_summary`; see its docstring for
    the structure-vs-id caveat.
    """
    labels = _override_labels(_LIFTING_LUG_LABELS, template_id, title)
    return _build_max_field_summary(
        reader,
        labels,
        project_id=project_id,
        task_id=task_id,
        report_id=report_id,
        bundle_id=bundle_id,
        step_id=step_id,
        material=material,
        code=code,
        threshold=threshold,
        temperature_C=temperature_C,
        bc_yaml_path=bc_yaml_path,
    )


# --- pressure-vessel local stress (ASME VIII Div 2 §5.5) -----------------


def generate_pressure_vessel_local_stress_summary(
    reader: ReaderHandle,
    *,
    project_id: str,
    task_id: str,
    report_id: str,
    bundle_id: str,
    scl_node_ids: _IntArrayLike,
    scl_distances: _FloatArrayLike,
    step_id: Optional[int] = None,
    template_id: Optional[str] = None,
    title: Optional[str] = None,
    resample_n_points: Optional[int] = None,
) -> Tuple[ReportSpec, EvidenceBundle]:
    """Generate a pressure-vessel local-stress assessment report draft.

    Operates on a Stress Classification Line (SCL) — a line through
    the wall thickness from inner surface to outer surface. The
    engineer identifies the SCL by its node IDs (in inner→outer order)
    and the per-node distances along the line. Both must be supplied;
    the producer does not auto-detect SCL geometry.

    Reports three categorised stresses per ASME VIII Div 2 §5.5.3:

      * **EV-PM**: P_m = von_mises(membrane). The through-thickness-
        averaged stress.
      * **EV-PM-PB**: max(von_mises(σ at outer surface),
        von_mises(σ at inner surface)) where σ_outer = membrane +
        bending_outer, σ_inner = membrane - bending_outer.
      * **EV-MAX-VM-SCL**: max von_mises(σ(s)) along the SCL — the
        worst-case **total** stress, ``P_m + P_b + Q + F``. The MVP
        does not split Q (secondary) from F (peak) because the
        Layer-3 linearizer's ``peak`` field carries the combined
        ``Q + F`` residual; honest labelling reflects this. RFC-002
        candidate: a Q/F split decomposition.

    Inputs
    ------
    scl_node_ids:
        Integer node IDs on the SCL, ORDERED from inner surface to
        outer surface. Accepts plain ``Sequence[int]`` or a NumPy
        integer array (per the typed alias ``_IntArrayLike``).
    scl_distances:
        Per-node distances along the SCL (typically from the inner
        surface). When ``resample_n_points`` is left as ``None``
        (default), distances must be uniformly spaced (the Layer-3
        linearizer rejects non-uniform). When ``resample_n_points``
        is set, the distances may be any strictly-monotonic series
        — they will be resampled before linearization.
    resample_n_points:
        If set, run the raw SCL tensor field through
        :func:`app.domain.stress_linearization.resample_to_uniform`
        with this many output points before linearizing. Lets the
        engineer hand the producer non-uniform CalculiX node spacing
        without the manual pre-step. Must be ≥ 2; project default is
        21 if you want a sensible value. ``None`` (default) preserves
        the strict uniform-spacing contract.

        Note: the EV-MAX-VM-SCL evidence (max von Mises along SCL)
        is computed from the *raw* per-physical-node tensors even
        when resampling is on, so the "max stress at node X" label
        keeps pointing at a real mesh node. Resampling only feeds
        the linearizer's M/B/Q decomposition.

    Caveats
    -------
    Region selection (which SCL is the worst case) is the engineer's
    responsibility — the producer does not search for a
    worst-location SCL. Future Layer-3 work (RFC-002 candidate)
    could automate that.

    Raises
    ------
    ValueError
        On length mismatch between node_ids and distances, fewer
        than 2 SCL nodes, missing STRESS_TENSOR field, unknown
        node IDs, non-NODE-located stress field, or non-uniform
        SCL spacing (raised by the Layer-3 linearizer).
    """
    template_id_resolved = template_id or "pressure_vessel_local_stress"
    title_resolved = title or "Pressure-vessel local-stress assessment"

    if len(scl_node_ids) != len(scl_distances):
        raise ValueError(
            f"scl_node_ids length {len(scl_node_ids)} != "
            f"scl_distances length {len(scl_distances)}"
        )
    if len(scl_node_ids) < 2:
        raise ValueError(
            f"SCL requires at least 2 nodes; got {len(scl_node_ids)}"
        )

    states = reader.solution_states
    if not states:
        raise ValueError(
            f"reader for task {task_id!r} has no solution states; "
            "nothing to summarise"
        )
    if step_id is None:
        step = states[-1]
    else:
        matches = [s for s in states if s.step_id == step_id]
        if not matches:
            raise ValueError(
                f"step_id={step_id!r} not present in reader for task "
                f"{task_id!r}; available: {[s.step_id for s in states]}"
            )
        step = matches[0]

    stress_fd = reader.get_field(CanonicalField.STRESS_TENSOR, step.step_id)
    if stress_fd is None:
        raise ValueError(
            f"solution state {step.step_id!r} has no STRESS_TENSOR "
            "field; cannot perform local-stress assessment."
        )
    _require_node_location(stress_fd, "stress-tensor")

    all_tensors = stress_fd.values()  # shape (N_total, 6)
    node_index = reader.mesh.node_index
    try:
        scl_indices = [node_index[int(nid)] for nid in scl_node_ids]
    except KeyError as exc:
        raise ValueError(
            f"SCL node id {exc.args[0]!r} not present in reader's mesh."
        ) from None
    scl_tensors = np.asarray(all_tensors[scl_indices], dtype=np.float64)
    distances_arr = np.asarray(scl_distances, dtype=np.float64)

    # Optional pre-pass: resample non-uniform inputs onto a uniform
    # grid before linearization. We feed only the linearizer the
    # resampled field; max-VM along SCL keeps using the raw
    # per-node tensors so the EV-MAX-VM-SCL evidence's "node X"
    # label still points at a real mesh node.
    if resample_n_points is not None:
        tensors_for_lin, distances_for_lin = resample_to_uniform(
            scl_tensors, distances_arr, n_points=resample_n_points
        )
    else:
        tensors_for_lin, distances_for_lin = scl_tensors, distances_arr

    # Layer-3 linearization. Raises ValueError on non-uniform spacing
    # or other shape problems — when resample_n_points is None the
    # caller is responsible for uniform input.
    decomposition = linearize_through_thickness(
        tensors_for_lin, distances_for_lin
    )

    # Categorised stresses.
    p_m = float(von_mises(decomposition.membrane.reshape(1, 6))[0])
    sigma_outer = (decomposition.membrane + decomposition.bending_outer).reshape(1, 6)
    sigma_inner = (decomposition.membrane - decomposition.bending_outer).reshape(1, 6)
    p_m_plus_p_b = float(
        max(
            von_mises(sigma_outer)[0],
            von_mises(sigma_inner)[0],
        )
    )
    # Total stress along SCL: max von_mises(σ(s)) = max(P_m + P_b + Q + F)
    # (we do NOT split Q from F at MVP — see EV-MAX-VM-SCL note).
    max_vm_per_point = von_mises(scl_tensors)
    max_vm_idx = int(np.argmax(max_vm_per_point))
    max_vm = float(max_vm_per_point[max_vm_idx])
    max_vm_node = int(scl_node_ids[max_vm_idx])

    unit_s = _unit_label_for_system(stress_fd.metadata.unit_system, "stress")

    bundle = EvidenceBundle(
        bundle_id=bundle_id,
        task_id=task_id,
        title=f"Evidence backing {title_resolved}",
    )

    inner_node = int(scl_node_ids[0])
    outer_node = int(scl_node_ids[-1])
    scl_location_label = (
        f"SCL nodes [{inner_node} → {outer_node}], "
        f"{len(scl_node_ids)} samples"
    )

    bundle.add_evidence(
        EvidenceItem(
            evidence_id="EV-PM",
            evidence_type=EvidenceType.SIMULATION,
            title="Primary membrane stress P_m",
            description=None,
            data=SimulationEvidence(
                value=p_m,
                unit=unit_s,
                location=scl_location_label,
            ),
            field_metadata=stress_fd.metadata,
            derivation=None,
            source=stress_fd.metadata.source_solver,
            source_file=str(stress_fd.metadata.source_file),
        )
    )
    bundle.add_evidence(
        EvidenceItem(
            evidence_id="EV-PM-PB",
            evidence_type=EvidenceType.SIMULATION,
            title="Maximum primary membrane + bending stress (P_m + P_b)",
            description=None,
            data=SimulationEvidence(
                value=p_m_plus_p_b,
                unit=unit_s,
                location=f"{scl_location_label}, surface max",
            ),
            field_metadata=stress_fd.metadata,
            derivation=["EV-PM"],
            source=stress_fd.metadata.source_solver,
            source_file=str(stress_fd.metadata.source_file),
        )
    )
    bundle.add_evidence(
        EvidenceItem(
            evidence_id="EV-MAX-VM-SCL",
            evidence_type=EvidenceType.SIMULATION,
            title=(
                "Maximum total stress along SCL (P_m + P_b + Q + F; "
                "Q/F not split at MVP)"
            ),
            description=None,
            data=SimulationEvidence(
                value=max_vm,
                unit=unit_s,
                location=f"node {max_vm_node} (along SCL)",
            ),
            field_metadata=stress_fd.metadata,
            derivation=["EV-PM-PB"],
            source=stress_fd.metadata.source_solver,
            source_file=str(stress_fd.metadata.source_file),
        )
    )

    section_lines = [
        f"- 薄膜应力 P_m: **{p_m:.6g} {unit_s}**  *(EV-PM)*",
        (
            f"- 膜+弯应力 P_m + P_b (表面最大): "
            f"**{p_m_plus_p_b:.6g} {unit_s}**  *(EV-PM-PB)*"
        ),
        (
            f"- SCL沿线总应力最大值 P_m + P_b + Q + F (Q/F 未拆分): "
            f"**{max_vm:.6g} {unit_s}** "
            f"@ node {max_vm_node}  *(EV-MAX-VM-SCL)*"
        ),
    ]

    summary = ReportSection(
        title="局部应力评估 (Local stress assessment)",
        level=1,
        content="\n".join(section_lines),
    )

    report = ReportSpec(
        report_id=report_id,
        project_id=project_id,
        title=title_resolved,
        template_id=template_id_resolved,
        sections=[summary],
        generated_at=datetime.utcnow(),
        evidence_bundle_id=bundle.bundle_id,
    )
    return report, bundle


# --- ballistic-penetration time-history (W7f) ----------------------------


def _unit_label_for_time(system: UnitSystem) -> str:
    """Time unit per ``UnitSystem`` (closed-set). ``UNKNOWN`` returns
    ``'unknown'`` rather than guessing — the wizard pins this before
    draft generation, so seeing ``unknown`` flags an upstream contract leak.
    """
    table: dict[UnitSystem, str] = {
        UnitSystem.SI: "s",
        UnitSystem.SI_MM: "ms",
        UnitSystem.ENGLISH: "s",
        UnitSystem.UNKNOWN: "unknown",
    }
    return table[system]


def generate_ballistic_penetration_summary(
    reader: ReaderHandle,
    *,
    project_id: str,
    task_id: str,
    report_id: str,
    bundle_id: str,
    template_id: Optional[str] = None,
    title: Optional[str] = None,
) -> Tuple[ReportSpec, EvidenceBundle]:
    """Generate the ``ballistic_penetration_summary`` report draft.

    Wires the Layer-1 ``ReaderHandle`` (typically OpenRadioss) through
    the Layer-3 ``app.domain.ballistics`` derivations and emits a
    single-section report whose evidence items capture:

      * ``EV-BALLISTIC-DURATION`` — total run time (final state's
        ``time``).
      * ``EV-BALLISTIC-MAX-DISP`` — peak nodal displacement magnitude
        across all states, with the step at which it occurred.
      * ``EV-BALLISTIC-EROSION-FINAL`` — eroded facet count at the
        final state. Emitted ONLY when the reader satisfies
        ``SupportsElementDeletion`` (CalculiX has no erosion; this
        evidence item is silently absent for it). The value is the
        raw count, including 0 (a "0 eroded" outcome is non-trivial
        evidence — it means the design survived the load case).
      * ``EV-BALLISTIC-PERFORATION-EVENT`` — step_id at which the
        first facet eroded. Emitted ONLY when the reader supports
        erosion AND erosion was actually observed in the run. If no
        erosion happened, the section text records "未观察到穿透 / no
        perforation observed" without minting an evidence item (a
        non-event isn't citeable per ADR-012).

    Multi-state contract: unlike the static-strength generators, this
    reader iterates EVERY ``solution_state`` to find the peak
    displacement and the perforation step. ``step_id`` is therefore
    NOT a parameter — the whole time history is the report subject.

    ADR-001 / ADR-003 / ADR-012:
      * Every per-state quantity comes from Layer 3 (``app.domain.ballistics``);
        no derivation in this Layer-4 module.
      * The unit_system flows from each evidence item's ``FieldMetadata``
        (or the reader's ``mesh.unit_system`` for time, since the time
        axis isn't part of any FieldMetadata yet — a known gap).
      * Every evidence item carries a resolved ``evidence_id`` and the
        section content cites at least 2 distinct ``EV-*`` tokens (the
        template requires ``minimum_evidence_citations=2``).

    ``template_id`` / ``title`` overrides match the static-strength
    generators' opt-in pattern.
    """
    template_id_resolved = template_id or "ballistic_penetration_summary"
    title_resolved = (
        title or "Ballistic-penetration time-history summary"
    )

    states = reader.solution_states
    if not states:
        raise ValueError(
            f"reader for task {task_id!r} has no solution states; "
            "cannot generate a ballistic-penetration summary"
        )

    step_ids = [s.step_id for s in states]
    state_lookup = {s.step_id: s for s in states}

    disp_by_step = displacement_history(reader, step_ids)
    has_erosion = isinstance(reader, SupportsElementDeletion)
    erosion_by_step: dict[int, int] = (
        eroded_history(reader, step_ids) if has_erosion else {}
    )
    perforation_step = (
        perforation_event_step(reader, step_ids) if has_erosion else None
    )

    # Peak displacement across the whole time axis.
    peak_step_id = max(disp_by_step, key=lambda sid: disp_by_step[sid])
    peak_disp_value = float(disp_by_step[peak_step_id])

    # Codex R1 HIGH: each evidence item must bind to its OWN step's
    # FieldMetadata so source_file in the audit trail points to the
    # actual file the value came from — earlier code reused
    # peak_field metadata for duration / final-erosion / perforation
    # evidence, which produced the wrong .Axxx path when peak
    # displacement and the final state were different frames. We pull
    # one DISPLACEMENT field per relevant step (ADR-021 makes
    # DISPLACEMENT universal across OpenRadioss frames; for adapters
    # that some day gate it, the contract failure surfaces here as a
    # clear ValueError, not a silent metadata leak).
    def _field_at(step_id: int) -> FieldData:
        fd = reader.get_field(CanonicalField.DISPLACEMENT, step_id)
        if fd is None:
            raise ValueError(
                f"reader has no DISPLACEMENT at step {step_id!r}; "
                "ballistic summary requires per-step displacement "
                "evidence for the audit trail (ADR-012)"
            )
        return fd

    peak_field = _field_at(peak_step_id)

    final_state = state_lookup[step_ids[-1]]
    final_field = _field_at(final_state.step_id)
    final_time = (
        float(final_state.time) if final_state.time is not None else 0.0
    )
    time_unit = _unit_label_for_time(reader.mesh.unit_system)
    length_unit = _unit_label_for_system(
        peak_field.metadata.unit_system, "length"
    )

    bundle = EvidenceBundle(
        bundle_id=bundle_id,
        task_id=task_id,
        title=f"Evidence backing {title_resolved}",
    )

    section_lines: list[str] = []

    # 1) Run duration — bind to the FINAL state's metadata since that
    # is the file the ``time`` value originated from.
    bundle.add_evidence(
        EvidenceItem(
            evidence_id="EV-BALLISTIC-DURATION",
            evidence_type=EvidenceType.SIMULATION,
            title="Total simulation duration",
            description=None,
            data=SimulationEvidence(
                value=final_time,
                unit=time_unit,
                location=f"final state step_id={final_state.step_id}",
            ),
            field_metadata=final_field.metadata,
            derivation=None,
            source=final_field.metadata.source_solver,
            source_file=str(final_field.metadata.source_file),
        )
    )
    section_lines.append(
        f"- 仿真时长 (Run duration): **{final_time:.6g} {time_unit}** "
        f"@ final state step_id={final_state.step_id}  "
        "*(EV-BALLISTIC-DURATION)*"
    )

    # 2) Peak displacement
    bundle.add_evidence(
        EvidenceItem(
            evidence_id="EV-BALLISTIC-MAX-DISP",
            evidence_type=EvidenceType.SIMULATION,
            title="Peak nodal displacement magnitude across run",
            description=None,
            data=SimulationEvidence(
                value=peak_disp_value,
                unit=length_unit,
                location=f"step_id={peak_step_id}",
            ),
            field_metadata=peak_field.metadata,
            derivation=None,
            source=peak_field.metadata.source_solver,
            source_file=str(peak_field.metadata.source_file),
        )
    )
    section_lines.append(
        f"- 峰值位移 (Peak displacement): "
        f"**{peak_disp_value:.6g} {length_unit}** "
        f"@ step_id={peak_step_id}  *(EV-BALLISTIC-MAX-DISP)*"
    )

    # 3) Eroded facet count (final state) — only when the reader
    #    supports element deletion. Bind to the FINAL state's metadata
    #    so source_file points to the file the count came from.
    if has_erosion:
        final_eroded = erosion_by_step[final_state.step_id]
        bundle.add_evidence(
            EvidenceItem(
                evidence_id="EV-BALLISTIC-EROSION-FINAL",
                evidence_type=EvidenceType.SIMULATION,
                title="Eroded facet count at final state",
                description=None,
                data=SimulationEvidence(
                    value=float(final_eroded),
                    unit="facets",
                    location=f"final state step_id={final_state.step_id}",
                ),
                field_metadata=final_field.metadata,
                derivation=None,
                source=final_field.metadata.source_solver,
                source_file=str(final_field.metadata.source_file),
            )
        )
        section_lines.append(
            f"- 终态侵蚀单元数 (Eroded facets at final state): "
            f"**{final_eroded} facets**  *(EV-BALLISTIC-EROSION-FINAL)*"
        )

    # 4) Perforation event — only when actually observed. Bind to the
    #    perforation-step's metadata so source_file points to the file
    #    where the first erosion was observed.
    if has_erosion:
        if perforation_step is not None:
            perforation_time = (
                float(state_lookup[perforation_step].time)
                if state_lookup[perforation_step].time is not None
                else 0.0
            )
            perforation_field = _field_at(perforation_step)
            bundle.add_evidence(
                EvidenceItem(
                    evidence_id="EV-BALLISTIC-PERFORATION-EVENT",
                    evidence_type=EvidenceType.SIMULATION,
                    title="Perforation event step (first eroded facet)",
                    description=None,
                    data=SimulationEvidence(
                        value=perforation_time,
                        unit=time_unit,
                        location=f"step_id={perforation_step}",
                    ),
                    field_metadata=perforation_field.metadata,
                    derivation=["EV-BALLISTIC-EROSION-FINAL"],
                    source=perforation_field.metadata.source_solver,
                    source_file=str(perforation_field.metadata.source_file),
                )
            )
            section_lines.append(
                f"- 穿透事件 (Perforation event): "
                f"**t={perforation_time:.6g} {time_unit}** "
                f"@ step_id={perforation_step}  "
                "*(EV-BALLISTIC-PERFORATION-EVENT)*"
            )
        else:
            # No erosion observed → cite the EV-BALLISTIC-EROSION-FINAL
            # evidence already added to the bundle (final_eroded == 0).
            # ADR-012 / RFC-001 §2.4 rule 1: every claim must reference
            # an EV-* evidence_id, including a "did not happen" claim.
            section_lines.append(
                "- 穿透事件 (Perforation event): "
                "**未观察到 / no perforation observed**  "
                "*(EV-BALLISTIC-EROSION-FINAL)*"
            )

    summary = ReportSection(
        title="弹道穿透时程摘要 (Ballistic-penetration time-history summary)",
        level=1,
        content="\n".join(section_lines),
    )

    report = ReportSpec(
        report_id=report_id,
        project_id=project_id,
        title=title_resolved,
        template_id=template_id_resolved,
        sections=[summary],
        generated_at=datetime.utcnow(),
        evidence_bundle_id=bundle.bundle_id,
    )
    return report, bundle
