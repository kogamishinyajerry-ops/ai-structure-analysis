"""Surrogate hint schema (P1-07).

Surrogate models (FNO, DeepONet, simpler MLPs, etc.) provide
**informational hints** to the agent pipeline — *never* validation
truth. Per Notion task `AI-FEA-P1-07 surrogate hook (FNO/DeepONet
只做提示，不做验收)` and ADR-002 (CalculiX is the only numerical truth
source).

Hints flow:

    Architect/Geometry → SurrogateProvider.predict(spec) → SurrogateHint
                              ↓
                         injected into prompt context for the next agent
                              ↓
                         CalculiX still validates — hint is informational only

If a hint contradicts the CalculiX result, the CalculiX result wins
and the hint goes into a discrepancy log for surrogate retraining.
The hint never gates merge / acceptance.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HintConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HintQuantity(BaseModel):
    """One predicted quantity with units + confidence band.

    Units follow the same convention as `expected_results.json`
    (mm/N/MPa for solid, m/N/Pa for civil — matches each GS doc).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., description="quantity name, e.g. 'max_displacement', 'sigma_vm_max'")
    value: float
    unit: str = Field(..., description="unit string verbatim, e.g. 'mm', 'MPa'")
    location: str | None = Field(
        default=None,
        description="optional spatial reference, e.g. 'free_end', 'hole_edge'",
    )
    confidence: HintConfidence = Field(
        default=HintConfidence.LOW,
        description=(
            "self-rated confidence by the surrogate; LOW for placeholder/stub providers, "
            "MEDIUM/HIGH require validated training-error bounds in the model card"
        ),
    )


class SurrogateHint(BaseModel):
    """Informational prediction from a surrogate model.

    Treated as advisory context for the agent pipeline. Never used to
    accept/reject a CalculiX result — that role belongs to the GS
    comparator + reviewer agent (ADR-004).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(..., description="case under analysis (matches SimPlan.case_id)")
    provider: str = Field(
        ...,
        description=(
            "provider id, e.g. 'placeholder-mlp@v0', 'fno-2d@v1', 'deeponet-cantilever@v2'. "
            "Mirrors the model card identifier."
        ),
    )
    quantities: list[HintQuantity] = Field(default_factory=list)
    notes: str = Field(
        default="",
        description="freeform diagnostic from the provider (e.g. extrapolation warnings)",
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="provider-specific data (raw outputs, intermediate features, etc.)",
    )

    def to_prompt_block(self) -> str:
        """Format the hint as a markdown block for inclusion in agent prompts."""
        if not self.quantities:
            return f"_Surrogate hint ({self.provider}): no predictions._"
        lines = [
            f"**Surrogate hint** (provider: `{self.provider}` — informational only, not validation)",
            "",
        ]
        for q in self.quantities:
            loc = f" @ {q.location}" if q.location else ""
            lines.append(f"- `{q.name}`{loc}: {q.value} {q.unit} (confidence: {q.confidence.value})")
        if self.notes:
            lines.append("")
            lines.append(f"_{self.notes}_")
        return "\n".join(lines)
