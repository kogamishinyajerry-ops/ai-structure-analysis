"""Claim-tier SSOT — FM-04a Phase 18 B (ADR-025).

A **single** module that decides, for any case_id, which tier its
envelopes should claim. Two values per ADR-025 §2:

* ``"tier_1_candidate"`` — synthetic fixture data; no real solver
  invocation; no analytical cross-check.
* ``"tier_2_validated"`` — real ``ccx`` subprocess produced the result
  AND the envelope cites an analytical cross-check verdict.

Phases 1-17 hard-coded ``"Tier 1 engineering candidate"`` (the human-
readable string) inline across many reporting modules. Phase 18 B
introduces this SSOT but does **not** rip out those inline strings —
they remain correct for the cases that haven't yet been promoted to
``tier_2_validated``. New consumers that want tier-aware behavior
import from this module; old consumers continue to work unchanged
(back-compat: an envelope without a ``tier`` field reads as
``tier_1_candidate``).

Phase 18 B carries the cohort still at tier_1_candidate; Phase 18 A
end-to-end ccx success on cylinder-pv-candidate is the gate for
flipping that case to tier_2_validated in a later sub-phase. Until
then, every entry in :data:`CLAIM_TIER_REGISTRY` is
``tier_1_candidate``.

Signed-registry cases (``^GS-\\d{3}$``) are deliberately **not** in
the registry: per ADR-011 §HF1.7a, those carry their own provenance
discipline (signed validation reports). This module would refuse a
``GS-NNN`` lookup with ``KeyError``; the runner-side HF1.7a guard
catches earlier any attempt to invoke ccx on a signed case at all.
"""

from __future__ import annotations

import re
from typing import Final, Literal

ClaimTier = Literal["tier_1_candidate", "tier_2_validated"]
"""Closed set of tier discriminator values. Type alias used by every
consumer that branches on tier."""

CLAIM_TIER_TIER_1_CANDIDATE: Final[ClaimTier] = "tier_1_candidate"
CLAIM_TIER_TIER_2_VALIDATED: Final[ClaimTier] = "tier_2_validated"

CLAIM_TIER_LABELS: Final[dict[ClaimTier, str]] = {
    "tier_1_candidate": "Tier 1 engineering candidate",
    "tier_2_validated": "Tier 2 real-solver validated",
}
"""Human-readable label per tier. Renderers / report headers consume
this; back-compat with the inline ``"Tier 1 engineering candidate"``
string used in Phases 1-17 is preserved by the tier_1_candidate
entry."""

CLAIM_BOUNDARIES: Final[dict[ClaimTier, str]] = {
    "tier_1_candidate": (
        "tier1_engineering_candidate; not_signed_validation; "
        "not_benchmark_agreement"
    ),
    "tier_2_validated": (
        "tier2_real_solver_validated; not_signed_validation; "
        "cross_check_against_analytical"
    ),
}
"""Claim-boundary copy per tier. The tier_1_candidate boundary is
byte-identical to the ``CLAIM_BOUNDARY`` constants scattered across
Phases 1-17 reporting modules (intentional — back-compat). The
tier_2_validated boundary explicitly retains ``not_signed_validation``
because real-solver validation is NOT signed validation, and adds
``cross_check_against_analytical`` to signal the substantiation."""

# Per-case tier registry. The single source of truth for which case
# gets which tier. Phase 19 B introduces verdict-driven promotion:
# the static dict below is the BASELINE; the module-load hook
# `_apply_verdict_overlay` below reads any
# `golden_samples/<case_id>/cross_check_verdict.yaml` artifact
# present and promotes the case to tier_2_validated when the
# verdict is "PASS". Phase 18 B baseline (every case at
# tier_1_candidate) is preserved unchanged when no verdict file
# exists.
CLAIM_TIER_REGISTRY: Final[dict[str, ClaimTier]] = {
    "cylinder-pv-candidate": "tier_1_candidate",
    "rod-wave-impact-candidate": "tier_1_candidate",
    "swing-arm-fatigue-candidate": "tier_1_candidate",
    "ballistic-plate-candidate": "tier_1_candidate",
    "leak-shell-candidate": "tier_1_candidate",
    # Phase 20 B addition — slender cantilever beam candidate for the
    # second analytical cross-check (Euler-Bernoulli tip-deflection).
    # Baseline tier_1; promotion to tier_2_validated waits for a
    # Phase 21 cantilever runner (Slice C's Gmsh-meshed pipeline lands
    # the multi-element bending capability that single-hex coupons
    # cannot provide).
    "cantilever-beam-candidate": "tier_1_candidate",
    # Phase 20 C — first meshed-pipeline demonstration case. The .geo
    # at golden_samples/plate-with-hole-candidate/data/plate_with_hole.geo
    # drives gmsh → C3D4 → ccx end-to-end. Promotion to
    # tier_2_validated waits for a Phase 21 Kirsch (σ_max = 3·σ_∞)
    # cross-check runner.
    "plate-with-hole-candidate": "tier_1_candidate",
    # Phase 22 A — Euler buckling column candidate. The runner at
    # `app.services.cross_check.buckling_runner.run_buckling_cross_check`
    # composes a hex column INP with *BUCKLE step + Euler analytical
    # cross-check (P_cr = π²EI/(kL)²). Promotion to tier_2_validated
    # via verdict YAML when residual < 10%.
    "euler-column-candidate": "tier_1_candidate",
    # Phase 25 A — simply-supported plate, uniform pressure. The runner
    # at `app.services.cross_check.plate_ss_runner` composes a
    # 4-edge clamp + corner-pin INP for a 1m × 1m × 20mm plate, runs
    # ccx, and compares the center deflection to the Timoshenko α=0.00406
    # closed-form. Promotion to tier_2_validated via verdict YAML when
    # residual < 15% (honest envelope; Kirchhoff vs 3D + C3D10 mesh
    # discretization).
    "plate-simply-supported-candidate": "tier_1_candidate",
    # Phase 26 A — slender steel cantilever first natural frequency.
    # The runner at `app.services.cross_check.cantilever_modal_runner`
    # composes a clamped-x=0 *FREQUENCY INP for a 0.5m × 20mm × 20mm
    # beam (L/h=25, slender Euler-Bernoulli regime), runs ccx, parses
    # the eigenfrequency list, filters rigid-body modes (A:-1 guard),
    # and compares the first structural f_1 to the closed-form
    # (β_1·L)²·√(EI/ρA)/(2π·L²) with β_1·L=1.875104. Promotion via
    # verdict YAML when residual < 12%. Introduces the *FREQUENCY
    # solver kind to the validated cohort (the four prior tier_2_
    # validated cases all used linear-static + one linear-buckling).
    "cantilever-beam-modal-candidate": "tier_1_candidate",
    # Phase 27 A — extreme-slender cantilever modal (L/h=50).
    # Second modal case; reuses Phase 26 A's runner verbatim with a
    # 1.000 m × 20 mm × 20 mm beam (DOUBLED length → 4× more slender
    # than Phase 26 A's L/h=25; still well inside the L/h ≥ 10
    # Euler-Bernoulli validity envelope). Analytical f_1 scales as
    # 1/L² → ≈ 16.71 Hz (vs Phase 26 A's 66.84 Hz). Live ccx
    # 2026-05-17 residual +0.136% — virtually identical to Phase 26
    # A's +0.13%, confirming the Euler-Bernoulli envelope holds at
    # the slenderness extreme. Honest scope: NO new element type
    # (still C3D10), NO new solver kind (still *FREQUENCY); the
    # value-add is an envelope-stress-test across 4× the
    # slenderness range. Shell elements deferred to a future phase
    # because CalculiX shell-output reader plumbing is non-trivial.
    "cantilever-beam-modal-l50-candidate": "tier_1_candidate",
    # Phase 28 A — cantilever Euler buckling (k=2.0). Second
    # buckling case; reuses Phase 23 A's `buckling_b31_runner`
    # verbatim with end_condition='fixed-free'. Tests the k-factor
    # discipline of the Euler formula: cantilever P_cr is 1/4 of
    # pinned-pinned P_cr at the same geometry. Live ccx 2026-05-17
    # residual +0.0298% (tightest residual across all 8 validated
    # cases). Honest scope: NO new element type (still B31), NO new
    # solver kind (still *BUCKLE); the value-add is k-factor family
    # validation at TWO points (k=1.0 pinned-pinned + k=2.0
    # cantilever). C3D8 hex cantilever attempt in `buckling_runner.py`
    # produced 256% residual due to shear locking; rejected and
    # documented in NOTES.md.
    "cantilever-buckle-candidate": "tier_1_candidate",
}


