"""Layer-4 template-spec tests — RFC-001 §2.4 rule 2 + §6.4."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.calculix import CalculiXReader
from app.core.types import UnitSystem
from app.models import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceType,
    ReportSection,
    ReportSpec,
    SimulationEvidence,
)
from app.services.report.draft import generate_static_strength_summary
from app.services.report.templates import (
    EQUIPMENT_FOUNDATION_STATIC,
    LIFTING_LUG,
    PRESSURE_VESSEL_LOCAL_STRESS,
    SectionRequirement,
    TemplateSpec,
    TemplateValidationError,
    get_template,
    supported_template_ids,
    validate_report,
)


GS001_FRD = (
    Path(__file__).resolve().parents[2] / "golden_samples" / "GS-001" / "gs001_result.frd"
)


# --- registry / lookup ----------------------------------------------------


def test_supported_template_ids_returns_three_known_templates() -> None:
    ids = supported_template_ids()
    assert ids == (
        "equipment_foundation_static",
        "lifting_lug",
        "pressure_vessel_local_stress",
    )


def test_get_template_resolves_known() -> None:
    t = get_template("equipment_foundation_static")
    assert t is EQUIPMENT_FOUNDATION_STATIC
    assert t.template_id == "equipment_foundation_static"


def test_get_template_unknown_raises() -> None:
    with pytest.raises(KeyError, match="unknown template_id"):
        get_template("does_not_exist")


def test_each_template_has_at_least_one_required_section() -> None:
    """Sanity: a template with no required_sections is meaningless."""
    for tid in supported_template_ids():
        t = get_template(tid)
        assert len(t.required_sections) >= 1, t.template_id


def test_each_template_id_matches_template_id_field() -> None:
    """Registry key must match the spec's own template_id field."""
    from app.services.report.templates import _REGISTRY

    for k, v in _REGISTRY.items():
        assert k == v.template_id


# --- happy-path validation -------------------------------------------------


def _make_pair_with_section(
    title: str,
    *,
    level: int = 1,
    citations: list[str],
    template_id: str,
) -> tuple[ReportSpec, EvidenceBundle]:
    citation_text = "  ".join(f"*({c})*" for c in citations)
    items = [
        EvidenceItem(
            evidence_id=eid,
            evidence_type=EvidenceType.SIMULATION,
            title=f"t-{eid}",
            data=SimulationEvidence(value=1.0, unit="mm", location="node 1"),
            source="synthetic",
        )
        for eid in citations
    ]
    bundle = EvidenceBundle(bundle_id="B", task_id="T", title="b")
    for it in items:
        bundle.add_evidence(it)
    report = ReportSpec(
        report_id="R",
        project_id="P",
        title="t",
        template_id=template_id,
        sections=[
            ReportSection(
                title=title, level=level,
                content=f"- value: **0.5 mm** {citation_text}",
            )
        ],
        evidence_bundle_id="B",
    )
    return report, bundle


def test_validate_report_passes_for_compliant_equipment_foundation() -> None:
    report, bundle = _make_pair_with_section(
        "结构强度摘要 (Static-strength summary)",
        level=1,
        citations=["EV-DISP-MAX", "EV-VM-MAX"],
        template_id="equipment_foundation_static",
    )
    validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_validate_report_passes_for_compliant_lifting_lug() -> None:
    report, bundle = _make_pair_with_section(
        "吊耳强度评估 (Lifting-lug strength assessment)",
        level=1,
        citations=["EV-LUG-VM", "EV-LUG-DISP"],
        template_id="lifting_lug",
    )
    validate_report(report, bundle, template=LIFTING_LUG)


def test_validate_report_passes_for_compliant_pressure_vessel() -> None:
    report, bundle = _make_pair_with_section(
        "局部应力评估 (Local stress assessment)",
        level=1,
        citations=["EV-PM", "EV-PM-PB", "EV-P-Q"],
        template_id="pressure_vessel_local_stress",
    )
    validate_report(report, bundle, template=PRESSURE_VESSEL_LOCAL_STRESS)


# --- validation refusals --------------------------------------------------


def test_validate_report_refuses_template_id_mismatch() -> None:
    report, bundle = _make_pair_with_section(
        "结构强度摘要 (Static-strength summary)",
        citations=["EV-A", "EV-B"],
        template_id="lifting_lug",  # wrong
    )
    with pytest.raises(TemplateValidationError, match="template_id"):
        validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_validate_report_refuses_missing_section() -> None:
    report, bundle = _make_pair_with_section(
        "Wrong title (Static-strength summary)",
        citations=["EV-A", "EV-B"],
        template_id="equipment_foundation_static",
    )
    with pytest.raises(TemplateValidationError, match="no such section"):
        validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_validate_report_refuses_wrong_level() -> None:
    report, bundle = _make_pair_with_section(
        "结构强度摘要 (Static-strength summary)",
        level=2,
        citations=["EV-A", "EV-B"],
        template_id="equipment_foundation_static",
    )
    with pytest.raises(TemplateValidationError, match="at level"):
        validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_validate_report_refuses_too_few_citations() -> None:
    report, bundle = _make_pair_with_section(
        "结构强度摘要 (Static-strength summary)",
        citations=["EV-ONLY-ONE"],  # template requires 2
        template_id="equipment_foundation_static",
    )
    with pytest.raises(TemplateValidationError, match="at least 2"):
        validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_validate_report_refuses_duplicate_evidence_id_double_count() -> None:
    """Codex R1 HIGH: citing the same evidence_id twice does not satisfy
    a 'minimum 2 evidence items' requirement — only DISTINCT EV-* tokens
    count."""
    items = [
        EvidenceItem(
            evidence_id="EV-A",
            evidence_type=EvidenceType.SIMULATION,
            title="t-A",
            data=SimulationEvidence(value=1.0, unit="mm", location="node 1"),
            source="synthetic",
        )
    ]
    bundle = EvidenceBundle(bundle_id="B", task_id="T", title="b")
    for it in items:
        bundle.add_evidence(it)
    # Section content cites EV-A twice; raw findall returns 2, but
    # set() returns 1 — must refuse against minimum=2 template.
    report = ReportSpec(
        report_id="R", project_id="P", title="t",
        template_id="equipment_foundation_static",
        sections=[
            ReportSection(
                title="结构强度摘要 (Static-strength summary)",
                level=1,
                content="- value: **0.5 mm** *(EV-A)* and again *(EV-A)*",
            )
        ],
        evidence_bundle_id="B",
    )
    with pytest.raises(TemplateValidationError, match="at least 2 distinct"):
        validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_validate_report_accepts_later_duplicate_when_earlier_under_cites() -> None:
    """Codex R1 MEDIUM: when two sections share a title, the validator
    must accept the report if ANY candidate satisfies the requirement,
    not just the first one walked."""
    items = [
        EvidenceItem(
            evidence_id=eid,
            evidence_type=EvidenceType.SIMULATION,
            title=f"t-{eid}",
            data=SimulationEvidence(value=1.0, unit="mm", location="node 1"),
            source="synthetic",
        )
        for eid in ("EV-A", "EV-B")
    ]
    bundle = EvidenceBundle(bundle_id="B", task_id="T", title="b")
    for it in items:
        bundle.add_evidence(it)
    # First same-titled section under-cites (1); second satisfies (2).
    report = ReportSpec(
        report_id="R", project_id="P", title="t",
        template_id="equipment_foundation_static",
        sections=[
            ReportSection(
                title="结构强度摘要 (Static-strength summary)",
                level=1,
                content="- only one *(EV-A)*",
            ),
            ReportSection(
                title="wrapper", level=1, content=None,
                subsections=[
                    ReportSection(
                        title="结构强度摘要 (Static-strength summary)",
                        level=1,
                        content="- two distinct *(EV-A)* *(EV-B)*",
                    ),
                ],
            ),
        ],
        evidence_bundle_id="B",
    )
    # Must NOT raise — the second candidate satisfies.
    validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_validate_report_finds_section_in_subsection_tree() -> None:
    """Section title can live anywhere in the report tree, not just
    at the top level."""
    items = [
        EvidenceItem(
            evidence_id=eid,
            evidence_type=EvidenceType.SIMULATION,
            title=f"t-{eid}",
            data=SimulationEvidence(value=1.0, unit="mm", location="node 1"),
            source="synthetic",
        )
        for eid in ("EV-A", "EV-B")
    ]
    bundle = EvidenceBundle(bundle_id="B", task_id="T", title="b")
    for it in items:
        bundle.add_evidence(it)
    report = ReportSpec(
        report_id="R", project_id="P", title="t",
        template_id="equipment_foundation_static",
        sections=[
            ReportSection(
                title="项目背景", level=1,
                content=None,  # heading-only, exempt from cite check
                subsections=[
                    ReportSection(
                        title="结构强度摘要 (Static-strength summary)",
                        level=1,
                        content="- *(EV-A)* *(EV-B)*",
                    ),
                ],
            ),
        ],
        evidence_bundle_id="B",
    )
    validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


# --- e2e: draft generator output validates against its declared template -


@pytest.fixture
def gs001_reader() -> CalculiXReader:
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 .frd missing at {GS001_FRD}")
    return CalculiXReader(GS001_FRD, unit_system=UnitSystem.SI_MM)


def test_static_summary_validates_against_equipment_foundation_template(
    gs001_reader: CalculiXReader,
) -> None:
    """generate_static_strength_summary's output is the canonical
    producer for the equipment_foundation_static template — they must
    agree by construction."""
    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="GS-001", report_id="R", bundle_id="B",
    )
    assert report.template_id == "equipment_foundation_static"
    validate_report(report, bundle, template=EQUIPMENT_FOUNDATION_STATIC)


def test_export_docx_with_template_kwarg_e2e(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """Exporter accepts a template kwarg and validates pre-render."""
    from app.services.report.exporter import export_docx

    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="GS-001", report_id="R", bundle_id="B",
    )
    out = export_docx(
        report, bundle,
        output_path=tmp_path / "gs001.docx",
        template=EQUIPMENT_FOUNDATION_STATIC,
    )
    assert out.exists()


def test_export_docx_with_wrong_template_refuses(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """Passing a mismatched template surfaces TemplateValidationError
    BEFORE any DOCX is written."""
    from app.services.report.exporter import export_docx

    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="GS-001", report_id="R", bundle_id="B",
    )
    target = tmp_path / "should_not_exist.docx"
    with pytest.raises(TemplateValidationError):
        export_docx(
            report, bundle,
            output_path=target,
            template=LIFTING_LUG,  # wrong template for this draft
        )
    assert not target.exists()
