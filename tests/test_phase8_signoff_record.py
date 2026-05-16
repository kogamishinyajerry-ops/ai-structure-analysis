"""FM-04a Phase 8 A — Tier 1 signoff record builder tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import SIGNOFF_RECORD_SCHEMA_VERSION
from app.services.reporting.signoff_record import (
    _FORBIDDEN_VERDICT_TOKENS,
    CLAIM_TIER,
    SUPPORTED_SIGNOFF_VERDICTS,
    _audit_verdict_whitelist,
    read_signoff_history,
    write_signoff_record,
)

# ---------------------------------------------------------------------
# Verdict whitelist + import-time audit (Phase 8 guard C: -10 / -8)
# ---------------------------------------------------------------------


def test_verdict_whitelist_contains_no_tier2_promotion_token() -> None:
    """Phase 8 anti-gaming guard C: -10. Load-bearing."""
    for verdict in SUPPORTED_SIGNOFF_VERDICTS:
        lowered = verdict.lower()
        for token in _FORBIDDEN_VERDICT_TOKENS:
            assert token not in lowered, (
                f"Verdict {verdict!r} contains forbidden Tier 2 promotion token {token!r}"
            )


def test_verdict_whitelist_has_expected_four_verdicts() -> None:
    """Pins the whitelist to exactly 4 verdicts; expansion requires
    re-running ``_audit_verdict_whitelist`` and updating this test."""
    assert SUPPORTED_SIGNOFF_VERDICTS == (
        "watching",
        "needs_more_evidence",
        "needs_more_convergence",
        "blocked_pending_input",
    )


def test_audit_verdict_whitelist_raises_when_synthetically_tampered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synthetic tamper: insert a Tier 2 verdict and verify the audit
    refuses. Phase 8 anti-gaming guard C: -8."""
    import app.services.reporting.signoff_record as sr

    tampered = sr.SUPPORTED_SIGNOFF_VERDICTS + ("ready_for_tier_2",)
    monkeypatch.setattr(sr, "SUPPORTED_SIGNOFF_VERDICTS", tampered)
    with pytest.raises(RuntimeError, match="forbidden Tier 2 promotion token"):
        _audit_verdict_whitelist()


# ---------------------------------------------------------------------
# Write — happy path + schema stamping
# ---------------------------------------------------------------------


def test_write_signoff_record_stamps_schema_version(tmp_path: Path) -> None:
    record = write_signoff_record(
        "GS-A-candidate",
        "alice",
        "watching",
        "Tier 1 candidate review; monitoring.",
        repo_root=tmp_path,
        now_utc=datetime(2026, 5, 16, 10, 0, 0, tzinfo=UTC),
    )
    assert record.schema_version == SIGNOFF_RECORD_SCHEMA_VERSION
    assert record.claim_tier == CLAIM_TIER
    out_path = tmp_path / "reports" / "signoffs" / "GS-A-candidate" / "2026-05-16T100000Z.json"
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SIGNOFF_RECORD_SCHEMA_VERSION
    assert payload["case_id"] == "GS-A-candidate"
    assert payload["reviewer"] == "alice"
    assert payload["verdict"] == "watching"
    assert payload["notes"] == "Tier 1 candidate review; monitoring."
    assert payload["signoff_utc"] == "2026-05-16T100000Z"


def test_write_signoff_record_uses_utc_iso8601_filename(tmp_path: Path) -> None:
    """Phase 8 anti-gaming guard M: -2 — no local time in filenames."""
    record = write_signoff_record(
        "GS-A-candidate",
        "bob",
        "needs_more_evidence",
        "Wants more snapshots.",
        repo_root=tmp_path,
        now_utc=datetime(2026, 5, 16, 23, 45, 7, tzinfo=UTC),
    )
    out_path = tmp_path / "reports" / "signoffs" / "GS-A-candidate" / "2026-05-16T234507Z.json"
    assert out_path.exists()
    assert record.signoff_utc.endswith("Z")
    assert "T" in record.signoff_utc


# ---------------------------------------------------------------------
# Write — rejection paths
# ---------------------------------------------------------------------


def test_write_signoff_rejects_signed_registry_case_id(tmp_path: Path) -> None:
    """Phase 8 anti-gaming guard C: -10 indirect — signed registry
    refused at write site, defense in depth."""
    with pytest.raises(ValueError, match="signed registry case_id"):
        write_signoff_record(
            "GS-001",
            "alice",
            "watching",
            "n/a",
            repo_root=tmp_path,
        )


def test_write_signoff_rejects_empty_case_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-empty case_id"):
        write_signoff_record(
            "",
            "alice",
            "watching",
            "n/a",
            repo_root=tmp_path,
        )