def _apply_verdict_overlay() -> None:
    """Read each case's `golden_samples/<case_id>/cross_check_verdict.yaml`
    (if present) and promote tier when the verdict is "PASS".

    Phase 19 B promotion seam — the cross-check service writes the
    verdict; this loader reads it at module-load. Failure modes
    (missing file / malformed json / wrong verdict value) all
    gracefully leave the registry at the baseline tier_1_candidate
    — the loader never raises so a stale or absent verdict cannot
    break import.
    """
    import json
    from pathlib import Path

    here = Path(__file__).resolve()
    # backend/app/services/reporting/_claim_tier.py → repo root is 4 up
    repo_root = here.parents[4]
    golden = repo_root / "golden_samples"
    if not golden.is_dir():
        return
    for case_id in list(CLAIM_TIER_REGISTRY):
        verdict_path = golden / case_id / "cross_check_verdict.yaml"
        if not verdict_path.is_file():
            continue
        try:
            payload = json.loads(verdict_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        verdict = payload.get("verdict")
        if verdict == "PASS":
            CLAIM_TIER_REGISTRY[case_id] = "tier_2_validated"


_apply_verdict_overlay()

_SIGNED_REGISTRY_PATTERN = re.compile(r"^GS-\d{3}$")
"""HF1.7a defense — signed cases are NOT in this registry. A lookup
for ``GS-NNN`` raises ``KeyError`` (caller treats this as a bug)."""


def get_claim_tier(case_id: str) -> ClaimTier:
    """Return the tier registered for ``case_id``.

    Defaults to ``tier_1_candidate`` for any case NOT in the registry —
    the conservative choice per ADR-025 §2.3 (unknown provenance is
    treated as candidate, not validated).

    Raises:
        ValueError: if ``case_id`` matches the signed-registry shape
            (HF1.7a defense in depth; signed cases must not pass
            through this lookup).
    """
    if _SIGNED_REGISTRY_PATTERN.fullmatch(case_id):
        raise ValueError(
            f"refused to resolve claim_tier for signed-registry case "
            f"{case_id!r} (HF1.7a defense); signed cases carry their own "
            f"validation provenance, not the candidate tier discriminator"
        )
    return CLAIM_TIER_REGISTRY.get(case_id, "tier_1_candidate")


def claim_tier_label_for(case_id: str) -> str:
    """Human-readable tier label for ``case_id``. Convenience accessor
    that composes :func:`get_claim_tier` and :data:`CLAIM_TIER_LABELS`.

    Back-compat: returns ``"Tier 1 engineering candidate"`` exactly
    for every case in the Phase 18 B baseline registry, matching the
    inline string used by Phases 1-17 reporting modules.
    """
    return CLAIM_TIER_LABELS[get_claim_tier(case_id)]


def claim_boundary_for(case_id: str) -> str:
    """Claim-boundary copy for ``case_id``. Convenience accessor that
    composes :func:`get_claim_tier` and :data:`CLAIM_BOUNDARIES`."""
    return CLAIM_BOUNDARIES[get_claim_tier(case_id)]


def register_tier_2_validated(case_id: str) -> None:
    """Mutate the registry to promote ``case_id`` to tier_2_validated.

    Phase 18 B intentionally leaves this as a programmatic seam rather
    than a runtime API — promotion is a code edit (a future commit that
    calls this from a tier-promotion migration script). The function
    refuses signed-registry shapes (HF1.7a defense) and refuses
    unknown case_ids (the registry is the SSOT of which cases exist).
    """
    if _SIGNED_REGISTRY_PATTERN.fullmatch(case_id):
        raise ValueError(
            f"refused to promote signed-registry case {case_id!r} "
            f"(HF1.7a defense)"
        )
    if case_id not in CLAIM_TIER_REGISTRY:
        raise KeyError(
            f"refused to promote unknown case_id {case_id!r}; "
            f"register the candidate in CLAIM_TIER_REGISTRY first"
        )
    CLAIM_TIER_REGISTRY[case_id] = "tier_2_validated"


__all__ = [
    "ClaimTier",
    "CLAIM_TIER_TIER_1_CANDIDATE",
    "CLAIM_TIER_TIER_2_VALIDATED",
    "CLAIM_TIER_LABELS",
    "CLAIM_BOUNDARIES",
    "CLAIM_TIER_REGISTRY",
    "get_claim_tier",
    "claim_tier_label_for",
    "claim_boundary_for",
    "register_tier_2_validated",
]
