"""Reporting-only 4-question gate audit — FM-04a Phase 18 B (ADR-025 §2.2).

The Phase 11 ``_audit_four_question_gate`` in ``advisor_critique.py``
raises ``ValueError`` on any False / missing / extra / non-boolean
gate input — correct for Tier 1 advisor envelope construction, where
a False on ``advisor_only`` would mean the harness had drifted out of
advisor posture entirely (loud failure is the right move).

Phase 18 introduces a **sibling** helper that NEVER raises and instead
returns a structured :class:`GateAuditRecord`. The Tier 2 transition
needs a reporting-only path for envelopes that come from a real
solver run (Phase 18 A) rather than an LLM advisor critique — those
envelopes still want to **surface** the four-question gate state as
audit metadata for the reviewer, but should not refuse the envelope
on a False answer (the policy-vs-reporting split per ADR-025 §2.2).

The Phase 11 hard-raise function remains intact; this is additive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

FOUR_QUESTION_GATE_KEYS: Final[tuple[str, str, str, str]] = (
    "llm_offline_ok",
    "artifacts_user_owned",
    "trustgate_explains",
    "advisor_only",
)
"""Pinned identical to ``advisor_critique.FOUR_QUESTION_GATE_KEYS``.
Re-exposed here so this module is self-contained for consumers that
want the reporting-only path without importing the advisor critique
module (and its construction side effects)."""


@dataclass(frozen=True)
class GateAuditRecord:
    """Structured audit of a 4-question gate response.

    Attributes:
        all_true: ``True`` iff every required key is present, of bool
            type, and ``True``.
        true_keys: tuple of keys answered ``True``.
        false_keys: tuple of keys answered ``False``.
        missing_keys: tuple of required keys not present in the input.
        unknown_keys: tuple of input keys not in
            :data:`FOUR_QUESTION_GATE_KEYS`.
        non_boolean_keys: tuple of input keys whose value was not a
            bool (e.g., ``None`` or a string truthy value).
        gate_raw: the input gate dict (frozen via tuple copy of items
            to preserve provenance without exposing mutation).
    """

    all_true: bool
    true_keys: tuple[str, ...]
    false_keys: tuple[str, ...]
    missing_keys: tuple[str, ...]
    unknown_keys: tuple[str, ...]
    non_boolean_keys: tuple[str, ...]
    gate_raw: tuple[tuple[str, Any], ...]


def build_gate_audit_record(gate: dict[str, Any]) -> GateAuditRecord:
    """Audit a 4-question gate dict without raising on any defect.

    Returns a :class:`GateAuditRecord` summarising:
      * which required keys are present + answered True / False
      * which required keys are missing
      * which input keys are unknown (not in the required set)
      * which keys have non-bool values

    The function NEVER raises; defects are returned as structured
    metadata for the caller to render (or, if the caller still wants
    loud failure, the caller can ``raise`` on
    ``not record.all_true``).

    Per ADR-025 §2.2 this is the reporting-only sibling of the Phase
    11 ``_audit_four_question_gate``. New consumers (Tier 2 envelope
    construction) call here; the Phase 11 hard-raise function remains
    in place for advisor critique envelopes that still want loud
    failure semantics.
    """
    missing: tuple[str, ...] = tuple(
        k for k in FOUR_QUESTION_GATE_KEYS if k not in gate
    )
    unknown: tuple[str, ...] = tuple(
        k for k in gate if k not in FOUR_QUESTION_GATE_KEYS
    )
    non_bool: tuple[str, ...] = tuple(
        k
        for k in FOUR_QUESTION_GATE_KEYS
        if k in gate and not isinstance(gate[k], bool)
    )
    true_keys: tuple[str, ...] = tuple(
        k
        for k in FOUR_QUESTION_GATE_KEYS
        if k in gate and isinstance(gate[k], bool) and gate[k] is True
    )
    false_keys: tuple[str, ...] = tuple(
        k
        for k in FOUR_QUESTION_GATE_KEYS
        if k in gate and isinstance(gate[k], bool) and gate[k] is False
    )
    all_true = (
        not missing
        and not non_bool
        and len(true_keys) == len(FOUR_QUESTION_GATE_KEYS)
    )
    return GateAuditRecord(
        all_true=all_true,
        true_keys=true_keys,
        false_keys=false_keys,
        missing_keys=missing,
        unknown_keys=unknown,
        non_boolean_keys=non_bool,
        gate_raw=tuple((k, v) for k, v in gate.items()),
    )


__all__ = [
    "FOUR_QUESTION_GATE_KEYS",
    "GateAuditRecord",
    "build_gate_audit_record",
]
