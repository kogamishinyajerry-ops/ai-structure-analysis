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

import json
import re
from pathlib import Path
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
``cross_check_against_analytical`` to signal the substantiation. The
DEFAULT tier_2 substantiation is analytical cross-check — true for every
Phase-18-through-38 validated case; cases whose tier_2 evidence is a
DIFFERENT substantiation (e.g. public-benchmark agreement) override it via
:data:`CLAIM_BOUNDARY_OVERRIDES`."""

CLAIM_BOUNDARY_OVERRIDES: Final[dict[str, str]] = {
    # V2-1 / ADR-027 (Codex R1 P1, 2026-06-03) — LE10's tier_2 substantiation
    # is NOT an analytical cross-check; it is agreement with the PUBLISHED
    # NAFEMS LE10 reference. Surfacing it with the cohort-default
    # ``cross_check_against_analytical`` boundary would mis-state the evidence.
    # This override is honored only when the case actually resolves to
    # tier_2_validated (see :func:`claim_boundary_for`); a tier_1 fall-back
    # still uses the conservative default boundary.
    "nafems-le10-thick-plate-candidate": (
        "tier2_real_solver_validated; not_signed_validation; "
        "public_benchmark_agreement_nafems_le10; "
        "sign_normalized_to_solver_convention"
    ),
}
"""Per-case claim-boundary overrides applied ONLY at tier_2_validated. Keyed
by case_id; the value replaces :data:`CLAIM_BOUNDARIES`'s tier_2 default. Used
when a validated case's substantiation differs from the analytical-cross-check
default (the LE10 public-benchmark agreement is the first such case)."""

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
    # Phase 29 A — simply-supported plate, S4 SHELL elements. The
    # FIRST validated case to use shell elements; closes the FEA
    # Dim 1 hard cap (≤75) that has been load-bearing since Phase 18.
    # Reuses Phase 25 A's Timoshenko α·q·a⁴/D analytical (helper in
    # `plate_simply_supported.py`) — the analytical is element-
    # discretization-agnostic. Hand-rolled 20×20 structured quad
    # mesh (441 nodes), simply-supported BC (u_z=0 on 4 edges + RBM
    # pin at corners), uniform pressure via *DLOAD P2. Promoted to
    # tier_2_validated by verdict YAML overlay.
    "plate-ss-shell-candidate": "tier_1_candidate",
    # Phase 30 A — cantilever free-vibration *DYNAMIC. The FIRST
    # transient time-integration case in the cohort. Reuses Phase 26 A
    # geometry + analytical f_1; only the solver path is new (HHT-α
    # implicit integration vs *FREQUENCY eigenvalue extraction).
    # Closes FEA Dim 6 ballistic-readiness floor (50 → 75 rubric v1.0
    # anchor) — first *DYNAMIC unlocks "transient implicit" anchor.
    # Promoted to tier_2_validated by verdict YAML overlay on a
    # PASS live ccx run.
    "cantilever-dynamic-candidate": "tier_1_candidate",
    # Phase 31 A — first *HEAT TRANSFER (steady-state 1D linear
    # conduction) validated case. Documented pivot from the Phase 31
    # blueprint's *CONTACT PAIR scope; contact deferred to Phase 32
    # for risk reduction. Closes FEA Dim 2 anchor 85 (Phase 30 A
    # *DYNAMIC implicit) → ~88 (interpolation between *DYNAMIC and
    # the 99-anchor "+ *HEAT TRANSFER + *VISCO + *COUPLED
    # TEMPERATURE-DISPLACEMENT" triple).
    # Promoted to tier_2_validated by verdict YAML overlay on a
    # PASS live ccx run.
    "heat-transfer-1d-candidate": "tier_1_candidate",
    # Phase 38 B — single-C3D6 wedge uniaxial Hooke's-law cross-check.
    # Adds the 6th element class (C3D6) to the cohort (prior 5: C3D4 /
    # C3D8 / C3D10 / S4 / B31). The runner at
    # `app.services.cross_check.wedge_c3d6_runner` writes one pentahedral
    # wedge in pure uniaxial stress and verifies ccx recovers
    # sigma_zz = E*epsilon exactly (constant-strain element → 0.00%
    # residual on the live run). Promoted to tier_2_validated by the
    # verdict YAML overlay on the PASS verdict.
    "wedge-c3d6-candidate": "tier_1_candidate",
    # Phase 34 C — *CONTACT PAIR validated case (stacked-cube uniaxial
    # contact; 1D-exact δ = F·H/(E·A) analytical, residual −6.82% within
    # the 20% envelope on live ccx 2.23). Solver kind #6 contact_pair_static.
    # REGISTRY OMISSION FIX (Phase 38 F, found by Codex R1): Phase 34 C
    # shipped the verdict + cohort-count bump but never registered the case
    # here, so a genuine real-solver promotion stayed invisible. Its verdict
    # artifact is YAML (not JSON) with a nested `verdict_outcome.verdict` —
    # the overlay below now parses both formats + shapes, promoting it.
    "hertz-contact-candidate": "tier_1_candidate",
    # V2-1 / ADR-027 (2026-06-03) — the project's first PUBLIC-BENCHMARK
    # AGREEMENT (all prior tier_2 cases cross-check an analytical closed form;
    # this one agrees with the published NAFEMS LE10 reference σ_yy(D) = −5.38
    # MPa). Real ccx 2.23, C3D20 40×20×6, observed −5.4379 MPa, +1.08% (tol 3%),
    # monotone convergence. Promoted to tier_2_validated by the overlay on the
    # cross_check_verdict.yaml verdict=PASS. Baseline tier_1 here.
    "nafems-le10-thick-plate-candidate": "tier_1_candidate",
}


def _verdict_path_for(repo_root: Path, case_id: str) -> Path:
    """Path to a case's cross-check verdict artifact under ``repo_root``."""
    return Path(repo_root) / "golden_samples" / case_id / "cross_check_verdict.yaml"


