"""NL → SimPlan draft + user-signed submit (ADR-015 §Confirmation protocol).

The Phase 2.1 user flow:

1. Browser sends `POST /runs/draft { "nl_request": "..." }`
2. Backend calls `draft_from_nl(nl_request)` → returns
   `(SimPlan, draft_id, confirmation_token)`
3. Browser displays the rendered SimPlan; user can edit or accept
4. Browser sends `POST /runs/submit { "draft_id", "confirmation_token", "edits" }`
5. Backend rebuilds the SimPlan with edits applied, validates the
   confirmation_token ties draft_id ↔ rebuilt SimPlan via HMAC, and
   only then invokes the LangGraph run

The HMAC is computed over `draft_id || canonical-JSON(SimPlan)` with
the workbench token as the key. It guarantees:

- the SimPlan the user confirmed in step 3 is identical to the SimPlan
  that runs in step 5 (no silent drift)
- a draft cannot be submitted by a third party who didn't see the
  rendered SimPlan
- replay of the same `confirmation_token` against a different
  `draft_id` fails

There is no LLM regeneration between draft and submit. If the user
edits the draft, edits are applied via a structured diff to the draft
SimPlan; the architect agent is NOT re-invoked.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid

from schemas.sim_plan import SimPlan

from .agent_facade import ArchitectResult, draft_simplan_from_nl


class ConfirmationError(Exception):
    """Raised when a draft → submit confirmation cannot be verified."""


def _canonical_json(plan: SimPlan) -> bytes:
    """Serialize a SimPlan to canonical JSON bytes.

    Pydantic v2's `model_dump_json` is non-canonical (key order tracks
    declaration). We re-serialize with `sort_keys=True` to make the
    HMAC input deterministic regardless of model evolution.
    """
    payload = json.loads(plan.model_dump_json())
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _hmac_token(secret: bytes, draft_id: str, plan: SimPlan) -> str:
    """Compute HMAC-SHA256 over draft_id || canonical-JSON(plan)."""
    if not secret:
        raise ValueError("workbench secret must be non-empty bytes")
    body = draft_id.encode("utf-8") + b"\x00" + _canonical_json(plan)
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _new_draft_id() -> str:
    """Generate a draft id with enough entropy to be unguessable.

    Format: `draft-<uuid4>` — uuid4 is 122 bits of randomness which is
    sufficient since the HMAC binding is the actual security boundary.
    """
    return f"draft-{uuid.uuid4()}"


def draft_from_nl(
    nl_request: str,
    *,
    workbench_secret: bytes,
    case_id: str | None = None,
) -> tuple[SimPlan, str, str]:
    """Architect-translate `nl_request` to a SimPlan and emit a confirmation token.

    Returns
    -------
    (plan, draft_id, confirmation_token)
        - `plan`: the SimPlan the architect produced
        - `draft_id`: a freshly minted, server-side-only identifier
        - `confirmation_token`: HMAC-SHA256 hex string binding the
          draft_id to the canonical-JSON of the plan

    Notes
    -----
    The caller (e.g. an `/runs/draft` endpoint) is responsible for
    persisting (draft_id, plan, confirmation_token) so the matching
    `submit_with_confirmation` call can validate against the same plan
    bytes. The token alone is NOT a session — it binds a specific
    plan-instance.
    """
    architect_result: ArchitectResult = draft_simplan_from_nl(
        nl_request, case_id=case_id
    )
    draft_id = _new_draft_id()
    token = _hmac_token(workbench_secret, draft_id, architect_result.plan)
    return architect_result.plan, draft_id, token


def verify_confirmation(
    *,
    workbench_secret: bytes,
    draft_id: str,
    plan: SimPlan,
    confirmation_token: str,
) -> None:
    """Raise `ConfirmationError` if the token does not bind draft_id to plan.

    Uses `hmac.compare_digest` to defeat timing oracle attacks on the
    token comparison.
    """
    expected = _hmac_token(workbench_secret, draft_id, plan)
    if not secrets.compare_digest(expected, confirmation_token):
        raise ConfirmationError(
            f"confirmation_token does not match draft_id={draft_id!r} and the supplied SimPlan; "
            f"either the plan was edited in transit or the token was issued for a different draft"
        )


__all__ = [
    "ConfirmationError",
    "draft_from_nl",
    "verify_confirmation",
]
