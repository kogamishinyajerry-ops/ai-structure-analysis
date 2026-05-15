"""Tests for the Tier 1 reviewer bundle exporter (FM-04a Phase 4 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from app.services.reporting.reviewer_bundle import (
    ReviewerBundleInputs,
    build_reviewer_bundle,
    reviewer_bundle_filename,
)


def _write_metrics(tmp_path: Path, case_id: str, *, name_suffix: str = "") -> Path:
    payload = {
        "case_id": case_id,
        "perforation_marker": "perforated_candidate",
        "projectile_initial_velocity_m_per_s": 600.0,
        "residual_velocity_candidate_m_per_s": 75.0,
        "crossing_evidence": {
            "front_face_crossed": True,
            "back_face_crossed": True,
            "first_back_face_crossing_t_s": 5e-5,
        },
        "energy_audit": {
            "status": "closed_aggregate",
            "initial_kinetic_energy_j": 1731.0,
            "residual_kinetic_energy_j": 575.5,
            "aggregate_internal_energy_j": 826.6,
            "external_work_j": 0.0,
            "energy_balance_error_pct": 19.0,
            "breakdown_status": "aggregated_into_internal_energy",
            "missing_terms": [],
        },
    }
    out = tmp_path / f"{case_id}_metrics{name_suffix}.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def _write_convergence(tmp_path: Path, case_id: str) -> Path:
    # Mirror the real orchestrator output: claim_boundary / claim_impact
    # fields are written by build_convergence_study so the per-member
    # audit can verify the Tier 1 banner is preserved end-to-end.
    payload = {
        "case_id": case_id,
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {"candidate_stability": "candidate_observed_stable"},
        "dt_sweep": {"candidate_stability": "candidate_observed_stable"},
        "row_count": 2,
        "tolerance_pct": 5.0,
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "claim_impact": (
            "Tier 1 candidate mesh and time-step convergence study only; "
            "not signed validation; not benchmark agreement"
        ),
    }
    out = tmp_path / f"{case_id}_convergence.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def _write_deck(tmp_path: Path, name: str) -> Path:
    out = tmp_path / name
    out.write_text(f"fake deck {name}\n", encoding="utf-8")
    return out


def _build_full_inputs(tmp_path: Path, case_id: str) -> ReviewerBundleInputs:
    metrics = _write_metrics(tmp_path, case_id)
    convergence = _write_convergence(tmp_path, case_id)
    starter = _write_deck(tmp_path, f"{case_id}_starter.rad")
    engine = _write_deck(tmp_path, f"{case_id}_engine.rad")
    notes = tmp_path / f"{case_id}_NOTES.md"
    notes.write_text("# notes\n", encoding="utf-8")
    return ReviewerBundleInputs(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=convergence,
        notes_path=notes,
    )


def test_bundle_requires_at_least_one_case(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_reviewer_bundle([], repo_root=tmp_path)


def test_single_case_bundle_contains_expected_members(tmp_path: Path) -> None:
    inputs = _build_full_inputs(tmp_path, "GS-102-phase4c-a")
    zip_bytes = build_reviewer_bundle([inputs], repo_root=tmp_path)
    assert zip_bytes.startswith(b"PK\x03\x04")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = sorted(zf.namelist())
    expected = [
        "BUNDLE_MANIFEST.json",
        "GS-102-phase4c-a/GS-102-phase4c-a_Tier1_candidate_report.md",
        "GS-102-phase4c-a/GS-102-phase4c-a_acceptance_packet.json",
        "GS-102-phase4c-a/GS-102-phase4c-a_completeness_scorecard.json",
        "GS-102-phase4c-a/GS-102-phase4c-a_convergence_study.json",
    ]
    assert names == expected


def test_multi_case_bundle_emits_one_dir_per_case(tmp_path: Path) -> None:
    case_a = _build_full_inputs(tmp_path, "GS-A-candidate")
    case_b = _build_full_inputs(tmp_path, "GS-B-candidate")
    zip_bytes = build_reviewer_bundle([case_a, case_b], repo_root=tmp_path)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        manifest_text = zf.read("BUNDLE_MANIFEST.json").decode("utf-8")

    assert any("GS-A-candidate/" in n for n in names)
    assert any("GS-B-candidate/" in n for n in names)

    manifest = json.loads(manifest_text)
    assert manifest["cohort_count"] == 2
    assert {c["case_id"] for c in manifest["cases"]} == {"GS-A-candidate", "GS-B-candidate"}


def test_bundle_omits_convergence_member_when_absent(tmp_path: Path) -> None:
    case_id = "GS-noconvergence-candidate"
    metrics = _write_metrics(tmp_path, case_id)
    inputs = ReviewerBundleInputs(
        case_id=case_id,
        ballistic_metrics_path=metrics,
    )
    zip_bytes = build_reviewer_bundle([inputs], repo_root=tmp_path)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("BUNDLE_MANIFEST.json").decode("utf-8"))
    assert not any("convergence_study.json" in n for n in names)
    # Manifest still lists the case, with convergence_study = None.
    case_entry = next(c for c in manifest["cases"] if c["case_id"] == case_id)
    assert case_entry["members"]["convergence_study"] is None
    assert case_entry["members"]["acceptance_packet"].endswith("_acceptance_packet.json")


def test_bundle_raises_when_metrics_missing(tmp_path: Path) -> None:
    inputs = ReviewerBundleInputs(
        case_id="GS-missing-candidate",
        ballistic_metrics_path=tmp_path / "no_such_file.json",
    )
    with pytest.raises(FileNotFoundError, match="ballistic_metrics.json missing"):
        build_reviewer_bundle([inputs], repo_root=tmp_path)


def test_bundle_manifest_preserves_tier1_boundary(tmp_path: Path) -> None:
    inputs = _build_full_inputs(tmp_path, "GS-phase4c-tier1-banner-candidate")
    zip_bytes = build_reviewer_bundle([inputs], repo_root=tmp_path)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        manifest_text = zf.read("BUNDLE_MANIFEST.json").decode("utf-8")
    text = manifest_text.lower()
    assert "tier1_engineering_candidate" in text
    assert "not_signed_validation" in text
    assert "not_benchmark_agreement" in text
    assert "not signed validation" in text
    assert "not a sealed fm-04b p8 packet" in text


def test_every_member_preserves_tier1_boundary(tmp_path: Path) -> None:
    """Strip-then-check audit over every member text in the zip."""
    inputs = _build_full_inputs(tmp_path, "GS-phase4c-audit-candidate")
    zip_bytes = build_reviewer_bundle([inputs], repo_root=tmp_path)
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            text = zf.read(name).decode("utf-8").lower()
            stripped = (
                text.replace("not_signed_validation", "")
                .replace("not_benchmark_agreement", "")
                .replace("not signed validation", "")
                .replace("not benchmark agreement", "")
            )
            for token in forbidden:
                assert token not in stripped, f"member {name!r} leaked forbidden wording {token!r}"
            # Positive disclaimers MUST appear somewhere.
            assert (
                "tier 1" in text
                or "tier1_engineering_candidate" in text
                or "not signed validation" in text
            ), f"member {name!r} has no Tier 1 banner / disclaimer"


def test_filename_uses_case_count(tmp_path: Path) -> None:
    assert reviewer_bundle_filename(1) == "tier1_reviewer_bundle_1cases.zip"
    assert reviewer_bundle_filename(5) == "tier1_reviewer_bundle_5cases.zip"
