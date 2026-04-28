"""Tests for the ballistic-penetration summary draft generator —
RFC-001 §6.4 W7f.

Tier-1 tests use synthetic ReaderHandle / SupportsElementDeletion
stubs — no parser, no fixtures. Tier-2 tests drive the
OpenRadiossReader against the GS-100 smoke fixture (parser-required;
GS-100 is the contact-only baseline so the perforation-event branch
is exercised via the synthetic erosion-shaped stub instead).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from app.core.types import (
    CanonicalField,
    ComponentType,
    CoordinateSystemKind,
    FieldLocation,
    FieldMetadata,
    UnitSystem,
)
from app.models import EvidenceBundle
from app.services.report.draft import (
    generate_ballistic_penetration_summary,
)
from app.services.report.templates import (
    BALLISTIC_PENETRATION_SUMMARY,
    validate_report,
)


# ---------------------------------------------------------------------------
# Tier-1 — synthetic reader stubs
# ---------------------------------------------------------------------------


class _StubSolutionState:
    def __init__(self, step_id: int, time: float) -> None:
        self.step_id = step_id
        self.time = time
        self.available_fields = (CanonicalField.DISPLACEMENT,)


class _StubMesh:
    def __init__(self, n: int, unit_system: UnitSystem) -> None:
        self.node_id_array = np.arange(1, n + 1, dtype=np.int64)
        self.unit_system = unit_system


def _stub_metadata(
    unit_system: UnitSystem, *, step_id: int = 1
) -> FieldMetadata:
    """Plausible metadata for the synthetic stub's DISPLACEMENT field.

    ``source_file`` is parameterised by ``step_id`` so the per-step
    audit-trail contract introduced after Codex R1 (HIGH) can be
    pinned: each evidence item must inherit metadata from the file
    its value actually came from, not from an arbitrary peer frame.
    """
    return FieldMetadata(
        name=CanonicalField.DISPLACEMENT,
        location=FieldLocation.NODE,
        component_type=ComponentType.VECTOR_3D,
        unit_system=unit_system,
        source_solver="StubSolver",
        source_field_name="coorA(step)-coorA(0)",
        source_file=Path(f"/tmp/stub.A{step_id:03d}"),
        coordinate_system=CoordinateSystemKind.GLOBAL.value,
        was_averaged=False,
    )


class _StubFieldData:
    def __init__(self, vals: np.ndarray, metadata: FieldMetadata) -> None:
        self._vals = vals
        self.metadata = metadata

    def values(self) -> np.ndarray:
        return self._vals


class _NoErosionReader:
    """Minimal ReaderHandle-shaped stub WITHOUT element-deletion support
    (CalculiX-shaped). The ballistic generator must produce a 2-evidence
    section without erosion / perforation citations."""

    def __init__(
        self,
        unit_system: UnitSystem,
        frames: dict[int, tuple[float, np.ndarray]],
    ) -> None:
        n = max(arr.shape[0] for _, arr in frames.values())
        self.mesh = _StubMesh(n, unit_system)
        self._frames = frames
        self._unit_system = unit_system
        self.solution_states = [
            _StubSolutionState(sid, t) for sid, (t, _) in sorted(frames.items())
        ]
        self.materials: dict[str, object] = {}
        self.boundary_conditions: list[object] = []

    def get_field(self, name, step_id):  # type: ignore[no-untyped-def]
        if name is not CanonicalField.DISPLACEMENT:
            return None
        if step_id not in self._frames:
            return None
        # Per-step metadata so source_file actually varies across
        # frames — the audit-trail regression test depends on this.
        return _StubFieldData(
            self._frames[step_id][1],
            _stub_metadata(self._unit_system, step_id=step_id),
        )

    def close(self) -> None:
        pass


class _ErosionReader(_NoErosionReader):
    """Add deleted_facets_for so the stub satisfies
    SupportsElementDeletion. This is the OpenRadioss-shaped stub."""

    def __init__(
        self,
        unit_system: UnitSystem,
        frames: dict[int, tuple[float, np.ndarray]],
        erosion: dict[int, np.ndarray],
    ) -> None:
        super().__init__(unit_system, frames)
        self._erosion = erosion

    def deleted_facets_for(self, step_id: int) -> np.ndarray:
        if step_id not in self._erosion:
            raise KeyError(step_id)
        return self._erosion[step_id]


def _disp(rows: list[list[float]]) -> np.ndarray:
    return np.asarray(rows, dtype=np.float64)


# ---------------------------------------------------------------------------
# Tier-1 cases
# ---------------------------------------------------------------------------


def test_no_erosion_reader_produces_two_evidence_items() -> None:
    """CalculiX-shaped (no SupportsElementDeletion) → DURATION + MAX-DISP
    only. Section content cites both EV-* tokens; template requires 2."""
    rdr = _NoErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={
            1: (0.0, _disp([[0, 0, 0], [0, 0, 0]])),
            2: (0.5, _disp([[3, 4, 0], [0, 0, 0]])),  # max ||u|| = 5
        },
    )
    report, bundle = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
    )
    ev_ids = {ev.evidence_id for ev in bundle.evidence_items}
    assert ev_ids == {"EV-BALLISTIC-DURATION", "EV-BALLISTIC-MAX-DISP"}
    section = report.sections[0]
    assert "EV-BALLISTIC-DURATION" in section.content
    assert "EV-BALLISTIC-MAX-DISP" in section.content
    # No erosion citation should leak in.
    assert "EV-BALLISTIC-EROSION-FINAL" not in section.content
    assert "EV-BALLISTIC-PERFORATION-EVENT" not in section.content


def test_no_erosion_reader_section_has_no_perforation_text() -> None:
    """Don't add a 'no perforation observed' bullet for adapters that
    don't support erosion at all — that line is reserved for the case
    where erosion IS supported but didn't fire."""
    rdr = _NoErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (1.0, _disp([[1, 0, 0]])),
        },
    )
    report, _ = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
    )
    assert "perforation observed" not in report.sections[0].content
    assert "未观察到" not in report.sections[0].content


def test_erosion_reader_no_perforation_records_observation_text() -> None:
    """Erosion adapter + run with no actual erosion → no
    EV-BALLISTIC-PERFORATION-EVENT (a non-event isn't citeable per
    ADR-012); section text records 'no perforation observed' so the
    engineer sees the explicit baseline."""
    rdr = _ErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (1.0, _disp([[1, 0, 0]])),
        },
        erosion={
            1: np.ones(74, dtype=np.int8),
            2: np.ones(74, dtype=np.int8),
        },
    )
    report, bundle = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
    )
    ev_ids = {ev.evidence_id for ev in bundle.evidence_items}
    assert "EV-BALLISTIC-EROSION-FINAL" in ev_ids
    assert "EV-BALLISTIC-PERFORATION-EVENT" not in ev_ids
    section_content = report.sections[0].content
    assert "no perforation observed" in section_content
    # ADR-012 / RFC-001 §2.4 rule 1: every claim line must reference an
    # EV-* evidence_id, including the "did not happen" claim. Pre-fix
    # the no-perforation line emitted no cite and the DOCX exporter
    # refused the report. Verify the perforation-event line ends with
    # the EV-BALLISTIC-EROSION-FINAL cite (the same evidence already
    # used by the eroded-facets-final claim).
    perforation_line = next(
        line
        for line in section_content.splitlines()
        if "Perforation event" in line
    )
    assert "(EV-BALLISTIC-EROSION-FINAL)" in perforation_line
    # GS-100-shaped baseline: 0 eroded at final.
    eroded_ev = next(
        ev for ev in bundle.evidence_items
        if ev.evidence_id == "EV-BALLISTIC-EROSION-FINAL"
    )
    assert eroded_ev.data.value == 0.0


def test_erosion_reader_with_perforation_emits_event_evidence() -> None:
    """Erosion adapter + actual erosion observed → all 4 evidence
    items present. The perforation event is the FIRST step where
    any facet eroded."""
    rdr = _ErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (0.25, _disp([[1, 0, 0]])),
            3: (0.5, _disp([[2, 0, 0]])),
        },
        erosion={
            1: np.ones(10, dtype=np.int8),                       # alive
            2: np.array([1, 1, 0, 1] + [1] * 6, dtype=np.int8),   # 1 eroded
            3: np.array([1, 0, 0, 1] + [1] * 6, dtype=np.int8),   # 2 eroded
        },
    )
    report, bundle = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
    )
    ev_ids = {ev.evidence_id for ev in bundle.evidence_items}
    assert ev_ids == {
        "EV-BALLISTIC-DURATION",
        "EV-BALLISTIC-MAX-DISP",
        "EV-BALLISTIC-EROSION-FINAL",
        "EV-BALLISTIC-PERFORATION-EVENT",
    }
    perf = next(
        ev for ev in bundle.evidence_items
        if ev.evidence_id == "EV-BALLISTIC-PERFORATION-EVENT"
    )
    # Perforation event should be at step 2 (first eroded), time = 0.25.
    assert perf.data.value == pytest.approx(0.25)
    eroded_final = next(
        ev for ev in bundle.evidence_items
        if ev.evidence_id == "EV-BALLISTIC-EROSION-FINAL"
    )
    assert eroded_final.data.value == 2.0


