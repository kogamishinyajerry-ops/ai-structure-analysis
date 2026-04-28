"""W6e.2 model-overview DOCX wiring tests — RFC-001 W6e.2.

Confirms the § 模型概览 (Model overview) section makes it from
``model_overview.summarize_model`` through ``draft.py`` into the
returned ``ReportSpec`` with the right evidence wiring, regardless
of which entry point (static / lifting-lug, both via the shared
``_render_max_field_summary`` engine) was invoked.

Test buckets:

1. Section presence + ordering: model-overview section appears
   between the strength summary and the BC section.
2. Evidence presence: ``EV-MODEL-OVERVIEW-001`` lands in the bundle
   with the right title / value / unit / type.
3. Inventory-available rendering: the section shows node count +
   element count + group breakdown.
4. Inventory-unavailable rendering: the section shows the
   ``[需工程师确认]`` placeholder when the adapter doesn't declare
   the capability OR returns None.
5. GROUP_OTHER footnote: when unknown solver-native types appear,
   the section lists them so the engineer sees the gap.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.adapters.calculix.reader import CalculiXReader
from app.core.types import UnitSystem


_GS001_FRD: Path = (
    Path(__file__).resolve().parents[2]
    / "golden_samples"
    / "GS-001"
    / "gs001_result.frd"
)


pytestmark = pytest.mark.skipif(
    not _GS001_FRD.is_file(), reason="GS-001 fixture missing"
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _gs001_reader() -> CalculiXReader:
    return CalculiXReader(_GS001_FRD, unit_system=UnitSystem.SI_MM)


def _generate_static() -> tuple:
    """Run the static-strength generator against GS-001 and return
    ``(report, bundle)``. Centralises the boilerplate — every test
    in this module shares the same entry point."""
    from app.services.report.draft import generate_static_strength_summary

    reader = _gs001_reader()
    try:
        return generate_static_strength_summary(
            reader,
            project_id="P-W6E2",
            task_id="T-W6E2",
            report_id="R-W6E2",
            bundle_id="B-W6E2",
        )
    finally:
        reader.close()


# ---------------------------------------------------------------------------
# Bucket 1 — section presence + ordering
# ---------------------------------------------------------------------------


def test_model_overview_section_is_emitted_for_static_report() -> None:
    report, _ = _generate_static()
    titles = [s.title for s in report.sections]
    assert any(
        "模型概览" in t or "Model overview" in t for t in titles
    ), f"missing § 模型概览 section; titles={titles}"


def test_model_overview_section_ordering_matches_existing_convention() -> None:
    """The established DOCX convention (per W6c.2 / W6d.2) is
    headlines-first, then upstream context: § 结构强度摘要 →
    § 许用应力 → § 评定结论 → § 模型概览 (W6e.2 — this PR) →
    § 边界条件. Pin that order so a future "context-first" reorder
    is a deliberate, reviewed change."""
    report, _ = _generate_static()
    titles = [s.title for s in report.sections]
    overview_idx = next(
        i for i, t in enumerate(titles) if "模型概览" in t or "Model overview" in t
    )
    strength_idx = next(
        i for i, t in enumerate(titles) if "结构强度" in t or "summary" in t.lower()
    )
    # Strength section comes FIRST (headline). Overview comes after.
    # If a § 边界条件 section is also present (only when bc_yaml_path
    # was supplied — not this test), it would come AFTER overview.
    assert strength_idx < overview_idx, (
        f"§ 模型概览 must come AFTER § 结构强度摘要 (headlines-first "
        f"convention); strength_idx={strength_idx}, "
        f"overview_idx={overview_idx}, titles={titles}"
    )


# ---------------------------------------------------------------------------
# Bucket 2 — evidence presence
# ---------------------------------------------------------------------------


def test_model_overview_evidence_lands_in_bundle() -> None:
    _, bundle = _generate_static()
    ev_ids = [item.evidence_id for item in bundle.evidence_items]
    assert "EV-MODEL-OVERVIEW-001" in ev_ids


def test_model_overview_evidence_has_reference_type() -> None:
    """Model overview is upstream context, not a derived computation
    — the evidence must be type=REFERENCE (parallels W6d's bc.yaml
    handling) so the renderer / auditor can distinguish it from
    SimulationEvidence (per-state field reads) and AnalyticalEvidence
    (allowable / verdict computations).

    GS-001 declares element inventory, so the inventory-available
    branch fires: value = total element count, unit = "elements".
    The inventory-unavailable branch is exercised by
    ``test_evidence_does_not_fabricate_element_count_when_inventory_missing``.
    """
    from app.models import EvidenceType

    _, bundle = _generate_static()
    ev = next(
        item
        for item in bundle.evidence_items
        if item.evidence_id == "EV-MODEL-OVERVIEW-001"
    )
    assert ev.evidence_type == EvidenceType.REFERENCE
    # Value is the total element count cast to float.
    assert ev.data.value >= 0.0
    assert ev.data.unit == "elements"
    assert "elements=" in ev.data.citation_anchor
    assert "unknown" not in ev.data.citation_anchor


def test_evidence_does_not_fabricate_element_count_when_inventory_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Codex R1 HIGH on PR #110 — ADR-003 (do-not-fabricate).

    When the adapter cannot supply an element inventory, the evidence
    bundle MUST NOT report ``elements=0`` as if zero were a confirmed
    measurement. Anchor the evidence to the always-known node count
    (Mesh Protocol guarantees node coordinates) and spell the missing
    element count out as text in ``citation_anchor`` so any downstream
    consumer that reads the payload (rather than the section prose)
    sees the unknown state.
    """
    from app.services.report.draft import generate_static_strength_summary

    reader = _gs001_reader()
    try:
        # Same simulation as the section-rendering test — adapter
        # declares the capability but the underlying FRD has no -3
        # block, so element_types() returns None.
        monkeypatch.setattr(reader._parsed, "elements", {})
        _, bundle = generate_static_strength_summary(
            reader,
            project_id="P-W6E2-NF",
            task_id="T-W6E2-NF",
            report_id="R-W6E2-NF",
            bundle_id="B-W6E2-NF",
        )
    finally:
        reader.close()

    ev = next(
        item
        for item in bundle.evidence_items
        if item.evidence_id == "EV-MODEL-OVERVIEW-001"
    )
    # Value cannot claim a concrete element count.
    assert ev.data.unit != "elements", (
        f"unit must not assert 'elements' when inventory unavailable; "
        f"got unit={ev.data.unit!r}"
    )
    # citation_anchor must spell out the unknown state.
    anchor = ev.data.citation_anchor or ""
    assert "elements=0" not in anchor, (
        f"citation_anchor fabricated elements=0 in unavailable branch: "
        f"{anchor!r}"
    )
    assert "unknown" in anchor.lower(), (
        f"citation_anchor must mark element count as unknown; "
        f"got {anchor!r}"
    )
    # Description still flags the unavailable state for human review.
    assert "has_inventory=False" in (ev.description or "")


