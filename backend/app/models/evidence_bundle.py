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
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..core.types import (
    CanonicalField,
    ComponentType,
    FieldLocation,
    FieldMetadata,
    UnitSystem,
)


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

    @model_validator(mode="after")
    def _check_kind_consistency(self) -> "EvidenceItem":
        """Tie ``evidence_type`` to ``data.kind`` so the two discriminators
        cannot disagree. Without this an item can validate as
        ``evidence_type=REFERENCE`` while carrying ``SimulationEvidence``,
        which silently splits ``get_evidence_by_type`` from any
        ``data.kind``-based dispatch downstream (Codex R1 finding HIGH-1).
        """
        expected_kind = {
            EvidenceType.SIMULATION: "simulation",
            EvidenceType.REFERENCE: "reference",
            EvidenceType.ANALYTICAL: "analytical",
        }[self.evidence_type]
        if self.data.kind != expected_kind:
            raise ValueError(
                f"evidence_type {self.evidence_type.value!r} does not match "
                f"data.kind {self.data.kind!r}"
            )
        return self


class EvidenceBundle(BaseModel):
    """Ordered set of EvidenceItems backing one report.

    Invariants:
      * Every ``evidence_id`` in ``evidence_items`` is unique.
      * If item ``X`` lists ``Y`` in its ``derivation``, then ``Y`` already
        appears in ``evidence_items`` *before* ``X`` (acyclic DAG, append-only).

    Enforced both by :meth:`add_evidence` (append-time) and by a
    bundle-level ``model_validator`` that runs on every construction —
    so loading a bundle from persisted JSON / dict cannot smuggle in
    duplicates, forward references, or cycles.
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

    @model_validator(mode="after")
    def _check_evidence_items_invariants(self) -> "EvidenceBundle":
        """Re-check uniqueness + topological order on every construction.

        Without this the constructor accepts duplicate IDs, forward
        references, and even cycles when ``evidence_items`` is passed
        as a kwarg or hydrated from JSON (Codex R1 finding HIGH-2).
        """
        seen_ids: set[str] = set()
        for item in self.evidence_items:
            if item.evidence_id in seen_ids:
                raise ValueError(
                    f"duplicate evidence_id {item.evidence_id!r} in bundle "
                    f"{self.bundle_id!r}"
                )
            if item.derivation:
                missing = [eid for eid in item.derivation if eid not in seen_ids]
                if missing:
                    raise ValueError(
                        f"item {item.evidence_id!r} derivation references "
                        f"unknown / not-yet-seen IDs: {missing!r}"
                    )
            seen_ids.add(item.evidence_id)
        return self

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


_FIELD_METADATA_TYPES = {
    "CanonicalField": CanonicalField,
    "ComponentType": ComponentType,
    "FieldLocation": FieldLocation,
    "Path": Path,
    "Union": Union,
    "UnitSystem": UnitSystem,
}

# Pydantic v2 does not always resolve the nested stdlib dataclass
# annotations on FieldMetadata when evidence models are imported through
# package re-exports. Rebuild once with the exact Layer-2 namespace so an
# empty EvidenceBundle is constructible without call-site workarounds.
EvidenceItem.model_rebuild(_types_namespace=_FIELD_METADATA_TYPES)
EvidenceBundle.model_rebuild(_types_namespace=_FIELD_METADATA_TYPES)