def test_peak_disp_reports_the_step_at_which_it_occurred() -> None:
    """Peak displacement is global across the time axis. Pin that
    the evidence's location string carries the actual peak step,
    not e.g. the final state."""
    rdr = _NoErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (0.25, _disp([[10, 0, 0]])),  # peak here
            3: (0.5, _disp([[3, 0, 0]])),    # rebound
        },
    )
    _, bundle = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
    )
    peak = next(
        ev for ev in bundle.evidence_items
        if ev.evidence_id == "EV-BALLISTIC-MAX-DISP"
    )
    assert peak.data.value == pytest.approx(10.0)
    assert "step_id=2" in peak.data.location


def test_template_validation_passes_for_no_erosion_baseline() -> None:
    """Generator output must satisfy the BALLISTIC_PENETRATION_SUMMARY
    contract (≥2 distinct citations, level-1 section title)."""
    rdr = _NoErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (1.0, _disp([[5, 0, 0]])),
        },
    )
    report, bundle = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
    )
    # validate_report raises TemplateValidationError on contract miss;
    # any other path means the contract holds.
    validate_report(report, bundle, template=BALLISTIC_PENETRATION_SUMMARY)


def test_empty_solution_states_raises_valueerror() -> None:
    """Empty reader is a contract violation, not a silent empty report."""
    rdr = _NoErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={1: (0.0, _disp([[0, 0, 0]]))},
    )
    rdr.solution_states = []
    with pytest.raises(ValueError, match="no solution states"):
        generate_ballistic_penetration_summary(
            rdr,
            project_id="P1",
            task_id="T1",
            report_id="R1",
            bundle_id="B1",
        )


def test_evidence_source_file_binds_to_owning_step() -> None:
    """Codex R1 HIGH: each evidence item's source_file must point to
    the file the value actually came from. Earlier code reused
    peak_field metadata for DURATION / EROSION-FINAL / PERFORATION-EVENT,
    so when peak displacement was at a non-final / non-perforation
    step the audit trail leaked the wrong .Axxx path.

    Repro: 3 frames where peak displacement is at step 2 but the
    final state is step 3 and erosion first appears at step 2.
    Expected source_file mapping after the fix:
        EV-BALLISTIC-DURATION       → step_3 file
        EV-BALLISTIC-MAX-DISP       → step_2 file (peak)
        EV-BALLISTIC-EROSION-FINAL  → step_3 file (final)
        EV-BALLISTIC-PERFORATION-EVENT → step_2 file (first eroded)
    """
    rdr = _ErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (0.25, _disp([[10, 0, 0]])),  # peak displacement here
            3: (0.5, _disp([[3, 0, 0]])),    # rebound; final state
        },
        erosion={
            1: np.ones(10, dtype=np.int8),
            2: np.array([1] * 9 + [0], dtype=np.int8),  # first eroded
            3: np.array([1] * 8 + [0, 0], dtype=np.int8),  # 2 eroded final
        },
    )
    _, bundle = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
    )
    by_id = {ev.evidence_id: ev for ev in bundle.evidence_items}
    assert by_id["EV-BALLISTIC-DURATION"].source_file == "/tmp/stub.A003"
    assert by_id["EV-BALLISTIC-MAX-DISP"].source_file == "/tmp/stub.A002"
    assert by_id["EV-BALLISTIC-EROSION-FINAL"].source_file == "/tmp/stub.A003"
    assert by_id["EV-BALLISTIC-PERFORATION-EVENT"].source_file == "/tmp/stub.A002"


