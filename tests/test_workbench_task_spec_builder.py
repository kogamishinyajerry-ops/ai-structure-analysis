"""Tests for backend.app.workbench.task_spec_builder (ADR-015 §Confirmation protocol)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

# schemas.sim_plan uses `enum.StrEnum` (Python 3.11+). Skip cleanly on older
# interpreters; CI is 3.11+.
pytest.importorskip("schemas.sim_plan")

from backend.app.workbench.task_spec_builder import (  # noqa: E402
    ConfirmationError,
    _canonical_json,
    _hmac_token,
    _new_draft_id,
    draft_from_nl,
    verify_confirmation,
)
from schemas.sim_plan import AnalysisType, GeometrySpec, PhysicsSpec, SimPlan  # noqa: E402

SECRET = b"workbench-token-fixture-32-bytes!"
ALT_SECRET = b"different-workbench-token-32-byts"


def _sample_plan(case_id: str = "AI-FEA-P0-11") -> SimPlan:
    return SimPlan(
        case_id=case_id,
        physics=PhysicsSpec(type=AnalysisType.STATIC),
        geometry=GeometrySpec(
            mode="knowledge",
            ref="naca",
            params={"profile": "NACA0012", "span": 1.2, "chord": 0.3},
        ),
    )


# ---------------------------------------------------------------------------
# canonical_json determinism
# ---------------------------------------------------------------------------


def test_canonical_json_is_sorted_keys():
    plan = _sample_plan()
    blob = _canonical_json(plan)
    parsed = json.loads(blob)
    # Re-serialize the parsed structure with sort_keys=True and verify
    # the string round-trips identically.
    rebuilt = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    assert blob == rebuilt


def test_canonical_json_stable_across_calls():
    plan = _sample_plan()
    a = _canonical_json(plan)
    b = _canonical_json(plan)
    assert a == b


def test_canonical_json_differs_between_distinct_plans():
    a = _canonical_json(_sample_plan(case_id="AI-FEA-P0-11"))
    b = _canonical_json(_sample_plan(case_id="AI-FEA-P0-12"))
    assert a != b


# ---------------------------------------------------------------------------
# _hmac_token contract
# ---------------------------------------------------------------------------


def test_hmac_token_is_hex_string():
    token = _hmac_token(SECRET, "draft-abc", _sample_plan())
    assert len(token) == 64
    int(token, 16)  # must parse as hex


def test_hmac_token_changes_when_draft_id_changes():
    plan = _sample_plan()
    a = _hmac_token(SECRET, "draft-aaa", plan)
    b = _hmac_token(SECRET, "draft-bbb", plan)
    assert a != b


def test_hmac_token_changes_when_plan_changes():
    a = _hmac_token(SECRET, "draft-x", _sample_plan(case_id="AI-FEA-P0-11"))
    b = _hmac_token(SECRET, "draft-x", _sample_plan(case_id="AI-FEA-P0-12"))
    assert a != b


def test_hmac_token_changes_when_secret_changes():
    plan = _sample_plan()
    a = _hmac_token(SECRET, "draft-x", plan)
    b = _hmac_token(ALT_SECRET, "draft-x", plan)
    assert a != b


def test_hmac_token_rejects_empty_secret():
    with pytest.raises(ValueError, match="non-empty"):
        _hmac_token(b"", "draft-x", _sample_plan())


# ---------------------------------------------------------------------------
# _new_draft_id
# ---------------------------------------------------------------------------


def test_draft_id_is_unique():
    seen = {_new_draft_id() for _ in range(100)}
    assert len(seen) == 100


def test_draft_id_has_expected_prefix():
    assert _new_draft_id().startswith("draft-")


# ---------------------------------------------------------------------------
# draft_from_nl wires architect → token correctly
# ---------------------------------------------------------------------------


def test_draft_from_nl_returns_plan_draft_id_token_triple():
    plan = _sample_plan()
    with patch(
        "agents.architect._extract_structured_data",
        return_value=plan,
    ):
        produced_plan, draft_id, token = draft_from_nl("static beam", workbench_secret=SECRET)
    assert produced_plan.case_id == "AI-FEA-P0-11"
    assert draft_id.startswith("draft-")
    assert len(token) == 64


def test_draft_from_nl_token_validates_with_returned_plan():
    plan = _sample_plan()
    with patch(
        "agents.architect._extract_structured_data",
        return_value=plan,
    ):
        produced_plan, draft_id, token = draft_from_nl("static beam", workbench_secret=SECRET)
    # Round-trip: the returned token must verify against the returned plan.
    verify_confirmation(
        workbench_secret=SECRET,
        draft_id=draft_id,
        plan=produced_plan,
        confirmation_token=token,
    )


# ---------------------------------------------------------------------------
# verify_confirmation contract — drift / replay / cross-secret
# ---------------------------------------------------------------------------


def test_verify_confirmation_rejects_token_for_different_plan():
    plan = _sample_plan()
    other_plan = _sample_plan(case_id="AI-FEA-P0-99")
    token = _hmac_token(SECRET, "draft-x", plan)
    with pytest.raises(ConfirmationError):
        verify_confirmation(
            workbench_secret=SECRET,
            draft_id="draft-x",
            plan=other_plan,
            confirmation_token=token,
        )


def test_verify_confirmation_rejects_token_for_different_draft_id():
    """Replay attack: same token, different draft_id."""
    plan = _sample_plan()
    token = _hmac_token(SECRET, "draft-original", plan)
    with pytest.raises(ConfirmationError):
        verify_confirmation(
            workbench_secret=SECRET,
            draft_id="draft-replay-target",
            plan=plan,
            confirmation_token=token,
        )


def test_verify_confirmation_rejects_token_signed_with_different_secret():
    plan = _sample_plan()
    token = _hmac_token(ALT_SECRET, "draft-x", plan)
    with pytest.raises(ConfirmationError):
        verify_confirmation(
            workbench_secret=SECRET,
            draft_id="draft-x",
            plan=plan,
            confirmation_token=token,
        )


def test_verify_confirmation_rejects_truncated_token():
    plan = _sample_plan()
    token = _hmac_token(SECRET, "draft-x", plan)
    with pytest.raises(ConfirmationError):
        verify_confirmation(
            workbench_secret=SECRET,
            draft_id="draft-x",
            plan=plan,
            confirmation_token=token[:-1],  # 63 chars instead of 64
        )


def test_verify_confirmation_rejects_empty_token():
    plan = _sample_plan()
    with pytest.raises(ConfirmationError):
        verify_confirmation(
            workbench_secret=SECRET,
            draft_id="draft-x",
            plan=plan,
            confirmation_token="",
        )


def test_verify_confirmation_uses_constant_time_compare():
    """Smoke test that the comparison path goes through hmac/secrets,
    not a Python `==` that early-exits on mismatch."""
    import secrets as secrets_mod

    plan = _sample_plan()
    valid = _hmac_token(SECRET, "draft-x", plan)

    # Patch compare_digest to a sentinel; if verify_confirmation calls
    # it, our test passes; if it uses `==`, the patch is unused and we
    # detect the regression.
    called = {"hit": False}

    real = secrets_mod.compare_digest

    def spy(a, b):
        called["hit"] = True
        return real(a, b)

    with patch("backend.app.workbench.task_spec_builder.secrets.compare_digest", spy):
        verify_confirmation(
            workbench_secret=SECRET,
            draft_id="draft-x",
            plan=plan,
            confirmation_token=valid,
        )

    assert called["hit"], (
        "verify_confirmation should compare via secrets.compare_digest "
        "to defeat timing-oracle attacks; saw direct equality instead"
    )
