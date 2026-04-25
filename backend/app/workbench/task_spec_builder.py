"""NL → SimPlan draft + user-signed submit (ADR-015 §Confirmation protocol).

The Phase 2.1 user flow (R2 — post Codex R1 fix for the edit-flow gap):

1. Browser sends `POST /runs/draft { "nl_request": "..." }`
2. Backend calls `draft_from_nl(nl_request)`:
     - architect runs ONCE → SimPlan
     - server stores `(draft_id → original_plan)` in an in-process draft
       registry (Phase 2.1 single-operator scope; Phase 3 may swap for
       Redis)
     - returns `(SimPlan, draft_id, draft_token)` where
       `draft_token = HMAC(draft_id || canonical-JSON(original_plan))`
3. Browser displays the rendered SimPlan; user can edit or accept.
4. If the user edits, browser calls `apply_edits_and_remint(draft_id,
   edited_plan, draft_token, secret)`:
     - server validates `draft_token` against the STORED original plan
     - server applies the supplied `edited_plan` as a full replacement
       (constrained to the same `case_id`; arbitrary structural changes
       are rejected)
     - server returns `(rebuilt_plan, submit_token)` where
       `submit_token = HMAC(draft_id || canonical-JSON(rebuilt_plan))`
   If no edits, the caller uses the draft_token as the submit_token
   directly (the rebuilt plan equals the original).
5. Browser sends `POST /runs/submit { draft_id, submit_token }`:
     - server looks up the rebuilt plan
     - calls `verify_confirmation` against (draft_id, rebuilt_plan,
       submit_token)
     - on success, `discard_draft(draft_id)` and invokes the LangGraph
       run

R2 contract differences vs. R1 (Codex R1 HIGH on PR #54):

- R1 minted the token over the pre-edit plan and rechecked against the
  post-edit plan, so any legitimate edit invalidated the token.
- R2 splits the flow: the SERVER re-mints the token over the rebuilt
  plan during the precommit step. The client never holds the workbench
  secret, so a client-side re-mint is impossible. The submit endpoint
  validates the SERVER-issued submit_token, which is the rebuilt-plan
  witness.

The architect runs ONCE per draft. Edits are deterministic
server-mediated transformations; the LLM is NOT re-invoked.

The HMAC guarantees:

- the SimPlan the user committed to (in step 4 or step 2 if no edits)
  is identical to the SimPlan that runs in step 5 (no silent drift)
- a draft cannot be submitted by a third party who didn't see the
  rendered SimPlan and complete the precommit step
- replay of the same submit_token against a different draft_id fails
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import uuid
from dataclasses import dataclass

from schemas.sim_plan import SimPlan

from .agent_facade import ArchitectResult, draft_simplan_from_nl


class ConfirmationError(Exception):
    """Raised when a draft → submit confirmation cannot be verified."""


class DraftNotFoundError(Exception):
    """Raised when a draft_id is not in the registry (expired or never issued)."""


class EditValidationError(Exception):
    """Raised when proposed edits fail server-side constraints."""


# In-process draft registry (Phase 2.1 single-operator scope).
# Keyed by draft_id. The registry is private to this module — `draft_from_nl`
# / `apply_edits_and_remint` / `discard_draft` are the only mutators.
@dataclass
class _DraftRecord:
    plan: SimPlan
    nl_request: str  # for audit; never returned to client


_DRAFTS: dict[str, _DraftRecord] = {}
_DRAFTS_LOCK = threading.Lock()


def _store_draft(draft_id: str, plan: SimPlan, nl_request: str) -> None:
    with _DRAFTS_LOCK:
        _DRAFTS[draft_id] = _DraftRecord(plan=plan, nl_request=nl_request)


def _load_draft(draft_id: str) -> SimPlan:
    with _DRAFTS_LOCK:
        record = _DRAFTS.get(draft_id)
    if record is None:
        raise DraftNotFoundError(
            f"draft_id={draft_id!r} not found — never issued or already discarded"
        )
    return record.plan


def discard_draft(draft_id: str) -> None:
    """Remove a draft from the registry (after successful run start, or
    on explicit cancel). Idempotent.
    """
    with _DRAFTS_LOCK:
        _DRAFTS.pop(draft_id, None)


def _registry_size() -> int:
    """Test-only helper for asserting registry growth/shrink."""
    with _DRAFTS_LOCK:
        return len(_DRAFTS)


def _registry_clear() -> None:
    """Test-only helper for isolating tests from each other's drafts."""
    with _DRAFTS_LOCK:
        _DRAFTS.clear()


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
    """Compute HMAC-SHA256 over `draft_id || NUL || canonical-JSON(plan)`.

    The NUL separator prevents an attacker from constructing a different
    `(draft_id, plan)` pair whose concatenation collides with the
    target — `(d1+chunk, p1) ≠ (d1, chunk+p1)` because the NUL is
    not allowed in `draft_id` (we only mint `draft-<uuid4>`).
    """
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
    """Architect-translate `nl_request` to a SimPlan and emit a draft token.

    Stores `(draft_id → plan)` in the in-process registry so a later
    `apply_edits_and_remint` (or direct submit) can recover the original
    plan and validate the user-signed witness.

    Returns
    -------
    (plan, draft_id, draft_token)
        - `plan`: the SimPlan the architect produced
        - `draft_id`: a freshly minted, server-side-only identifier
        - `draft_token`: HMAC-SHA256 hex string binding draft_id to the
          canonical-JSON of the original plan
    """
    architect_result: ArchitectResult = draft_simplan_from_nl(
        nl_request, case_id=case_id
    )
    draft_id = _new_draft_id()
    token = _hmac_token(workbench_secret, draft_id, architect_result.plan)
    _store_draft(draft_id, architect_result.plan, nl_request)
    return architect_result.plan, draft_id, token


