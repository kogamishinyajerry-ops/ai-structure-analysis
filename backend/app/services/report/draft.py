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


__all__ = ["generate_static_strength_summary"]


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


def generate_static_strength_summary(
    reader: ReaderHandle,
    *,
    project_id: str,
    task_id: str,
    report_id: str,
    bundle_id: str,
    step_id: Optional[int] = None,
    template_id: str = "equipment_foundation_static",
    title: str = "Static-strength summary",
) -> Tuple[ReportSpec, EvidenceBundle]:
    """Generate the minimum-viable static-strength report draft.

    Returns ``(report, bundle)`` such that every section in ``report``
    references at least one ``evidence_id`` that resolves inside
    ``bundle`` (ADR-012 invariant). The caller persists / exports
    these together; the exporter (lands W4+) refuses to emit DOCX
    for any draft whose evidence references don't resolve.

    ``step_id`` selects which solution state to summarise. When
    ``None`` the *final* state is used (``solution_states[-1]``) — for
    static analyses this matches the converged result; the choice is
    deliberate, never silent. Pass ``step_id`` explicitly for
    multi-step / transient cases.

    Raises ``ValueError`` when the chosen state exposes neither
    ``DISPLACEMENT`` nor ``STRESS_TENSOR`` — emitting a section with no
    cited evidence would violate ADR-012.
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
        title=f"Evidence backing {title}",
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
            evidence_id="EV-DISP-MAX",
            evidence_type=EvidenceType.SIMULATION,
            title="Maximum displacement magnitude",
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
            f"- 最大位移: **{max_u:.6g} {unit_u}** "
            f"@ node {node_u}  *(EV-DISP-MAX)*"
        )

    stress_pair = _max_von_mises(stress_fd, node_ids)
    if stress_pair is not None:
        assert stress_fd is not None  # see disp_fd comment above
        max_vm, node_vm = stress_pair
        unit_s = _unit_label_for_system(stress_fd.metadata.unit_system, "stress")
        ev_s = EvidenceItem(
            evidence_id="EV-VM-MAX",
            evidence_type=EvidenceType.SIMULATION,
            title="Maximum von Mises stress",
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
            f"- 最大 von Mises 应力: **{max_vm:.6g} {unit_s}** "
            f"@ node {node_vm}  *(EV-VM-MAX)*"
        )

    if not section_lines:
        # ADR-012: a section with no cited evidence_ids cannot ship.
        # Refuse rather than emit an uncited placeholder.
        raise ValueError(
            f"solution state {step.step_id!r} of task {task_id!r} exposes "
            "neither DISPLACEMENT nor STRESS_TENSOR; cannot generate a "
            "static-strength draft with zero evidence (ADR-012)."
        )

    summary = ReportSection(
        title="结构强度摘要 (Static-strength summary)",
        level=1,
        content="\n".join(section_lines),
    )

    report = ReportSpec(
        report_id=report_id,
        project_id=project_id,
        title=title,
        template_id=template_id,
        sections=[summary],
        generated_at=datetime.utcnow(),
        evidence_bundle_id=bundle.bundle_id,
    )
    return report, bundle
