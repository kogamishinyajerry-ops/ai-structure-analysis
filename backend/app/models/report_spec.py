"""ReportSpec — RFC-001 §6.2 slim.

Keeps only project metadata, template ID, section list, generated_at,
and the EvidenceBundle ID. Approval flow, reviewer roster, and status
tracking from the Sprint-2 schema have been deleted (the MVP wedge
relies on the engineer's own signature and on the company's existing
review channel — re-implementing those is out of scope per RFC §2.3).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReportSection(BaseModel):
    """A single hierarchical section of a generated report."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="章节标题")
    level: int = Field(default=1, ge=1, le=3, description="章节级别 1-3")
    content: Optional[str] = Field(None, description="章节正文 (Markdown)")
    subsections: List["ReportSection"] = Field(
        default_factory=list,
        description="子章节列表",
    )


class ReportSpec(BaseModel):
    """The minimum identity of a generated MVP report.

    ``evidence_bundle_id`` links to the ``EvidenceBundle`` whose items
    every claim in the rendered draft must trace back to (RFC ADR-012).
    Drafts without a populated bundle MUST NOT be exportable.
    """

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., description="报告唯一标识符")
    project_id: str = Field(..., description="所属项目 ID")
    title: str = Field(..., description="报告标题")
    template_id: str = Field(..., description="模板 ID (e.g. equipment_foundation_static)")
    sections: List[ReportSection] = Field(
        default_factory=list,
        description="报告章节树",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="生成时间",
    )
    evidence_bundle_id: str = Field(..., description="关联 EvidenceBundle ID")


ReportSection.model_rebuild()
