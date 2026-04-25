"""Preflight summary — combines a SurrogateHint with a ReviewerAdvice into
one rendered preflight report (P1-08).

Sits at the integration seam between two recently-built primitives:

  * `agents.surrogate_adapter.predict_for_simplan` → SurrogateHint
    (empirical prediction, e.g. "max_displacement = 1.234 mm @ free_end")
  * `backend.app.rag.reviewer_advisor.advise`      → ReviewerAdvice
    (corpus context, e.g. top FailurePatterns + theory snippets)

The Reviewer (Phase 1.5) will eventually call both — and want a single
rendered block to attach to its log/PR comment / agent prompt. This
module is that block.

Design choice — duck-typed `hint` parameter:

  We deliberately do NOT import SurrogateHint at module-load time. The
  surrogate stack lives in `agents/` and the rag stack lives in
  `backend/app/rag/`. Forcing a hard dep here would create an import
  cycle through the schema layer.

  Instead, the `hint` parameter is duck-typed: any object exposing
  `.case_id` (str), `.provider` (str), `.quantities` (iterable of
  objects with `.name`, `.value`, `.unit`, `.confidence`) and `.notes`
  (str) is accepted. SurrogateHint satisfies this; tests use a minimal
  stub with the same shape.

  Callers who already have a SurrogateHint just pass it. Callers in
  environments without `agents.surrogate` (e.g. tests, future agents
  that produce hint-shaped data from a different source) construct
  their own duck-type and pass that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.rag.reviewer_advisor import ReviewerAdvice


@dataclass(frozen=True)
class PreflightSummary:
    """Combined surrogate + advisor rendering."""

    case_id: str
    verdict: str
    fault_class: str
    quantity_lines: tuple[str, ...] = field(default_factory=tuple)
    advice_lines: tuple[str, ...] = field(default_factory=tuple)
    confidence_indicator: str = "n/a"
    markdown: str = ""

    def has_quantities(self) -> bool:
        return len(self.quantity_lines) > 0

    def has_advice(self) -> bool:
        return len(self.advice_lines) > 0

    def is_empty(self) -> bool:
        return not self.has_quantities() and not self.has_advice()


def _format_quantity_line(q: Any) -> str:
    """One line per quantity. Robust to missing fields."""
    name = getattr(q, "name", "?")
    value = getattr(q, "value", float("nan"))
    unit = getattr(q, "unit", "")
    location = getattr(q, "location", None) or ""
    confidence = getattr(q, "confidence", "low")
    # confidence may be an enum (HintConfidence.LOW) or a plain str
    confidence_str = (
        confidence.value if hasattr(confidence, "value") else str(confidence)
    ).lower()

    if isinstance(value, float):
        value_str = f"{value:.4g}"
    else:
        value_str = str(value)

    base = f"  - {name} = {value_str} {unit}".rstrip()
    if location:
        base += f" @ {location}"
    base += f"  ({confidence_str})"
    return base


def _aggregate_confidence(quantities: list[Any]) -> str:
    """Roll up per-quantity confidence into a single indicator."""
    if not quantities:
        return "n/a"
    levels = []
    for q in quantities:
        c = getattr(q, "confidence", "low")
        c_str = (c.value if hasattr(c, "value") else str(c)).lower()
        levels.append(c_str)
    if all(level == "high" for level in levels):
        return "high"
    if all(level in ("high", "medium") for level in levels):
        return "medium"
    return "low"


def _format_advice_line(rank: int, score: float, source: str, chunk_id: str, snippet: str) -> str:
    snippet = snippet.replace("\n", " ").strip()
    if len(snippet) > 100:
        snippet = snippet[:97] + "..."
    return f"  - #{rank + 1} [{source}] {chunk_id} (score={score:.3f})  {snippet}"


def _render_markdown(
    case_id: str,
    verdict: str,
    fault_class: str,
    provider: str,
    quantity_lines: list[str],
    advice_lines: list[str],
    confidence_indicator: str,
    notes: str,
) -> str:
    parts: list[str] = []
    parts.append(f"## Preflight — {case_id}")
    parts.append("")
    parts.append(f"**Verdict:** {verdict}    **Fault:** {fault_class}    "
                 f"**Surrogate confidence:** {confidence_indicator}")
    parts.append("")
    parts.append(f"### Surrogate predictions ({provider})")
    if quantity_lines:
        parts.extend(quantity_lines)
    else:
        parts.append("  _(no predictions)_")
    if notes:
        parts.append("")
        parts.append(f"  _notes:_ {notes}")
    parts.append("")
    parts.append("### Corpus advice")
    if advice_lines:
        parts.extend(advice_lines)
    else:
        parts.append("  _(no corpus hits)_")
    return "\n".join(parts).rstrip() + "\n"


def combine(
    hint: Any,
    advice: ReviewerAdvice,
    *,
    max_advice_lines: int = 3,
) -> PreflightSummary:
    """Combine a hint + advice into a rendered preflight summary.

    Args:
        hint: a SurrogateHint or any object exposing the duck-type contract
              (`.case_id`, `.provider`, `.quantities`, `.notes`).
              Each `.quantities[i]` must expose `.name`, `.value`, `.unit`,
              `.confidence`, and optionally `.location`.
        advice: a ReviewerAdvice from `reviewer_advisor.advise`.
        max_advice_lines: cap the number of advice lines shown (default 3).
                          0 disables (shows all).

    Returns:
        PreflightSummary (frozen dataclass) with quantity_lines,
        advice_lines, confidence_indicator, and a rendered `markdown`
        block suitable for attaching to logs / PR comments / agent
        prompts.
    """
    if max_advice_lines < 0:
        raise ValueError("max_advice_lines must be >= 0")

    case_id = getattr(hint, "case_id", "<unknown-case>")
    provider = getattr(hint, "provider", "<unknown-provider>")
    notes = getattr(hint, "notes", "") or ""
    quantities = list(getattr(hint, "quantities", []) or [])

    quantity_lines = tuple(_format_quantity_line(q) for q in quantities)
    confidence_indicator = _aggregate_confidence(quantities)

    advice_results = advice.results
    if max_advice_lines > 0:
        advice_results = advice_results[:max_advice_lines]
    advice_lines = tuple(
        _format_advice_line(r.rank, r.score, r.chunk.source, r.chunk.chunk_id, r.chunk.text)
        for r in advice_results
    )

    md = _render_markdown(
        case_id=case_id,
        verdict=advice.verdict,
        fault_class=advice.fault_class,
        provider=provider,
        quantity_lines=list(quantity_lines),
        advice_lines=list(advice_lines),
        confidence_indicator=confidence_indicator,
        notes=notes,
    )

    return PreflightSummary(
        case_id=case_id,
        verdict=advice.verdict,
        fault_class=advice.fault_class,
        quantity_lines=quantity_lines,
        advice_lines=advice_lines,
        confidence_indicator=confidence_indicator,
        markdown=md,
    )
