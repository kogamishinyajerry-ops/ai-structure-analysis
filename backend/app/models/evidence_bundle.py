"""EvidenceBundle — RFC-001 §6.2 enhancement.

Every claim in a generated report must trace back to an
``EvidenceItem`` in a bundle (ADR-012). The Sprint-2 ``data: dict``
field is replaced with a discriminated union of three shapes
(simulation / reference / analytical) so the Layer-4 template engine
can pattern-match instead of probing dict keys.

``field_metadata`` (Layer-2 provenance) and ``derivation`` (DAG of
upstream evidence IDs) make the chain auditable. ``add_evidence``
enforces evidence-ID uniqueness and referential integrity of the
derivation DAG.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.types import FieldMetadata


class EvidenceType(str, Enum):
    """Discriminator for the ``data`` union below."""

    SIMULATION = "simulation"
    REFERENCE = "reference"
    ANALYTICAL = "analytical"


class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PENDING = "pending"


class _EvidencePayloadBase(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    value: float
    unit: str


class SimulationEvidence(_EvidencePayloadBase):
    """A scalar extracted from a solver result file."""

    kind: Literal["simulation"] = "simulation"
    location: Optional[str] = Field(None, description="节点 ID / 单元 ID / 位置标签")


class ReferenceEvidence(_EvidencePayloadBase):
    """A value cited from a standard, handbook, or company spec."""

    kind: Literal["reference"] = "reference"
    source_document: str = Field(..., description="规范号 / 手册名 / 文件号")
    citation_anchor: Optional[str] = Field(None, description="章节号 / 表号 / 公式号")


class AnalyticalEvidence(_EvidencePayloadBase):
    """A value computed from a closed-form formula on other evidence."""

    kind: Literal["analytical"] = "analytical"
    formula: str = Field(..., description="公式 (LaTeX 或纯文本)")
    inputs: Dict[str, float] = Field(default_factory=dict, description="入参映射")


EvidencePayload = Annotated[
    Union[SimulationEvidence, ReferenceEvidence, AnalyticalEvidence],
    Field(discriminator="kind"),
]


class EvidenceItem(BaseModel):
    """One atomic piece of evidence inside a bundle.

    ``derivation`` lists the ``evidence_id``s of items this one is
    derived from (e.g. an analytical evidence depends on two simulation
    evidences plus one reference). The list MUST stay acyclic and every
    referenced ID MUST resolve inside the same bundle — both invariants
    are enforced by ``EvidenceBundle.add_evidence``.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    evidence_id: str = Field(..., description="证据项 ID (bundle 内唯一)")
    evidence_type: EvidenceType = Field(..., description="证据类型")
    title: str = Field(..., description="证据标题")
    description: Optional[str] = Field(None, description="人类可读描述")
    data: EvidencePayload = Field(..., description="证据数据载荷 (discriminated union)")
    field_metadata: Optional[FieldMetadata] = Field(
        None,
        description="Layer-2 来源元数据 (CanonicalField + 单位 + 文件等),"
        " 仅 simulation 类证据期望填写",
    )
    derivation: Optional[List[str]] = Field(
        None,
        description="此证据依赖的上游 evidence_id 列表 (DAG)",
    )
    source: str = Field(..., description="数据来源标签 (solver name / standard ID / formula author)")
    source_file: Optional[str] = Field(None, description="源文件路径")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verification_status: Optional[VerificationStatus] = None
    verification_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("derivation")
    @classmethod
    def _derivation_no_self_ref(
        cls, value: Optional[List[str]], info: Any
    ) -> Optional[List[str]]:
        if value is None:
            return value
        if len(value) != len(set(value)):
            raise ValueError("derivation list contains duplicates")
        own = info.data.get("evidence_id")
        if own and own in value:
            raise ValueError("derivation may not reference the item's own evidence_id")
        return value


class EvidenceBundle(BaseModel):
    """Ordered set of EvidenceItems backing one report.

    Invariants:
      * Every ``evidence_id`` in ``evidence_items`` is unique.
      * If item ``X`` lists ``Y`` in its ``derivation``, then ``Y`` already
        appears in ``evidence_items`` *before* ``X`` (acyclic DAG, append-only).

    Both are enforced by :meth:`add_evidence`. Direct mutation of
    ``evidence_items`` bypasses validation — don't do it.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bundle_id: str = Field(..., description="证据包 ID")
    task_id: str = Field(..., description="关联 TaskSpec.task_id")
    title: str = Field(..., description="证据包标题")
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    verification_summary: Optional[str] = None
    overall_status: Optional[VerificationStatus] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_evidence(self, evidence: EvidenceItem) -> None:
        """Append an item, enforcing uniqueness + derivation referential integrity.

        Raises:
            ValueError: if ``evidence_id`` already exists in this bundle,
                or if any ID in ``evidence.derivation`` is not yet present.
        """
        existing_ids = {item.evidence_id for item in self.evidence_items}
        if evidence.evidence_id in existing_ids:
            raise ValueError(
                f"evidence_id {evidence.evidence_id!r} already in bundle "
                f"{self.bundle_id!r}"
            )
        if evidence.derivation:
            missing = [eid for eid in evidence.derivation if eid not in existing_ids]
            if missing:
                raise ValueError(
                    f"evidence {evidence.evidence_id!r} derives from unknown IDs: "
                    f"{missing!r}"
                )
        self.evidence_items.append(evidence)
        self.updated_at = datetime.utcnow()

    def get_evidence_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        for item in self.evidence_items:
            if item.evidence_id == evidence_id:
                return item
        return None

    def get_evidence_by_type(self, evidence_type: EvidenceType) -> List[EvidenceItem]:
        return [item for item in self.evidence_items if item.evidence_type == evidence_type]