def test_write_signoff_rejects_empty_reviewer(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-empty reviewer"):
        write_signoff_record(
            "GS-A-candidate",
            "   ",
            "watching",
            "n/a",
            repo_root=tmp_path,
        )


def test_write_signoff_rejects_unknown_verdict(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not in the whitelist"):
        write_signoff_record(
            "GS-A-candidate",
            "alice",
            "ready_for_tier_2",  # Tier 2 token — load-bearing reject
            "n/a",
            repo_root=tmp_path,
        )


def test_write_signoff_rejects_forbidden_notes_token(tmp_path: Path) -> None:
    """Phase 8 anti-gaming guard C: -5."""
    with pytest.raises(ValueError, match="forbidden positive claim"):
        write_signoff_record(
            "GS-A-candidate",
            "alice",
            "watching",
            "This case has benchmark agreement.",  # forbidden positive
            repo_root=tmp_path,
        )


def test_write_signoff_accepts_forbidden_token_in_disclaimer_form(tmp_path: Path) -> None:
    """`not <claim>` disclaimer form must be accepted."""
    record = write_signoff_record(
        "GS-A-candidate",
        "alice",
        "watching",
        "This is Tier 1 only — not benchmark agreement, not signed validation.",
        repo_root=tmp_path,
    )
    assert record.notes.startswith("This is Tier 1 only")


def test_write_signoff_rejects_golden_samples_root(tmp_path: Path) -> None:
    """Phase 8 anti-gaming guard C: -10 indirect."""
    golden = tmp_path / "golden_samples"
    golden.mkdir()
    with pytest.raises(ValueError, match="golden_samples"):
        write_signoff_record(
            "GS-A-candidate",
            "alice",
            "watching",
            "n/a",
            repo_root=golden,
        )


# ---------------------------------------------------------------------
# Read — positive paths + chronology
# ---------------------------------------------------------------------


def test_read_signoff_history_empty_returns_empty_list(tmp_path: Path) -> None:
    assert read_signoff_history("GS-A-candidate", repo_root=tmp_path) == []


def test_read_signoff_history_returns_chronological_order(tmp_path: Path) -> None:
    for hour, verdict in (
        (10, "watching"),
        (12, "needs_more_evidence"),
        (14, "needs_more_convergence"),
    ):
        write_signoff_record(
            "GS-A-candidate",
            "alice",
            verdict,
            f"Round at {hour}.",
            repo_root=tmp_path,
            now_utc=datetime(2026, 5, 16, hour, 0, 0, tzinfo=UTC),
        )
    history = read_signoff_history("GS-A-candidate", repo_root=tmp_path)
    assert len(history) == 3
    assert [r.signoff_utc for r in history] == [
        "2026-05-16T100000Z",
        "2026-05-16T120000Z",
        "2026-05-16T140000Z",
    ]
    assert [r.verdict for r in history] == [
        "watching",
        "needs_more_evidence",
        "needs_more_convergence",
    ]


def test_read_signoff_history_rejects_signed_registry(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="signed registry case_id"):
        read_signoff_history("GS-001", repo_root=tmp_path)


def test_read_signoff_history_is_tolerant_of_unknown_extra_fields(tmp_path: Path) -> None:
    """A future MINOR bump that adds a field must remain readable
    by current code (additive bump policy)."""
    case_dir = tmp_path / "reports" / "signoffs" / "GS-A-candidate"
    case_dir.mkdir(parents=True)
    payload = {
        "schema_version": "1.0.0",
        "case_id": "GS-A-candidate",
        "reviewer": "alice",
        "verdict": "watching",
        "signoff_utc": "2026-05-16T100000Z",
        "notes": "n/a",
        "claim_tier": CLAIM_TIER,
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "claim_impact": (
            "Tier 1 candidate review judgments only; not signed "
            "validation; not benchmark agreement."
        ),
        "future_extra_field": "ignored on read",
    }
    (case_dir / "2026-05-16T100000Z.json").write_text(json.dumps(payload), encoding="utf-8")
    history = read_signoff_history("GS-A-candidate", repo_root=tmp_path)
    assert len(history) == 1
    assert history[0].verdict == "watching"


# ---------------------------------------------------------------------
# Every supported verdict has a positive test (Phase 8 guard T: -2 each)
# ---------------------------------------------------------------------


@pytest.mark.parametrize("verdict", SUPPORTED_SIGNOFF_VERDICTS)
def test_every_supported_verdict_has_positive_path(verdict: str, tmp_path: Path) -> None:
    record = write_signoff_record(
        "GS-A-candidate",
        "alice",
        verdict,
        "Tier 1 monitoring round.",
        repo_root=tmp_path,
    )
    assert record.verdict == verdict


# ---------------------------------------------------------------------
# Tier 1 disclaimer trio preserved
# ---------------------------------------------------------------------


def test_record_envelope_carries_tier1_disclaimer_trio(tmp_path: Path) -> None:
    record = write_signoff_record(
        "GS-A-candidate",
        "alice",
        "watching",
        "Tier 1 monitoring round.",
        repo_root=tmp_path,
    )
    assert record.claim_tier == "Tier 1 engineering candidate"
    assert "not_signed_validation" in record.claim_boundary
    assert "not_benchmark_agreement" in record.claim_boundary
    assert "not signed validation" in record.claim_impact
    assert "not benchmark agreement" in record.claim_impact