def test_template_id_override_changes_report_id_only() -> None:
    """``template_id`` opt-in produces a report whose id differs but
    section structure is unchanged — same as static-strength
    generators' override pattern."""
    rdr = _NoErosionReader(
        unit_system=UnitSystem.SI_MM,
        frames={1: (0.0, _disp([[0, 0, 0]])), 2: (1.0, _disp([[1, 0, 0]]))},
    )
    report, _ = generate_ballistic_penetration_summary(
        rdr,
        project_id="P1",
        task_id="T1",
        report_id="R1",
        bundle_id="B1",
        template_id="custom_ballistic_v1",
        title="Custom ballistic check",
    )
    assert report.template_id == "custom_ballistic_v1"
    assert report.title == "Custom ballistic check"
    # Section title is the canonical bilingual form regardless.
    assert (
        report.sections[0].title
        == "弹道穿透时程摘要 (Ballistic-penetration time-history summary)"
    )


# ---------------------------------------------------------------------------
# Tier-2 — GS-100 integration
# ---------------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parents[2]
GS100_DIR = REPO_ROOT / "golden_samples" / "GS-100-radioss-smoke"

_HAS_PARSER = (
    importlib.util.find_spec("vortex_radioss") is not None
    and importlib.util.find_spec("lasso") is not None
)
needs_parser = pytest.mark.skipif(
    not _HAS_PARSER,
    reason="vortex_radioss / lasso-python not installed (optional 'openradioss' extra)",
)


@pytest.fixture()
def gs100_reader():
    if not _HAS_PARSER:
        pytest.skip("optional 'openradioss' extra not installed")
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    from app.adapters.openradioss import OpenRadiossReader

    rdr = OpenRadiossReader(
        root_dir=GS100_DIR,
        rootname="BOULE1V5",
        unit_system=UnitSystem.SI_MM,
    )
    try:
        yield rdr
    finally:
        rdr.close()


@needs_parser
def test_gs100_full_evidence_roster(gs100_reader) -> None:
    """OpenRadiossReader satisfies SupportsElementDeletion, so all
    erosion-related evidence is gated by 'has_erosion_data=True'.
    GS-100 is contact-only, so EV-BALLISTIC-PERFORATION-EVENT is
    absent (no perforation observed). The 3 expected items are
    DURATION, MAX-DISP, EROSION-FINAL=0."""
    report, bundle = generate_ballistic_penetration_summary(
        gs100_reader,
        project_id="GS-100",
        task_id="BOULE1V5",
        report_id="R-GS100-W7F",
        bundle_id="EB-GS100-W7F",
    )
    ev_ids = {ev.evidence_id for ev in bundle.evidence_items}
    assert ev_ids == {
        "EV-BALLISTIC-DURATION",
        "EV-BALLISTIC-MAX-DISP",
        "EV-BALLISTIC-EROSION-FINAL",
    }
    eroded = next(
        ev for ev in bundle.evidence_items
        if ev.evidence_id == "EV-BALLISTIC-EROSION-FINAL"
    )
    assert eroded.data.value == 0.0  # all 74 alive


@needs_parser
def test_gs100_template_validation_passes(gs100_reader) -> None:
    report, bundle = generate_ballistic_penetration_summary(
        gs100_reader,
        project_id="GS-100",
        task_id="BOULE1V5",
        report_id="R-GS100-W7F",
        bundle_id="EB-GS100-W7F",
    )
    validate_report(
        report, bundle, template=BALLISTIC_PENETRATION_SUMMARY
    )


@needs_parser
def test_gs100_section_text_records_no_perforation(gs100_reader) -> None:
    report, _ = generate_ballistic_penetration_summary(
        gs100_reader,
        project_id="GS-100",
        task_id="BOULE1V5",
        report_id="R-GS100-W7F",
        bundle_id="EB-GS100-W7F",
    )
    assert "no perforation observed" in report.sections[0].content


@needs_parser
def test_gs100_duration_is_about_half_ms(gs100_reader) -> None:
    """W7a deck runs to 0.5 ms; pin ±5% so a future fixture re-bake
    would be a visible test diff."""
    _, bundle = generate_ballistic_penetration_summary(
        gs100_reader,
        project_id="GS-100",
        task_id="BOULE1V5",
        report_id="R-GS100-W7F",
        bundle_id="EB-GS100-W7F",
    )
    duration = next(
        ev for ev in bundle.evidence_items
        if ev.evidence_id == "EV-BALLISTIC-DURATION"
    )
    assert duration.data.value == pytest.approx(0.5, rel=0.05)
    assert duration.data.unit == "ms"
