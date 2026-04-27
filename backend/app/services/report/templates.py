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

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

from app.models import EvidenceBundle, ReportSection, ReportSpec
from app.services.report.exporter import CITATION_RE


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
    "validate_report_collect",
]


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
    """Raised when a :class:`ReportSpec` violates a :class:`TemplateSpec`.

    Carries a structured ``violations`` tuple so engineering tooling
    can introspect every violation without parsing the error message.
    The exception's string form is the aggregated multi-line summary
    that gets shown on stderr; ``violations`` is the same set of
    messages in raw form.
    """

    def __init__(
        self,
        message: str,
        *,
        violations: Tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.violations: Tuple[str, ...] = tuple(violations) or (message,)


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


def _find_sections_by_title(
    sections: Iterable[ReportSection], title: str
) -> List[ReportSection]:
    """Return *all* sections whose title matches ``title``. Multiple
    matches are allowed — :func:`validate_report` accepts the report
    if *any* candidate satisfies the level + citation requirements
    (avoids rejecting a report just because an earlier duplicate-titled
    section under-cites; Codex R1 MEDIUM finding)."""
    return [s for s in _walk_sections(sections) if s.title == title]


def _distinct_citation_count(content: str) -> int:
    """Count the number of *distinct* ``EV-*`` tokens cited in
    ``content``. Repeating the same citation N times still counts as
    one piece of evidence (Codex R1 HIGH finding)."""
    return len(set(CITATION_RE.findall(content)))


def validate_report_collect(
    report: ReportSpec,
    bundle: EvidenceBundle,
    *,
    template: TemplateSpec,
) -> List[str]:
    """Return every violation of ``template`` by ``report`` as a list
    of human-readable messages.

    Empty list ⇒ the report satisfies the template contract.

    This is the building block engineers reach for when they want to
    surface *all* fixes the report needs in one pass — the reach-for-
    a-DOCX-fix-rerun loop is dramatically slower if validation only
    reports the first problem on each iteration.

    Multi-error contract per requirement:
      * The ``template_id`` mismatch is reported on its own; if the
        IDs disagree, no per-section checks are performed (the
        sections aren't comparable until the engineer fixes the
        template alignment first). This is the only short-circuit.
      * Each ``SectionRequirement`` is checked independently: missing
        section → 1 violation; same-titled candidates that all fail
        their level+citation contract → 1 violation derived from the
        *last* same-titled candidate inspected (DFS pre-order order).
        We do NOT emit one violation per bad candidate; that would
        multiply the noise without adding signal. The "last one
        inspected" wording is deliberate — earlier we considered
        picking the "closest-to-correct" candidate, but the simpler
        rule is what's implemented and what callers should rely on.

    Duplicate section titles are still tolerated: the requirement
    passes if *any* same-titled section satisfies level + citation.

    The ``bundle`` parameter is reserved for future per-template
    evidence-type checks; currently only section content is consulted.
    """
    violations: List[str] = []

    if report.template_id != template.template_id:
        violations.append(
            f"report.template_id={report.template_id!r} but template "
            f"contract is for {template.template_id!r}; pass the "
            "matching TemplateSpec or fix the report's template_id."
        )
        # Stop here — comparing per-section requirements between
        # mismatched templates produces meaningless noise.
        return violations

    # Reserved for future per-template bundle requirements.
    _ = bundle

    for req in template.required_sections:
        candidates = _find_sections_by_title(report.sections, req.title)
        if not candidates:
            violations.append(
                f"template {template.template_id!r} requires a section "
                f"titled {req.title!r}; report has no such section. "
                f"Sections present: "
                f"{[s.title for s in _walk_sections(report.sections)]!r}"
            )
            continue
        n_candidates = len(candidates)
        candidate_suffix = (
            f" ({n_candidates} same-titled section(s) checked, none satisfy)"
            if n_candidates > 1
            else ""
        )
        last_error: str | None = None
        for sec in candidates:
            if sec.level != req.level:
                last_error = (
                    f"template {template.template_id!r} requires section "
                    f"{req.title!r} at level {req.level}; report has it "
                    f"at level {sec.level}.{candidate_suffix}"
                )
                continue
            citations = _distinct_citation_count(sec.content or "")
            if citations < req.minimum_evidence_citations:
                last_error = (
                    f"template {template.template_id!r} requires section "
                    f"{req.title!r} to cite at least "
                    f"{req.minimum_evidence_citations} distinct evidence "
                    f"items (EV-* tokens); found {citations}."
                    f"{candidate_suffix}"
                )
                continue
            # All requirements satisfied for this candidate.
            last_error = None
            break
        if last_error is not None:
            violations.append(last_error)

    return violations


def _format_aggregated_message(
    template: TemplateSpec,
    violations: Sequence[str],
) -> str:
    n = len(violations)
    header = (
        f"template {template.template_id!r} validation failed "
        f"({n} violation{'s' if n != 1 else ''}):"
    )
    bullets = "\n".join(f"  - {v}" for v in violations)
    return f"{header}\n{bullets}"


def validate_report(
    report: ReportSpec,
    bundle: EvidenceBundle,
    *,
    template: TemplateSpec,
) -> None:
    """Refuse if ``report`` does not honour the ``template`` contract.

    Collects every violation via :func:`validate_report_collect` and,
    if any are present, raises a single :class:`TemplateValidationError`
    whose message aggregates all of them. The exception's
    ``violations`` attribute carries the same list in structured form
    so engineering tooling can introspect without parsing strings.

    Engineer ergonomics: reporting all violations at once turns the
    fix-rerun loop from O(N) into O(1). Each violation's wording is
    unchanged from the previous fail-fast implementation, so existing
    ``pytest.raises(..., match=...)`` assertions keep matching the
    aggregated message text.

    Duplicate section titles are tolerated (a requirement passes if
    *any* same-titled section satisfies level + citation). Templates
    with mismatched ``template_id`` are reported as a single violation
    and per-section checks are skipped (they would compare apples to
    oranges).
    """
    violations = validate_report_collect(report, bundle, template=template)
    if violations:
        raise TemplateValidationError(
            _format_aggregated_message(template, violations),
            violations=tuple(violations),
        )
