"""TaskSpec — RFC-001 §6.2 slim.

Keeps only the five fields the MVP wedge needs: task ID, human name,
result-file path, unit system, and standards citations. Mesh
specification, solver settings, and acceptance criteria from the
Sprint-2 schema have been deleted.

Why slim: the MVP report Copilot consumes a *result* file (.frd / .rst /
.bdf / odb-export.h5) and writes a static-strength report against
standards. It does not own the upstream mesh / solver setup, and it
does not gate on user-authored acceptance criteria — the standards
citations are the only acceptance vocabulary it speaks.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from ..core.types import UnitSystem


class TaskSpec(BaseModel):
    """The minimum identity of a single MVP analysis task.

    ``citations`` is the list of standards / handbooks / company specs
    the report must measure the result against (e.g. ``["GB 50017-2017",
    "ASME VIII Div 2"]``). The closed-set ``UnitSystem`` (RFC ADR-003)
    must be set explicitly — never inferred — and ``UNKNOWN`` is the
    legitimate placeholder until the wizard resolves it.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., description="任务唯一标识符")
    name: str = Field(..., description="任务名称")
    result_file: str = Field(..., description="求解器结果文件路径 (.frd/.rst/.bdf/.h5)")
    unit_system: UnitSystem = Field(
        default=UnitSystem.UNKNOWN,
        description="结果文件单位制；UNKNOWN 时由 wizard 强制用户解决 (ADR-003)",
    )
    citations: List[str] = Field(
        default_factory=list,
        description="规范 / 手册 / 企业标准引用列表",
    )
