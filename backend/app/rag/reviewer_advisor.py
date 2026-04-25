"""Reviewer-side RAG advisor — surfaces relevant ADRs / FailurePatterns / theory snippets
given a Reviewer verdict and (optionally) a fault classification (P1-05b).

This module is the *consumer* seam for `KnowledgeBase.query`. It lets the
Reviewer (or any caller working with a SimState verdict) ask:

    "Given that we just classified this run as a SOLVER_CONVERGENCE failure,
     what does the corpus say about that?"

The advisor turns a verdict + fault into a query string, calls the KB, and
returns a structured `ReviewerAdvice` payload that:

  * lists the top-k retrieved chunks with full metadata
  * groups them by source label (project-adr-fp vs gs-theory) so the caller
    can prioritise governance hits over theory hits when both are present
  * yields a one-line `summary` for log/PR-comment surfaces

This PR does NOT modify `agents/reviewer.py` (HF1.3-adjacent) — wiring the
advisor into the Reviewer's run loop is a follow-up. Today the seam is
importable + testable, ready to be called.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from backend.app.rag.knowledge_base import KnowledgeBase
from backend.app.rag.schemas import RetrievalResult

# We import FaultClass lazily by string to avoid a hard top-level dep
# on schemas/sim_state.py for callers who only have a verdict string.

# Fault → query-text seeds. These are deliberately concise; the embedder
# does the heavy lifting of mapping to ADR/FP language.
FAULT_QUERY_SEEDS: dict[str, str] = {
    "geometry_invalid": "geometry validation invalid topology repair",
    "mesh_jacobian": "mesh jacobian negative element distortion quality",
    "mesh_resolution": "mesh resolution refinement convergence study",
    "solver_convergence": "solver convergence Newton residual tolerance",
    "solver_timestep": "solver timestep increment cutback adaptive",
    "solver_syntax": "CalculiX input deck syntax keyword",
    "reference_mismatch": "expected results deviation reference mismatch",
    "unknown": "diagnostic guidance",
    "none": "best practices",
}

# Verdict tokens that should bias the query toward governance docs.
GOVERNANCE_BIASING_VERDICTS = {"Reject", "Re-run", "Needs Review"}


@dataclass(frozen=True)
class ReviewerAdvice:
    """Structured advisor output."""

    query: str
    verdict: str
    fault_class: str
    results: tuple[RetrievalResult, ...] = field(default_factory=tuple)
    grouped_by_source: dict[str, tuple[RetrievalResult, ...]] = field(default_factory=dict)
    summary: str = ""

    def is_empty(self) -> bool:
        return len(self.results) == 0

    def top_governance_hit(self) -> RetrievalResult | None:
        for r in self.results:
            if r.chunk.source == "project-adr-fp":
                return r
        return None

    def top_theory_hit(self) -> RetrievalResult | None:
        for r in self.results:
            if r.chunk.source == "gs-theory":
                return r
        return None


def _build_query(verdict: str, fault_class: str) -> str:
    """Compose a query string from verdict + fault."""
    fault_seed = FAULT_QUERY_SEEDS.get(fault_class, fault_class.replace("_", " "))
    if verdict in GOVERNANCE_BIASING_VERDICTS:
        return f"{verdict} {fault_seed} ADR FailurePattern"
    return f"{verdict} {fault_seed}"


def _summarise(results: tuple[RetrievalResult, ...], verdict: str, fault_class: str) -> str:
    if not results:
        return f"No corpus hits for verdict={verdict} fault={fault_class}."
    top = results[0]
    label = top.chunk.source
    return (
        f"verdict={verdict} fault={fault_class}: "
        f"{len(results)} hit(s); top=[{label}] {top.chunk.chunk_id} (score={top.score:.3f})"
    )


def advise(
    kb: KnowledgeBase,
    verdict: str,
    fault_class: str = "unknown",
    k: int = 5,
    source_filter: str | None = None,
) -> ReviewerAdvice:
    """Run a verdict-driven query against the KB and group results by source.

    Args:
        kb: a populated KnowledgeBase. Caller is responsible for ingest.
        verdict: a Reviewer verdict string (e.g. "Reject", "Accept with Note").
        fault_class: a FaultClass value as a string (e.g. "solver_convergence").
            Defaults to "unknown" when no classification is available.
        k: number of retrieved chunks (default 5).
        source_filter: restrict to one source label; None = all.

    Returns:
        ReviewerAdvice (frozen dataclass). `is_empty()` distinguishes
        "no corpus" from "no relevant hits".
    """
    if not isinstance(verdict, str) or not verdict.strip():
        raise ValueError("verdict must be a non-empty string")
    if k <= 0:
        raise ValueError("k must be a positive integer")

    query = _build_query(verdict, fault_class)
    raw_results = kb.query(query, k=k, source_filter=source_filter)
    results = tuple(raw_results)

    grouped: dict[str, list[RetrievalResult]] = defaultdict(list)
    for r in results:
        grouped[r.chunk.source].append(r)
    grouped_frozen = {src: tuple(rs) for src, rs in grouped.items()}

    return ReviewerAdvice(
        query=query,
        verdict=verdict,
        fault_class=fault_class,
        results=results,
        grouped_by_source=grouped_frozen,
        summary=_summarise(results, verdict, fault_class),
    )
