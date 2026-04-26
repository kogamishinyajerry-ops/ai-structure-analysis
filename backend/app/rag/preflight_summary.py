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


def _confidence_to_str(c: Any) -> str:
    """Coerce a confidence value to a lowercase string.

    R2 (post Codex R1 MEDIUM-1 on PR #63): the prior code did
    `c.value.lower()` which crashes when `.value` is an int (e.g.
    `Enum("...", auto)` produces int values). Wrapping in `str()`
    handles both string-backed and int-backed enums plus plain strings.
    """
    raw = c.value if hasattr(c, "value") else c
    return str(raw).lower()


def _md_escape(s: Any) -> str:
    """Best-effort markdown escape for free-text fields rendered into
    the preflight block.

    R2 (post Codex R1 MEDIUM-2 on PR #63): the rendered preflight goes
    into PR comments and agent prompts. A `notes` field like
    `## hi\\n- boom` used to inject a real heading and a real list
    item into the block. Strip newlines + escape the most damaging
    leading-line markers (#, -, *, >, |, `, [, ]). This is not a
    full sanitiser — it is a pragmatic guard against accidental
    markdown reshape, which is what we actually saw.
    """
    if s is None:
        return ""
    text = str(s)
    # Collapse newlines so a single field cannot start a new
    # markdown block.
    text = text.replace("\r", " ").replace("\n", " ")
    # Escape backticks (would close/open code spans inside lines).
    text = text.replace("`", "\\`")
    return text


def _format_quantity_line(q: Any) -> str:
    """One line per quantity. Robust to missing fields and adversarial
    free-text inputs (R2: markdown-escapes name / unit / location)."""
    name = _md_escape(getattr(q, "name", "?"))
    value = getattr(q, "value", float("nan"))
    unit = _md_escape(getattr(q, "unit", ""))
    location = _md_escape(getattr(q, "location", None) or "")
    confidence_str = _confidence_to_str(getattr(q, "confidence", "low"))

    value_str = f"{value:.4g}" if isinstance(value, float) else _md_escape(value)

    base = f"  - {name} = {value_str} {unit}".rstrip()
    if location:
        base += f" @ {location}"
    base += f"  ({confidence_str})"
    return base


def _aggregate_confidence(quantities: list[Any]) -> str:
    """Roll up per-quantity confidence into a single indicator."""
    if not quantities:
        return "n/a"
    levels = [_confidence_to_str(getattr(q, "confidence", "low")) for q in quantities]
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
    """Render the combined preflight block.

    R2 (post Codex R1 MEDIUM-2): case_id / verdict / fault_class /
    provider / notes are escaped before substitution to prevent free-
    text from reshaping the markdown structure when this block is
    surfaced in PR comments / agent prompts.
    """
    case_id_e = _md_escape(case_id)
    verdict_e = _md_escape(verdict)
    fault_e = _md_escape(fault_class)
    provider_e = _md_escape(provider)
    notes_e = _md_escape(notes)

    parts: list[str] = []
    parts.append(f"## Preflight — {case_id_e}")
    parts.append("")
    parts.append(
        f"**Verdict:** {verdict_e}    **Fault:** {fault_e}    "
        f"**Surrogate confidence:** {confidence_indicator}"
    )
    parts.append("")
    parts.append(f"### Surrogate predictions ({provider_e})")
    if quantity_lines:
        parts.extend(quantity_lines)
    else:
        parts.append("  _(no predictions)_")
    if notes_e:
        parts.append("")
        parts.append(f"  _notes:_ {notes_e}")
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

    # R2 (post Codex R1 LOW on PR #63): validate the duck-typed
    # `quantities` container. Pre-fix, `hint.quantities = "abc"` (a
    # string) was iterable and produced 3 bogus quantity lines —
    # silently nonsensical output. Explicitly reject strings/bytes,
    # accept None / list / tuple / generator / any other true iterable.
    raw_quantities = getattr(hint, "quantities", None)
    if raw_quantities is None:
        quantities: list[Any] = []
    elif isinstance(raw_quantities, (str, bytes)):
        raise ValueError(
            f"hint.quantities must be an iterable of quantity objects, "
            f"got a {type(raw_quantities).__name__} ({raw_quantities!r:.40})"
        )
    else:
        try:
            quantities = list(raw_quantities)
        except TypeError as e:
            raise ValueError(
                f"hint.quantities must be iterable, got {type(raw_quantities).__name__}: {e}"
            ) from e

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