def _parse_verdict_payload(verdict_path: Path) -> dict | None:
    """Parse a ``cross_check_verdict.yaml`` artifact into a mapping, or None.

    Phase 18-34 verdicts are JSON-style; Phase 34 C hertz-contact is YAML.
    Mirror the Phase 35 B census loader: try ``json`` first (the fast path for
    the 12 JSON verdicts), fall back to ``yaml`` (the hertz YAML). Never raises
    — any failure (missing / malformed / non-mapping) returns None so a stale
    or absent verdict cannot break import or a request.
    """
    try:
        text = verdict_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml

            payload = yaml.safe_load(text)
        except Exception:
            return None
    return payload if isinstance(payload, dict) else None


def _verdict_is_pass(verdict_path: Path) -> bool:
    """True iff the verdict artifact records a PASS, across both verdict
    shapes: a top-level ``verdict`` (the 12 JSON verdicts) OR a nested
    ``verdict_outcome.verdict`` (the Phase 34 C hertz-contact YAML)."""
    payload = _parse_verdict_payload(verdict_path)
    if not payload:
        return False
    if payload.get("verdict") == "PASS":
        return True
    outcome = payload.get("verdict_outcome")
    return isinstance(outcome, dict) and outcome.get("verdict") == "PASS"


def _apply_verdict_overlay() -> None:
    """Promote registered cases to ``tier_2_validated`` when their
    `golden_samples/<case_id>/cross_check_verdict.yaml` records a PASS.

    Phase 19 B promotion seam — read at module-load against the real repo
    root. Never raises; a missing / malformed / non-PASS verdict leaves the
    baseline ``tier_1_candidate``. Phase 38 F: parses both JSON and YAML
    verdicts and both the top-level and nested ``verdict_outcome`` shapes (the
    hertz-contact YAML), so a Phase-34-C-style validated case is no longer
    silently skipped.
    """
    here = Path(__file__).resolve()
    # backend/app/services/reporting/_claim_tier.py → repo root is 4 up
    repo_root = here.parents[4]
    if not (repo_root / "golden_samples").is_dir():
        return
    for case_id in list(CLAIM_TIER_REGISTRY):
        if _verdict_is_pass(_verdict_path_for(repo_root, case_id)):
            CLAIM_TIER_REGISTRY[case_id] = "tier_2_validated"


_apply_verdict_overlay()