def apply_edits_and_remint(
    *,
    workbench_secret: bytes,
    draft_id: str,
    draft_token: str,
    edited_plan: SimPlan,
) -> tuple[SimPlan, str]:
    """Validate the draft token, apply user-supplied edits, and re-mint.

    Closes Codex R1 HIGH on PR #54: edits applied to the draft now flow
    through this server-side step which produces a *new* token bound to
    the rebuilt plan. The submit endpoint validates the new token; the
    HMAC binding is preserved.

    Constraints on `edited_plan`:

    - `edited_plan.case_id` MUST equal the stored draft's `case_id`.
      The case id is the run identity — the user is editing the
      *contents* of a specific case, not picking a different case.

    Returns
    -------
    (rebuilt_plan, submit_token)
        - `rebuilt_plan`: the canonicalized post-edit SimPlan (caller
          stores this for the actual submit step)
        - `submit_token`: HMAC over (draft_id, rebuilt_plan)

    Raises
    ------
    DraftNotFoundError
        If the draft_id is not in the registry.
    ConfirmationError
        If `draft_token` does not match the stored original plan.
    EditValidationError
        If the supplied `edited_plan` violates server-side constraints
        (currently: case_id must equal the stored draft's case_id).
    """
    original = _load_draft(draft_id)
    expected_draft_token = _hmac_token(workbench_secret, draft_id, original)
    if not secrets.compare_digest(expected_draft_token, draft_token):
        raise ConfirmationError(
            f"draft_token does not match the stored original plan for "
            f"draft_id={draft_id!r}; either the token was issued for a "
            f"different draft or the workbench secret has rotated"
        )

    if edited_plan.case_id != original.case_id:
        raise EditValidationError(
            f"edited_plan.case_id={edited_plan.case_id!r} does not match the "
            f"draft's case_id={original.case_id!r}; case identity is fixed at "
            f"draft time"
        )

    submit_token = _hmac_token(workbench_secret, draft_id, edited_plan)
    return edited_plan, submit_token


def verify_confirmation(
    *,
    workbench_secret: bytes,
    draft_id: str,
    plan: SimPlan,
    confirmation_token: str,
) -> None:
    """Raise `ConfirmationError` if the token does not bind draft_id to plan.

    The `plan` argument is whatever the submit endpoint is about to
    run — the original draft (no edits) or the rebuilt plan returned
    by `apply_edits_and_remint` (with edits). Either way, the
    `confirmation_token` must bind draft_id to that plan.

    Uses `hmac.compare_digest` to defeat timing oracle attacks on the
    token comparison.
    """
    expected = _hmac_token(workbench_secret, draft_id, plan)
    if not secrets.compare_digest(expected, confirmation_token):
        raise ConfirmationError(
            f"confirmation_token does not match draft_id={draft_id!r} and the "
            f"supplied SimPlan; either the plan was edited without a precommit "
            f"step or the token was issued for a different draft"
        )


__all__ = [
    "ConfirmationError",
    "DraftNotFoundError",
    "EditValidationError",
    "apply_edits_and_remint",
    "discard_draft",
    "draft_from_nl",
    "verify_confirmation",
]