# ---------------------------------------------------------------------------
# Bucket 3 — inventory-available rendering
# ---------------------------------------------------------------------------


def test_section_content_includes_node_and_element_counts() -> None:
    report, _ = _generate_static()
    overview_section = next(
        s for s in report.sections
        if "模型概览" in s.title or "Model overview" in s.title
    )
    assert "节点数" in overview_section.content or "Total nodes" in overview_section.content
    assert "单元数" in overview_section.content or "Total elements" in overview_section.content
    assert "EV-MODEL-OVERVIEW-001" in overview_section.content


def test_section_content_includes_group_distribution_for_gs001() -> None:
    """GS-001 has a known element-type distribution (resolves through
    the FRD-code translation table); the rendered section should
    include the by-family breakdown line."""
    report, _ = _generate_static()
    overview_section = next(
        s for s in report.sections
        if "模型概览" in s.title or "Model overview" in s.title
    )
    assert (
        "按类型分布" in overview_section.content
        or "Distribution by family" in overview_section.content
    )


# ---------------------------------------------------------------------------
# Bucket 4 — inventory-unavailable rendering
# ---------------------------------------------------------------------------


def test_section_renders_placeholder_when_capability_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the adapter reports ``element_types() == None`` (FRD with
    no -3 block), the renderer must show the ``[需工程师确认]`` flag
    rather than fabricating a count."""
    from app.services.report.draft import generate_static_strength_summary

    reader = _gs001_reader()
    try:
        # Simulate an FRD whose -3 block was missing or failed to parse.
        monkeypatch.setattr(reader._parsed, "elements", {})
        report, _ = generate_static_strength_summary(
            reader,
            project_id="P-W6E2",
            task_id="T-W6E2",
            report_id="R-W6E2-NO-INV",
            bundle_id="B-W6E2-NO-INV",
        )
    finally:
        reader.close()

    overview_section = next(
        s for s in report.sections
        if "模型概览" in s.title or "Model overview" in s.title
    )
    assert "[需工程师确认]" in overview_section.content
    assert "无单元清单" in overview_section.content
    # Node count is still rendered (Mesh Protocol always works).
    assert "节点数" in overview_section.content or "Total nodes" in overview_section.content
    # NO group-distribution line in this branch (placeholder takes its place).
    assert "按类型分布" not in overview_section.content


# ---------------------------------------------------------------------------
# Bucket 5 — GROUP_OTHER footnote
# ---------------------------------------------------------------------------


def test_section_lists_unknown_types_in_other_footnote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the adapter emits solver-native types not in
    ELEMENT_TYPE_GROUPS, the section must list them in an
    "其他 / GROUP_OTHER includes" footnote so the engineer can decide
    whether to extend the W6e table."""
    from app.adapters.calculix.reader import CalculiXReader
    from app.parsers.frd_parser import FRDElement
    from app.services.report.draft import generate_static_strength_summary

    reader = _gs001_reader()
    try:
        # Replace the FRD elements with a deck full of made-up types
        # that are not in ELEMENT_TYPE_GROUPS. Keep one known type
        # so the section still exercises the GROUP_OTHER branch
        # alongside a known group.
        fake_elements = {
            1: FRDElement(element_id=1, element_type="6", nodes=[1, 2, 3]),  # → C3D10 (known tet)
            2: FRDElement(
                element_id=2, element_type="MYSTERY", nodes=[1, 2, 3]
            ),
            3: FRDElement(
                element_id=3, element_type="GASKET_X", nodes=[1, 2, 3]
            ),
        }
        monkeypatch.setattr(reader._parsed, "elements", fake_elements)
        report, _ = generate_static_strength_summary(
            reader,
            project_id="P-W6E2",
            task_id="T-W6E2",
            report_id="R-W6E2-OTHER",
            bundle_id="B-W6E2-OTHER",
        )
    finally:
        reader.close()

    overview_section = next(
        s for s in report.sections
        if "模型概览" in s.title or "Model overview" in s.title
    )
    assert "GASKET_X" in overview_section.content
    assert "MYSTERY" in overview_section.content
    # The known C3D10 must NOT appear in the OTHER footnote.
    # Codex R1 NIT on PR #110: isolate the actual footnote line and
    # assert against it instead of splitting on a prose fragment.
    other_footnote_lines = [
        ln
        for ln in overview_section.content.splitlines()
        if "GROUP_OTHER includes" in ln
    ]
    assert len(other_footnote_lines) == 1, (
        "expected exactly one GROUP_OTHER footnote line; "
        f"got {other_footnote_lines!r}"
    )
    other_line = other_footnote_lines[0]
    assert "GASKET_X" in other_line
    assert "MYSTERY" in other_line
    assert "C3D10" not in other_line
