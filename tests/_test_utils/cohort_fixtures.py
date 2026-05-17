"""Shared 5-case cohort fixture helpers for Phase 15+ journey tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 16 retrospective carry-forward (consolidated into Phase 17 D):
**the 5-case cohort fixture-seeding pattern**. Each prior journey file
(Phase 15 D / Phase 16 D / Phase 17 D) used to inline ~4-5 helper
functions per file (``_stub_path``, ``_explicit_dynamics_healthy_input``,
``_pv_case_input``, ``_clean_leak_case_input``, ``_regressed_leak_case_input``);
that pattern is hoisted here so a future cohort-fixture change lands in
one place.

A meta-test in ``tests/test_phase17_cohort_fixtures_ssot.py`` enforces
that Phase 15+ journey files do NOT re-inline any of these helpers
(lexical detection of the canonical ``def _stub_path(`` /
``def _clean_leak_case_input(`` patterns inside journey files).

All helpers:
* Write strictly under ``tmp_path`` (the ``tmp`` argument). The real
  ``reports/snapshots/`` tree is NEVER touched (V:-3 invariant).
* Read from the real ``golden_samples/<case_id>/data/`` tree to seed
  per-case ``SnapshotCaseInput`` field paths. The seed read is a
  filesystem byte read; nothing is mutated under ``golden_samples/``.

Exported helper protocol (Phase 17 D SSOT contract):

* :func:`make_stub_path` — write a tiny stub artifact under ``tmp``
  (used for starter/engine/generator decks where the case-completeness
  rubric only checks presence).
* :func:`make_explicit_dynamics_healthy_input` — assemble a
  ``SnapshotCaseInput`` for a healthy explicit_dynamics case (5
  artifact fields populated; ``result_mesh_path=None``).
* :func:`make_pv_case_input` — assemble a ``SnapshotCaseInput`` for a
  linear_static_pv case (uses stub fallbacks for missing starter/engine/
  generator artifacts).
* :func:`make_clean_leak_case_input` — assemble a ``SnapshotCaseInput``
  for the energy-leak case in its CLEAN variant (energy_audit ==
  "closed_aggregate"). The ``suffix`` keyword keeps per-arc clean
  staging directories disjoint when the same ``tmp`` hosts multiple
  arc-shape snapshots side-by-side (Phase 16 D Journey 2 + Phase 17 D
  Journey 2 use this).
* :func:`make_regressed_leak_case_input` — assemble a
  ``SnapshotCaseInput`` for the energy-leak case in its REGRESSED
  variant (3 optional artifacts omitted; drops trust below the 50-pt
  floor).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.reporting.cohort_snapshot import SnapshotCaseInput


def make_stub_path(tmp: Path, name: str) -> Path:
    """Write a tiny stub file under ``tmp`` and return its path.

    Used for starter / engine / generator decks where the
    case-completeness rubric only checks presence. The artifact body
    bears the Tier 1 disclaimer in a comment so a future grep audit
    surfaces the deliberate stub origin.
    """
    p = tmp / name
    if not p.exists():
        p.write_text(
            "# stub artifact for cohort-fixture seeding; not signed validation",
            encoding="utf-8",
        )
    return p


def make_explicit_dynamics_healthy_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    """SnapshotCaseInput for a healthy explicit_dynamics case.

    Reads from ``tmp/golden_samples/<case_id>/data/`` (callers must
    copy the case's ``golden_samples/<case_id>`` tree into ``tmp``
    before invoking this).
    """
    fixture = tmp / "golden_samples" / case_id
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=make_stub_path(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def make_pv_case_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    """SnapshotCaseInput for a linear_static_pv case.

    The pv case fixtures don't always carry starter/engine/generator
    artifacts in the canonical paths; this helper falls back to stubs
    via :func:`make_stub_path` when the canonical path doesn't exist.
    """
    fixture = tmp / "golden_samples" / case_id
    starter = fixture / "data" / "model_00_0000.rad"
    engine = fixture / "data" / "model_00_0001.rad"
    generator = fixture / "data" / "generator.py"
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter
        if starter.is_file()
        else make_stub_path(tmp, f"{case_id}_starter.rad"),
        engine_deck_path=engine
        if engine.is_file()
        else make_stub_path(tmp, f"{case_id}_engine.rad"),
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator
        if generator.is_file()
        else make_stub_path(tmp, f"{case_id}_gen.py"),
        notes_path=None,
        analysis_type="linear_static_pv",
    )


def make_clean_leak_case_input(
    tmp: Path,
    case_id: str,
    *,
    suffix: str = "snap1_clean",
) -> SnapshotCaseInput:
    """SnapshotCaseInput for the energy-leak case in CLEAN variant.

    Builds a per-arc staging directory under
    ``tmp/cohort_fixture_<suffix>/<case_id>/`` with a mutated
    ``ballistic_metrics.json`` (``energy_audit.status =
    "closed_aggregate"``) and ``convergence_study.json``
    (``combined_verdict = "candidate_observed_stable"``). The
    ``suffix`` keyword keeps per-arc clean staging dirs disjoint when
    the same ``tmp`` hosts multiple arc-shape snapshots side-by-side
    (Phase 16 D Journey 2 + Phase 17 D Journey 2).
    """
    fixture = tmp / "golden_samples" / case_id
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate clean state. Not signed validation; not benchmark agreement."
    )
    clean_dir = tmp / f"cohort_fixture_{suffix}" / case_id
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_metrics = clean_dir / "ballistic_metrics.json"
    clean_metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    conv_src = fixture / "data" / "convergence_study.json"
    conv_payload = json.loads(conv_src.read_text(encoding="utf-8"))
    conv_payload["combined_verdict"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["dt_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["rationale"] = "Tier 1 candidate clean state. Not signed validation."
    conv_payload["dt_sweep"]["rationale"] = "Tier 1 candidate clean state. Not benchmark agreement."
    clean_conv = clean_dir / "convergence_study.json"
    clean_conv.write_text(json.dumps(conv_payload, indent=2), encoding="utf-8")

    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=clean_metrics,
        convergence_study_path=clean_conv,
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=make_stub_path(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def make_regressed_leak_case_input(
    tmp: Path,
    case_id: str,
    *,
    drop_optional_artifacts: bool = True,
) -> SnapshotCaseInput:
    """SnapshotCaseInput for the energy-leak case in REGRESSED variant.

    Reads the canonical (already-regressed) leak case fixture from
    ``tmp/golden_samples/<case_id>/data/``.

    When ``drop_optional_artifacts=True`` (default), OMITS 3 optional
    artifacts (animation_manifest, generator_script, notes) so the
    case-completeness rubric drops below the 50-pt floor at this
    snapshot. Most journey arcs use this shape to land the leak case
    in the regressed bucket.

    When ``drop_optional_artifacts=False``, keeps every artifact
    present so the ONLY axis moving across the arc is ``energy_audit``
    (Phase 16 D Journey 2 uses this for the cumulative-vs-consecutive
    coherence pin where a cleaner invariant is needed).
    """
    fixture = tmp / "golden_samples" / case_id
    if drop_optional_artifacts:
        return SnapshotCaseInput(
            case_id=case_id,
            starter_deck_path=fixture / "data" / "model_00_0000.rad",
            engine_deck_path=fixture / "data" / "model_00_0001.rad",
            ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
            convergence_study_path=fixture / "data" / "convergence_study.json",
            animation_manifest_path=None,
            result_mesh_path=None,
            generator_script_path=None,
            notes_path=None,
            analysis_type="explicit_dynamics",
        )
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=make_stub_path(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )
