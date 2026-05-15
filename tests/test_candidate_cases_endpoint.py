"""Tests for /api/v1/candidate-cases (FM-04a Phase 2 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.api.routes import candidate_cases


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a synthetic repo with a few candidate dirs + signed dir."""
    golden = tmp_path / "golden_samples"
    (golden / "GS-102-candidate" / "data").mkdir(parents=True)
    (golden / "GS-102-candidate" / "data" / "model_00_0000.rad").write_text("starter\n")
    (golden / "GS-102-candidate" / "data" / "model_00_0001.rad").write_text("engine\n")
    (golden / "GS-102-candidate" / "NOTES.md").write_text(
        "# GS-102-candidate Notes\n\n"
        "> Tier 1 engineering candidate; not signed validation.\n\n"
        "Synthetic note body for test purposes.\n"
    )

    (golden / "GS-102-refined-candidate" / "data").mkdir(parents=True)
    (golden / "GS-102-refined-candidate" / "data" / "model_00_0000.rad").write_text(
        "refined starter\n"
    )
    (golden / "GS-102-refined-candidate" / "data" / "model_00_0001.rad").write_text(
        "refined engine\n"
    )

    (golden / "GS-102-hifi-candidate" / "data").mkdir(parents=True)
    (golden / "GS-102-hifi-candidate" / "NOTES.md").write_text("# hifi notes\n")

    # Signed `^GS-\d{3}$` registry entry — must NOT be surfaced.
    (golden / "GS-001" / "data").mkdir(parents=True)
    (golden / "GS-001" / "data" / "model_00_0000.rad").write_text("signed\n")

    # Sibling generator scripts the picker may surface.
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "gen_gs102_refined_deck.py").write_text("# generator stub\n")
    (scripts / "gen_gs102_hifi_deck.py").write_text("# generator stub\n")

    monkeypatch.setattr(candidate_cases, "_repo_root", lambda: tmp_path)
    return tmp_path


def test_scan_includes_only_candidate_dirs(fake_repo: Path) -> None:
    cases = candidate_cases._scan_candidate_cases(fake_repo)
    ids = [case["case_id"] for case in cases]
    assert "GS-102-candidate" in ids
    assert "GS-102-refined-candidate" in ids
    assert "GS-102-hifi-candidate" in ids
    assert "GS-001" not in ids, "Signed ^GS-\\d{3}$ entry must never be exposed through the picker"


def test_describe_case_extracts_deck_paths_and_notes_excerpt(fake_repo: Path) -> None:
    cases = candidate_cases._scan_candidate_cases(fake_repo)
    by_id = {case["case_id"]: case for case in cases}
    candidate = by_id["GS-102-candidate"]
    assert candidate["claim_tier"] == "Tier 1 engineering candidate"
    assert candidate["claim_boundary"] == candidate_cases.CLAIM_BOUNDARY
    assert candidate["starter_deck_relpath"].endswith(
        "golden_samples/GS-102-candidate/data/model_00_0000.rad"
    )
    assert candidate["engine_deck_relpath"].endswith(
        "golden_samples/GS-102-candidate/data/model_00_0001.rad"
    )
    assert candidate["notes_excerpt"] is not None
    assert "Tier 1 engineering candidate" in candidate["notes_excerpt"]


def test_generator_script_relpath_is_resolved_when_present(fake_repo: Path) -> None:
    cases = candidate_cases._scan_candidate_cases(fake_repo)
    by_id = {case["case_id"]: case for case in cases}
    assert by_id["GS-102-refined-candidate"]["generator_script_relpath"] == (
        "scripts/gen_gs102_refined_deck.py"
    )
    assert by_id["GS-102-hifi-candidate"]["generator_script_relpath"] == (
        "scripts/gen_gs102_hifi_deck.py"
    )
    # GS-102-candidate has no matching gen script in our synthetic repo.
    assert by_id["GS-102-candidate"]["generator_script_relpath"] is None


def test_list_endpoint_payload_has_count_and_tier1_claim_impact(
    fake_repo: Path,
) -> None:
    import asyncio

    payload = asyncio.run(candidate_cases.list_candidate_cases())
    assert payload["count"] == 3
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "Tier 1 candidate-case picker" in payload["claim_impact"]
    assert "not signed validation" in payload["claim_impact"]
    assert "not benchmark agreement" in payload["claim_impact"]
    case_ids = [c["case_id"] for c in payload["cases"]]
    assert "GS-001" not in case_ids


def test_endpoint_returns_empty_when_golden_samples_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(candidate_cases, "_repo_root", lambda: tmp_path)
    cases = candidate_cases._scan_candidate_cases(tmp_path)
    assert cases == []


def test_endpoint_payload_preserves_forbidden_wording_audit(fake_repo: Path) -> None:
    import asyncio

    payload = asyncio.run(candidate_cases.list_candidate_cases())
    text = (
        payload["claim_boundary"]
        + " "
        + payload["claim_impact"]
        + " "
        + " ".join(str(case.get("notes_excerpt") or "") for case in payload["cases"])
    ).lower()
    for positive_claim in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert positive_claim not in text


def test_endpoint_lists_only_dirs_matching_case_id_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    golden = tmp_path / "golden_samples"
    # Valid candidate.
    (golden / "GS-200-candidate" / "data").mkdir(parents=True)
    # Suffix-matching but invalid id (whitespace etc.)
    (golden / "Bad Name-candidate").mkdir(parents=True)
    # File (not dir) ending in -candidate.
    (golden / "stray-candidate").mkdir(parents=True)
    (golden / "stray-candidate" / "fake.txt").write_text("x")
    # Non-matching: missing suffix.
    (golden / "GS-200").mkdir(parents=True)

    monkeypatch.setattr(candidate_cases, "_repo_root", lambda: tmp_path)
    cases = candidate_cases._scan_candidate_cases(tmp_path)
    ids = {case["case_id"] for case in cases}
    assert "GS-200-candidate" in ids
    assert "GS-200" not in ids
    # "Bad Name-candidate" contains a space → regex rejects it.
    assert "Bad Name-candidate" not in ids
