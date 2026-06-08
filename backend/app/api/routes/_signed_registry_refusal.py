"""SSOT helper: refuse signed-registry case_ids on Tier 1 candidate routes.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

FM-04a Phase 14 A — closes the Phase 13 retrospective slice-B LOW #3
carry-forward (cross-route signed-registry meta-guard).

Phase 13 B closed the case-completeness signed-registry gap (originally
observed in Phase 12 F slice-F LOW); Phase 11 closed the equivalent
gap on advisor-critique. Both implementations duplicated the regex +
the 422 + detail vocabulary. Phase 14 A consolidates those into a
single SSOT helper so every Tier 1 reviewer-facing route consistently
refuses ``^GS-\\d{3}$`` identifiers with the same status code + same
detail vocabulary. The duplication-free shape is also what makes the
slice-A meta-guard test trip cleanly when a NEW route forgets to call
the helper: a single grep ``assert_not_signed_registry`` enumerates
the surfaces, the meta-test enumerates the routes, and the diff is
the gap.

Why 422 (not 400)?
* 400 ``Bad Request`` semantically means "the syntax of the request
  is malformed". A ``GS-001`` case_id is SYNTACTICALLY VALID (matches
  ``^[A-Za-z0-9_-]{1,64}$``), so 400 mis-classifies the refusal as a
  malformation error.
* 422 ``Unprocessable Entity`` means "the request is well-formed but
  the server refuses to process it for semantic reasons" — exactly
  what a signed-registry refusal is: the syntax is fine, but the
  Tier 1 surface refuses the sealed FM-04b P8 packet identifier as
  out-of-scope.
* Advisor-critique (Phase 11) + case-completeness (Phase 13 B) both
  use 422; this helper preserves that convention.

Why a SHARED detail vocabulary?
* The Phase 13 retrospective §1 named "cohort-surface inconsistency"
  where ``GS-101`` returned different status codes on different
  routes (silent 200 on case-completeness, 422 on advisor-critique).
  A reviewer who sees inconsistent refusal codes loses trust in the
  surface; a reviewer who sees the SAME 422 + ``"signed-registry"``
  + ``"candidate"`` + ``"out of scope"`` tokens everywhere learns
  the rule once and reads it everywhere.
"""

from __future__ import annotations

import re

from fastapi import HTTPException

# SSOT for the signed-registry shape. Phase 13 D split HF1.7 into
# HF1.7a (signed-registry hard-stop) + HF1.7b (`*-candidate`
# writable). The signed-registry pattern is anchored on the WHOLE
# case_id to refuse only the canonical shape; `*-candidate` names
# pass through to the route handler.
SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


def signed_registry_refusal_detail(surface_name: str) -> str:
    """Return the canonical refusal detail string for a route surface.

    ``surface_name`` is a short human-readable surface identifier
    embedded in the detail message so a reviewer reading the response
    sees WHICH surface refused (e.g., ``"trust-score"``,
    ``"reproducibility-manifest"``).
    """
    return (
        f"{surface_name} refuses signed-registry case_id; "
        f"Tier 1 candidate surfaces only accept *-candidate "
        f"identifiers (sealed FM-04b packets are out of scope)"
    )


def assert_not_signed_registry(case_id: str, surface_name: str) -> None:
    """Raise HTTP 422 if ``case_id`` matches the signed-registry shape.

    Intended to be called by every Tier 1 reviewer-facing route's
    handler AFTER the basic ``_CASE_ID_RE`` syntax check (which raises
    400 on malformed input). The order matters:

      1. 400 on syntactically-malformed case_id (existing per-route
         guard; e.g., URL-decoded space characters).
      2. 422 on signed-registry case_id (this helper).
      3. Route-specific handler logic.

    The 422 raise is BEFORE any filesystem lookup so a tampered or
    hypothetical seeded signed-registry directory under
    ``golden_samples/`` cannot leak data through a Tier 1 candidate
    route.
    """
    if SIGNED_REGISTRY_RE.fullmatch(case_id):
        raise HTTPException(
            status_code=422,
            detail=signed_registry_refusal_detail(surface_name),
        )
