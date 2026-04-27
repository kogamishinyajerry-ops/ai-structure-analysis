"""Layer-4 report-template registry — RFC-001 §2.4 rule 2 + §6.4.

The MVP wedge (RFC §3) targets three chemical / power design-institute
report kinds, each with a fixed structural skeleton:

  * ``equipment_foundation_static`` — equipment foundation static
    strength check
  * ``lifting_lug`` — lifting-lug strength assessment
  * ``pressure_vessel_local_stress`` — pressure-vessel local stress
    assessment (WRC-107 / FE-supported)

This module captures each template as a :class:`TemplateSpec` —
**Python data, not a ``.docx`` binary**. The wedge today produces a
section-by-section programmatic DOCX via :mod:`exporter`; the
template's job is to declare *what sections must appear, at which
level, and with how many cited evidence items*. A future iteration
(W5+) may pivot to ``.docx``-template binaries with placeholder
substitution; the ``TemplateSpec`` interface is the migration seam.

Why structural specs, not ``.docx`` binaries, for the MVP:
  * No new heavyweight dependency (``docxtpl`` carries Jinja2 +
    template loaders; the exporter already builds DOCX via
    ``python-docx``).
  * Validation is the load-bearing requirement (RFC §2.4 rule 2 —
    "模板占位符是白名单制" / placeholder whitelist). A Python data
    contract gives strict type-checking; a ``.docx`` template would
    delegate validation to template-engine string scanning.
  * The 3 MVP layouts are short (1-3 sections each). The cost of
    declaring them in code is negligible.

Key invariants enforced by :func:`validate_report`:
  1. Every :class:`SectionRequirement` in ``template.required_sections``
     must match at least one section in ``report.sections`` (exact
     title; the section walker descends into subsections).
  2. Each matched section must have at least
     ``requirement.minimum_evidence_citations`` ``EV-*`` citations
     in its ``content`` (RFC §2.4 rule 1: every claim cites evidence).
  3. ``report.template_id`` must match ``template.template_id`` —
     mixing a draft generator's template_id with a different
     template's spec is a programmer error, not a content problem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, Optional, Tuple

from app.models import EvidenceBundle, ReportSection, ReportSpec


__all__ = [
    "SectionRequirement",
    "TemplateSpec",
    "TemplateValidationError",
    "EQUIPMENT_FOUNDATION_STATIC",
    "LIFTING_LUG",
    "PRESSURE_VESSEL_LOCAL_STRESS",
    "get_template",
    "supported_template_ids",
    "validate_report",
]


_CITATION_RE = re.compile(r"\bEV-[A-Z0-9][A-Z0-9_\-]*\b")
"""Citation pattern, must match :data:`exporter._CITATION_RE`. Kept
local to avoid coupling templates → exporter; if either drifts the
test suite catches it via the e2e roundtrip."""


@dataclass(frozen=True)
class SectionRequirement:
    """A single section the template requires the report to contain.

    ``title`` is matched literally against ``ReportSection.title`` —
    no regex, no fuzzy match. The Chinese / English title pair the
    draft generator emits (``"结构强度摘要 (Static-strength summary)"``)
    is the canonical form; deviations are caught by validation.
    """

    title: str
    level: int
    minimum_evidence_citations: int = 0


@dataclass(frozen=True)
class TemplateSpec:
    """One MVP report template's structural contract.

    ``required_sections`` is order-independent at validation time —
    the template asserts that each required section appears
    *somewhere* in the report tree. The exporter is what controls
    rendering order.
    """

    template_id: str
    name: str
    description: str
    required_sections: Tuple[SectionRequirement, ...]


class TemplateValidationError(ValueError):
    """Raised when a :class:`ReportSpec` violates a :class:`TemplateSpec`."""


# --- the 3 MVP templates --------------------------------------------------

EQUIPMENT_FOUNDATION_STATIC = TemplateSpec(
    template_id="equipment_foundation_static",
    name="设备基础静力强度核算 / Equipment foundation static-strength check",
    description=(
        "Chemical / power-equipment foundation static-load assessment. "
        "Verifies maximum displacement and maximum von Mises stress at "
        "design conditions; the engineer compares σ_vm,max against the "
        "material's allowable stress in the signed report."
    ),
    required_sections=(
        SectionRequirement(
            title="结构强度摘要 (Static-strength summary)",
            level=1,
            minimum_evidence_citations=2,
        ),
    ),
)


LIFTING_LUG = TemplateSpec(
    template_id="lifting_lug",
    name="吊耳强度评估 / Lifting-lug strength assessment",
    description=(
        "Lifting-lug strength check under hoisting load (typically 2x "
        "service factor per GB 50017 §11). Reports max σ_vm at the "
        "lug-shell weld and the maximum displacement under hoist load."
    ),
    required_sections=(
        SectionRequirement(
            title="吊耳强度评估 (Lifting-lug strength assessment)",
            level=1,
            minimum_evidence_citations=2,
        ),
    ),
)


PRESSURE_VESSEL_LOCAL_STRESS = TemplateSpec(
    template_id="pressure_vessel_local_stress",
    name="压力容器局部应力评估 / Pressure-vessel local stress assessment",
    description=(
        "Local stress assessment at a nozzle / saddle-support location, "
        "compared against ASME VIII Div 2 5.5 / WRC-107 limits. Reports "
        "membrane stress P_m, membrane+bending P_m+P_b, and the maximum "
        "primary-plus-secondary stress (P+Q) at the assessment section."
    ),
    required_sections=(
        SectionRequirement(
            title="局部应力评估 (Local stress assessment)",
            level=1,
            minimum_evidence_citations=3,
        ),
    ),
)


_REGISTRY: Dict[str, TemplateSpec] = {
    t.template_id: t
    for t in (
        EQUIPMENT_FOUNDATION_STATIC,
        LIFTING_LUG,
        PRESSURE_VESSEL_LOCAL_STRESS,
    )
}


def supported_template_ids() -> Tuple[str, ...]:
    """Sorted tuple of registered template IDs."""
    return tuple(sorted(_REGISTRY))


def get_template(template_id: str) -> TemplateSpec:
    """Look up a template by ID. Raises ``KeyError`` if unknown."""
    if template_id not in _REGISTRY:
        raise KeyError(
            f"unknown template_id {template_id!r}; registered: "
            f"{supported_template_ids()!r}"
        )
    return _REGISTRY[template_id]


# --- validation -----------------------------------------------------------


def _walk_sections(sections: Iterable[ReportSection]) -> Iterator[ReportSection]:
    """Pre-order DFS walk (iterative, no recursion limit)."""
    stack = list(reversed(list(sections)))
    while stack:
        sec = stack.pop()
        yield sec
        for child in reversed(sec.subsections):
            stack.append(child)


def _find_section_by_title(
    sections: Iterable[ReportSection], title: str
) -> Optional[ReportSection]:
    for sec in _walk_sections(sections):
        if sec.title == title:
            return sec
    return None


def validate_report(
    report: ReportSpec,
    bundle: EvidenceBundle,
    *,
    template: TemplateSpec,
) -> None:
    """Refuse if ``report`` does not honour the ``template`` contract.

    Raises :class:`TemplateValidationError` on the first violation
    encountered (template_id mismatch → missing section → wrong level
    → too few citations). Single-error semantics keep the failure
    message actionable; the engineer fixes one issue and re-runs.

    The ``bundle`` parameter is currently consulted only via the
    cited-evidence count derived from section content. A future
    extension may also enforce template-specific evidence-type
    requirements; the parameter is kept in the signature now to
    avoid an API churn later.
    """
    if report.template_id != template.template_id:
        raise TemplateValidationError(
            f"report.template_id={report.template_id!r} but template "
            f"contract is for {template.template_id!r}; pass the "
            "matching TemplateSpec or fix the report's template_id."
        )

    # Reserved for future per-template bundle requirements.
    _ = bundle

    for req in template.required_sections:
        sec = _find_section_by_title(report.sections, req.title)
        if sec is None:
            raise TemplateValidationError(
                f"template {template.template_id!r} requires a section "
                f"titled {req.title!r}; report has no such section. "
                f"Sections present: "
                f"{[s.title for s in _walk_sections(report.sections)]!r}"
            )
        if sec.level != req.level:
            raise TemplateValidationError(
                f"template {template.template_id!r} requires section "
                f"{req.title!r} at level {req.level}; report has it at "
                f"level {sec.level}."
            )
        citations = (
            len(_CITATION_RE.findall(sec.content)) if sec.content else 0
        )
        if citations < req.minimum_evidence_citations:
            raise TemplateValidationError(
                f"template {template.template_id!r} requires section "
                f"{req.title!r} to cite at least "
                f"{req.minimum_evidence_citations} evidence items "
                f"(EV-* tokens); found {citations}."
            )
