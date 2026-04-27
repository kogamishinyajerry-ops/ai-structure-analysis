"""Layer-4 DOCX exporter — RFC-001 §3 + ADR-012.

Materialises a signed-ready ``.docx`` from a ``(ReportSpec,
EvidenceBundle)`` pair produced by :func:`~app.services.report.draft.
generate_static_strength_summary`.

ADR-012 hard refusal:
  * The exporter MUST refuse to emit DOCX for a draft whose
    section-content cites an ``evidence_id`` that doesn't resolve in
    the linked bundle.
  * The bundle linkage itself is checked: ``report.evidence_bundle_id``
    must equal ``bundle.bundle_id``.

Citation convention (matches what ``draft.py`` emits):
  Inline references appear as ``EV-<UPPER-WITH-DASHES>`` somewhere in
  the section content (typically wrapped as ``*(EV-DISP-MAX)*``). The
  exporter scans content with a strict regex (see ``_CITATION_RE``)
  and treats every match as a claim that must resolve.

What this module does NOT do (deferred):
  * Standards-citation lookup (GB / ASME) — RFC §6.4 W4+.
  * Pretty Markdown → DOCX rendering. We do *minimum-viable*
    formatting: bold ``**...**``, italics ``*...*``, leading-dash
    bullets, and headings via section ``level``. Tables, images,
    code blocks are out of scope.
  * Signature blocks. The MVP wedge says the engineer signs the
    PDF/DOCX themselves through the company's review channel
    (RFC §2.3).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Set

from docx import Document
from docx.document import Document as _DocxDocument

from app.models import (
    EvidenceBundle,
    EvidenceItem,
    ReportSection,
    ReportSpec,
    SimulationEvidence,
)


__all__ = ["export_docx", "ExportError", "find_cited_evidence_ids"]


_CITATION_RE = re.compile(r"\bEV-[A-Z0-9][A-Z0-9_\-]*\b")
"""Citation pattern. ``EV-`` prefix followed by ``[A-Z0-9]`` then any
``[A-Z0-9_-]``. Word-boundary anchored so a stray ``EV-FOO`` inside a
URL won't accidentally match a leading hyphen.

The pattern intentionally rejects lowercase / mixed-case to avoid
false-positive collisions with prose. Authors who deviate must
introduce the new convention via RFC."""


class ExportError(ValueError):
    """Raised when ADR-012 invariants are violated at export time."""


def find_cited_evidence_ids(sections: Iterable[ReportSection]) -> Set[str]:
    """Walk a section tree and return the set of evidence_ids cited in
    any section's ``content`` (matched against :data:`_CITATION_RE`)."""
    cited: Set[str] = set()
    stack: List[ReportSection] = list(sections)
    while stack:
        sec = stack.pop()
        if sec.content:
            cited.update(_CITATION_RE.findall(sec.content))
        stack.extend(sec.subsections)
    return cited


def _format_evidence_value(item: EvidenceItem) -> str:
    """Human-readable one-liner for an evidence item, used in the
    appendix. Currently only ``SimulationEvidence`` is rendered with
    value/unit/location detail; reference / analytical evidence get a
    title-only entry until those payloads land in the MVP."""
    data = item.data
    if isinstance(data, SimulationEvidence):
        loc = f" @ {data.location}" if data.location else ""
        return f"{data.value:.6g} {data.unit}{loc}"
    return data.kind


_EMPHASIS_RE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")


def _emit_runs(para: object, line: str) -> None:
    """Tokenize ``line`` into runs honouring ``**bold**`` and ``*italic*``.

    Minimum-viable: a single linear pass through :data:`_EMPHASIS_RE`.
    Doesn't handle escapes or nested emphasis — and doesn't need to,
    the draft generator emits flat one-line bullets.
    """
    if not line:
        return
    for tok in _EMPHASIS_RE.split(line):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**") and len(tok) >= 4:
            run = para.add_run(tok[2:-2])  # type: ignore[attr-defined]
            run.bold = True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) >= 2:
            run = para.add_run(tok[1:-1])  # type: ignore[attr-defined]
            run.italic = True
        else:
            para.add_run(tok)  # type: ignore[attr-defined]