_SIGNED_REGISTRY_PATTERN = re.compile(r"^GS-\d{3}$")
"""HF1.7a defense — signed cases are NOT in this registry. A lookup
for ``GS-NNN`` raises ``KeyError`` (caller treats this as a bug)."""


def get_claim_tier(case_id: str, repo_root: Path | None = None) -> ClaimTier:
    """Return the tier for ``case_id``.

    Defaults to ``tier_1_candidate`` for any case NOT in the registry —
    the conservative choice per ADR-025 §2.3 (unknown provenance is
    treated as candidate, not validated).

    ``repo_root`` (Phase 38 F, Codex R1): when supplied, the tier is resolved
    against THAT tree's ``golden_samples/<case_id>/cross_check_verdict.yaml``
    rather than the module-load-time registry (which reflects the real repo).
    Root-parameterized callers (``candidate_cases``, ``cohort_overview``,
    ``cohort_snapshot``) pass their ``repo_root`` so a cohort built against an
    alternate / synthetic worktree reports that worktree's promotions instead
    of the host checkout's. Without a root, the module registry is used
    (back-compat for the reporting modules that resolve by case_id alone).

    Root-scoped resolution still gates on registry membership: only a case
    present in :data:`CLAIM_TIER_REGISTRY` can be promoted, and only when the
    supplied root records a PASS. A PASS verdict for an unregistered case does
    NOT promote it — the registry remains the SSOT of cohort admission, so a
    stray experimental verdict file cannot fabricate a Tier-2 claim.

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
    if repo_root is not None:
        # Root-scoped: honor the supplied tree's verdict file for WHICH root's
        # promotion to read — but still gate on registry membership (Codex R2).
        # The registry is the SSOT of which cases are admitted to the validated
        # cohort; a stray PASS verdict for an UNREGISTERED experimental
        # `*-candidate` dir must NOT auto-surface as Tier 2. So tier_2 iff the
        # case is registered AND this root records a PASS; everything else
        # (unregistered, or registered-but-no-verdict-under-this-root) is the
        # conservative Tier-1 floor.
        if case_id in CLAIM_TIER_REGISTRY and _verdict_is_pass(
            _verdict_path_for(repo_root, case_id)
        ):
            return "tier_2_validated"
        return "tier_1_candidate"
    return CLAIM_TIER_REGISTRY.get(case_id, "tier_1_candidate")


def claim_tier_label_for(case_id: str, repo_root: Path | None = None) -> str:
    """Human-readable tier label for ``case_id``. Convenience accessor
    that composes :func:`get_claim_tier` and :data:`CLAIM_TIER_LABELS`.

    Back-compat: returns ``"Tier 1 engineering candidate"`` exactly
    for every case in the Phase 18 B baseline registry, matching the
    inline string used by Phases 1-17 reporting modules. See
    :func:`get_claim_tier` for the ``repo_root`` scoping semantics.
    """
    return CLAIM_TIER_LABELS[get_claim_tier(case_id, repo_root)]


def claim_boundary_for(case_id: str, repo_root: Path | None = None) -> str:
    """Claim-boundary copy for ``case_id``. Convenience accessor that
    composes :func:`get_claim_tier` and :data:`CLAIM_BOUNDARIES`. See
    :func:`get_claim_tier` for the ``repo_root`` scoping semantics.

    A case in :data:`CLAIM_BOUNDARY_OVERRIDES` whose tier resolves to
    ``tier_2_validated`` returns its bespoke boundary instead of the cohort
    tier_2 default — this is how a validated case whose substantiation is NOT
    an analytical cross-check (e.g. the LE10 public-benchmark agreement) states
    its real evidence honestly. The override never applies at tier_1 (an
    unpromoted case keeps the conservative default boundary)."""
    tier = get_claim_tier(case_id, repo_root)
    if tier == "tier_2_validated" and case_id in CLAIM_BOUNDARY_OVERRIDES:
        return CLAIM_BOUNDARY_OVERRIDES[case_id]
    return CLAIM_BOUNDARIES[tier]


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
    "CLAIM_BOUNDARY_OVERRIDES",
    "CLAIM_TIER_REGISTRY",
    "get_claim_tier",
    "claim_tier_label_for",
    "claim_boundary_for",
    "register_tier_2_validated",
]
