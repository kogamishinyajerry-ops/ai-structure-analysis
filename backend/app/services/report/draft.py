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

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional, Tuple

import numpy as np
import numpy.typing as npt

from app.core.types import (
    CanonicalField,
    FieldData,
    FieldLocation,
    ReaderHandle,
    UnitSystem,
)
from app.domain.stress_derivatives import von_mises
from app.models import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceType,
    ReportSection,
    ReportSpec,
    SimulationEvidence,
)


__all__ = [
    "generate_static_strength_summary",
    "generate_lifting_lug_summary",
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

    report = ReportSpec(
        report_id=report_id,
        project_id=project_id,
        title=labels.title,
        template_id=labels.template_id,
        sections=[summary],
        generated_at=datetime.utcnow(),
        evidence_bundle_id=bundle.bundle_id,
    )
    return report, bundle


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

    Raises ``ValueError`` when the chosen state exposes neither
    ``DISPLACEMENT`` nor ``STRESS_TENSOR`` — emitting a section with no
    cited evidence would violate ADR-012.
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
    )