def _render_section_content(doc: _DocxDocument, content: str) -> None:
    """Render a section's content body. Each line becomes a paragraph;
    leading ``- `` is treated as a List Bullet style."""
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line:
            doc.add_paragraph()
            continue
        if line.startswith("- "):
            para = doc.add_paragraph(style="List Bullet")
            _emit_runs(para, line[2:])
        else:
            para = doc.add_paragraph()
            _emit_runs(para, line)


def _render_section_tree(
    doc: _DocxDocument, sections: Iterable[ReportSection], depth_offset: int = 0
) -> None:
    """Recursively render ReportSection tree.

    ``ReportSection.level`` is 1..3 (validated by the schema). DOCX
    heading levels max at 9 in python-docx, so the offset is safe.
    """
    for sec in sections:
        doc.add_heading(sec.title, level=min(9, sec.level + depth_offset))
        if sec.content:
            _render_section_content(doc, sec.content)
        if sec.subsections:
            _render_section_tree(doc, sec.subsections, depth_offset)


def _render_evidence_appendix(
    doc: _DocxDocument, bundle: EvidenceBundle
) -> None:
    """ADR-012 audit trail. Every evidence item gets one bulleted
    paragraph: ``- [EV-ID] Title — value unit @ location  (source: X)``.
    Empty bundles are still rendered with an explicit "no evidence"
    line — though :func:`export_docx` will never reach this branch
    (the draft generator already refuses zero-evidence reports)."""
    doc.add_heading("附录: 证据清单 / Evidence audit trail", level=1)
    if not bundle.evidence_items:
        doc.add_paragraph("(no evidence items in this bundle)")
        return
    for item in bundle.evidence_items:
        line = (
            f"- [{item.evidence_id}] {item.title} — "
            f"{_format_evidence_value(item)}  (source: {item.source})"
        )
        para = doc.add_paragraph(style="List Bullet")
        para.add_run(line[2:])  # strip leading "- " (style adds bullet)
        if item.source_file:
            sub = doc.add_paragraph(
                f"    file: {item.source_file}", style="Intense Quote"
            )
            for run in sub.runs:
                run.italic = True


def export_docx(
    report: ReportSpec,
    bundle: EvidenceBundle,
    *,
    output_path: Path,
) -> Path:
    """Materialise ``(report, bundle)`` to a DOCX at ``output_path``.

    Returns the resolved output path on success.

    Raises:
        ExportError: bundle linkage broken, an evidence_id cited in
            section content doesn't resolve in the bundle, or the
            output directory doesn't exist.
    """
    if report.evidence_bundle_id != bundle.bundle_id:
        raise ExportError(
            f"bundle linkage broken: report.evidence_bundle_id="
            f"{report.evidence_bundle_id!r} but bundle.bundle_id="
            f"{bundle.bundle_id!r}"
        )

    cited = find_cited_evidence_ids(report.sections)
    bundle_ids = {item.evidence_id for item in bundle.evidence_items}
    unresolved = cited - bundle_ids
    if unresolved:
        raise ExportError(
            f"section content cites evidence_id(s) {sorted(unresolved)!r} "
            f"that do not resolve in bundle {bundle.bundle_id!r} "
            f"(ADR-012). Bundle ids present: {sorted(bundle_ids)!r}."
        )

    if not output_path.parent.exists():
        raise ExportError(
            f"output_path parent {output_path.parent} does not exist; "
            "create it before calling export_docx (the exporter does "
            "not mkdir on the caller's behalf)."
        )

    doc = Document()
    doc.add_heading(report.title, level=0)
    info_lines = [
        f"Report ID: {report.report_id}",
        f"Project ID: {report.project_id}",
        f"Template: {report.template_id}",
        f"Generated: {report.generated_at.isoformat()}",
        f"Evidence bundle: {report.evidence_bundle_id}",
    ]
    for ln in info_lines:
        doc.add_paragraph(ln)

    _render_section_tree(doc, report.sections)
    _render_evidence_appendix(doc, bundle)

    doc.save(str(output_path))
    return output_path
