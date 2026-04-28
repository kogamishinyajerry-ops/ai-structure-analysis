"""PASS / FAIL verdict for the engineer-signs-DOCX wedge
(RFC-001 W6c / ADR-020 §"What this does NOT decide" — the
verdict step lives here, NOT in the allowable-stress lookup).

Given σ_max (peak Mises from Layer-3) and [σ] (allowable from
``allowable_stress.compute_allowable_stress``), compute:

    SF = [σ] / σ_max

and return a :class:`Verdict` dataclass that the W6c.2 DOCX
template will render into the "评定结论" section. This module
is **pure compute**: no DOCX, no LLM, no I/O. The deterministic
PASS/FAIL string lives in the template; this layer only emits
the numeric truth.

Per RFC-001 §2.4 rule 1 ("LLM 不接触数字"), the verdict number
must come from this function — never from an LLM completion.
The template may invoke an LLM only to micro-edit phrasing, with
the four required evidence items (σ_max, [σ], SF, threshold)
fed in as immutable inputs.

Refusal contract:

* ``ValueError`` if ``sigma_max`` or ``sigma_allow`` is not finite,
  not positive, or NaN. A non-positive σ_max is structurally
  meaningless (Mises is non-negative; zero means "no stress
  state extracted" which is a Layer-3 bug, not a PASS).
* ``ValueError`` if ``threshold`` is ``< 1.0`` or non-finite. The
  roadmap default is 1.0 (regulatory floor — GB 150 / ASME VIII
  Div 2 build SF into [σ]); users may set higher (e.g. 1.5 for
  institute-internal margin), never lower. Codex R1 on PR #99
  caught an earlier `> 0` guard that let ``threshold=0.5`` slip
  through and return PASS for SF=0.6.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Literal

__all__ = [
    "Verdict",
    "VerdictKind",
    "compute_verdict",
    "DEFAULT_THRESHOLD",
]


VerdictKind = Literal["PASS", "FAIL"]


DEFAULT_THRESHOLD: Final[float] = 1.0
"""Default safety-factor threshold per RFC-001-W6-roadmap.md §5
question 3 default. ``SF >= 1.0`` is the **regulatory** threshold
(GB 150 / ASME VIII Div 2 already build their own safety factors
into [σ] = min(σ_y/1.5, σ_u/3.0); requiring SF >= 1.0 on top is
*not* a doubled safety factor, it is the audit-floor "[σ]
covers σ_max with no margin"). Engineers wanting institute-internal
extra margin can pass a higher threshold per call."""


@dataclass(frozen=True)
class Verdict:
    """Result of one verdict computation.

    Field semantics:

    * ``kind`` — ``"PASS"`` iff ``safety_factor >= threshold``,
      else ``"FAIL"``. The boundary case ``SF == threshold``
      counts as PASS — RFC-001-W6-roadmap.md §5 question 3
      explicitly aligns this with the regulatory floor (the codes
      themselves treat SF=1.0 as the boundary of acceptability).
    * ``safety_factor`` — ``[σ] / σ_max``. Always > 0 because the
      constructor refuses non-positive inputs.
    * ``margin_pct`` — ``(safety_factor / threshold - 1) * 100``,
      i.e. how many percent of headroom (negative) or excess
      (positive) the verdict has against the threshold. **Not**
      ``(safety_factor - 1) * 100`` — the percent surfaces in the
      DOCX evaluation conclusion, and the engineer is reading it
      against *their* threshold, not against 1.0.
    * ``inputs`` — frozen view of the four numbers that produced
      the verdict, for the DOCX substitution line (W6c.2). Stored
      verbatim so the renderer doesn't have to re-parse them.

    The dataclass is frozen + the inputs tuple is immutable
    (Python tuples are immutable by construction); a future
    addition of mutable fields must preserve this contract.
    """

    kind: VerdictKind
    safety_factor: float
    margin_pct: float
    inputs: tuple[tuple[str, float], ...]


def _check_positive_finite(name: str, value: float) -> None:
    """Reject NaN / inf / non-positive at the boundary.

    Reused for σ_max and σ_allow. ``threshold`` has its own
    validator (:func:`_check_threshold`) because it has a stricter
    floor of 1.0, not just ``> 0``.
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if value <= 0:
        raise ValueError(
            f"{name} must be positive, got {value!r} "
            f"(non-positive values have no physical meaning here — "
            f"σ_max=0 means no stress was extracted, not a PASS)"
        )


def _check_threshold(value: float) -> None:
    """Reject non-finite, non-numeric, or `< 1.0` thresholds.

    The contract floor is 1.0: GB 150 / ASME VIII Div 2 already
    build their safety factors into [σ], so a threshold below the
    regulatory floor of SF=1.0 has no physical meaning. Codex R1
    on PR #99 demonstrated that an earlier `> 0` guard accepted
    `threshold=0.5` and returned PASS for SF=0.6, undermining the
    audit-floor semantics — hence this stricter validator.

    Engineers wanting institute-internal extra margin can pass any
    threshold ≥ 1.0; the upper bound is open.
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"threshold must be a real number, got {type(value).__name__}")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"threshold must be finite, got {value!r}")
    if value < 1.0:
        raise ValueError(
            f"threshold must be >= 1.0 (regulatory-floor semantics — "
            f"GB 150 / ASME VIII Div 2 already build SF into [σ]; "
            f"a threshold below 1.0 has no physical meaning), got "
            f"{value!r}"
        )


def compute_verdict(
    sigma_max: float,
    sigma_allow: float,
    threshold: float = DEFAULT_THRESHOLD,
) -> Verdict:
    """Compute PASS / FAIL verdict for an engineer-signed report.

    Both stresses must be in **the same unit** (typically MPa
    under the project's si-mm convention). This function does NOT
    enforce unit consistency — that's the caller's job, since the
    units come from the upstream Material / Layer-3 / Layer-1
    chain. A future linting step could compare
    ``allowable_stress.AllowableStress.code_standard`` against the
    Material's unit system to surface a mismatch warning, but
    that's a W6c.2 DOCX-renderer concern, not this function's.

    The threshold default of 1.0 matches the regulatory floor.
    Setting threshold=1.5 (institute-internal extra margin) flips
    SF=1.2 from PASS to FAIL even though regulatory minimum is
    met. This is intentional — engineers choose their own margin.

    Refusals:

    * sigma_max / sigma_allow non-finite / non-positive → ``ValueError``
    * threshold < 1.0 (regulatory floor) or non-finite → ``ValueError``

    Returns a frozen :class:`Verdict` ready for DOCX rendering.
    """
    _check_positive_finite("sigma_max", sigma_max)
    _check_positive_finite("sigma_allow", sigma_allow)
    _check_threshold(threshold)

    safety_factor = sigma_allow / sigma_max
    kind: VerdictKind = "PASS" if safety_factor >= threshold else "FAIL"
    margin_pct = (safety_factor / threshold - 1.0) * 100.0

    inputs: tuple[tuple[str, float], ...] = (
        ("sigma_max", float(sigma_max)),
        ("sigma_allow", float(sigma_allow)),
        ("safety_factor", safety_factor),
        ("threshold", float(threshold)),
    )
    return Verdict(
        kind=kind,
        safety_factor=safety_factor,
        margin_pct=margin_pct,
        inputs=inputs,
    )
