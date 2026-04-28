"""Animation-manifest tests — RFC-001 §6.4 W7c.

Tier-1 tests use synthetic reader stubs satisfying the
``ReaderHandle`` / ``SupportsElementDeletion`` Protocols so the
manifest builder can be exercised without the optional
``vortex_radioss`` parser installed.

Tier-2 tests drive the actual ``OpenRadiossReader`` against the
GS-100 smoke fixture. They skip when the parser isn't available
(consistent with adjacent ballistics + adapter test modules).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from app.core.types import UnitSystem
from app.viz.animation_manifest import (
    AnimationFrame,
    AnimationManifest,
    build_manifest,
)


# ---------------------------------------------------------------------------
# Tier-1 — synthetic Reader stubs
# ---------------------------------------------------------------------------


class _StubSolutionState:
    def __init__(self, step_id: int, time: float) -> None:
        self.step_id = step_id
        self.time = time
        self.available_fields = ()  # not consulted by the manifest


class _StubMesh:
    def __init__(self, n: int, unit_system: UnitSystem) -> None:
        self.node_id_array = np.arange(1, n + 1, dtype=np.int64)
        self.unit_system = unit_system


class _StubFieldData:
    def __init__(self, vals: np.ndarray) -> None:
        self._vals = vals
        self.metadata = None

    def values(self) -> np.ndarray:
        return self._vals


class _NoErosionReader:
    """ReaderHandle-shaped stub WITHOUT element-deletion support.

    Pins the contract that the manifest skips erosion data on
    adapters that don't satisfy ``SupportsElementDeletion``
    (e.g. CalculiX)."""

    def __init__(self, frames: dict[int, tuple[float, np.ndarray]]) -> None:
        self.mesh = _StubMesh(
            n=max(arr.shape[0] for _, arr in frames.values()),
            unit_system=UnitSystem.SI_MM,
        )
        self._frames = frames
        self.solution_states = [
            _StubSolutionState(sid, t) for sid, (t, _) in sorted(frames.items())
        ]

    def get_field(self, name, step_id):  # type: ignore[no-untyped-def]
        if step_id not in self._frames:
            return None
        return _StubFieldData(self._frames[step_id][1])


class _ErosionReader(_NoErosionReader):
    """Adds ``deleted_facets_for`` so the stub satisfies
    ``SupportsElementDeletion``. Erosion flags are int8 with values in
    {0, 1} per the Protocol contract."""

    def __init__(
        self,
        frames: dict[int, tuple[float, np.ndarray]],
        erosion: dict[int, np.ndarray],
    ) -> None:
        super().__init__(frames)
        self._erosion = erosion

    def deleted_facets_for(self, step_id: int) -> np.ndarray:
        if step_id not in self._erosion:
            raise KeyError(step_id)
        return self._erosion[step_id]


def _disp(rows: list[list[float]]) -> np.ndarray:
    return np.asarray(rows, dtype=np.float64)


def test_manifest_basic_no_erosion() -> None:
    rdr = _NoErosionReader(
        frames={
            1: (0.0, _disp([[0, 0, 0], [0, 0, 0]])),
            2: (0.5, _disp([[3, 4, 0], [0, 0, 0]])),
        }
    )
    mf = build_manifest(rdr, solver_name="StubSolver")
    assert mf.solver == "StubSolver"
    assert mf.unit_system == "SI_mm"
    assert mf.has_erosion_data is False
    assert len(mf.frames) == 2
    assert mf.frames[0] == AnimationFrame(
        step_id=1, time=0.0, max_displacement_magnitude=0.0,
        eroded_facet_count=None, png_path=None, frame_index=None,
    )
    # 3-4-5 triangle → magnitude 5.
    assert mf.frames[1].max_displacement_magnitude == pytest.approx(5.0)
    assert mf.frames[1].eroded_facet_count is None


def test_manifest_includes_erosion_when_supported() -> None:
    rdr = _ErosionReader(
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (1.0, _disp([[1, 0, 0]])),
        },
        erosion={
            1: np.ones(10, dtype=np.int8),
            2: np.array([1] * 7 + [0, 0, 0], dtype=np.int8),
        },
    )
    mf = build_manifest(rdr, solver_name="StubBallistic")
    assert mf.has_erosion_data is True
    assert mf.frames[0].eroded_facet_count == 0
    assert mf.frames[1].eroded_facet_count == 3


def test_manifest_step_ids_subset_preserves_order() -> None:
    """If the caller passes a non-monotonic subset, the manifest
    preserves that order verbatim — pinned because compare-frame
    plots may want last-vs-first sequencing."""
    rdr = _NoErosionReader(
        frames={
            1: (0.0, _disp([[0, 0, 0]])),
            2: (0.5, _disp([[1, 0, 0]])),
            3: (1.0, _disp([[2, 0, 0]])),
        }
    )
    mf = build_manifest(rdr, solver_name="X", step_ids=[3, 1])
    assert [f.step_id for f in mf.frames] == [3, 1]
    assert mf.frames[0].max_displacement_magnitude == pytest.approx(2.0)
    assert mf.frames[1].max_displacement_magnitude == pytest.approx(0.0)


def test_manifest_unknown_step_id_raises_keyerror() -> None:
    """Inherits the W7d displacement_history contract: unknown step_ids
    fail upfront instead of silently fabricating zero rows."""
    rdr = _NoErosionReader(
        frames={1: (0.0, _disp([[0, 0, 0]]))}
    )
    with pytest.raises(KeyError, match="999"):
        build_manifest(rdr, solver_name="X", step_ids=[1, 999])


def test_manifest_to_json_is_diff_friendly() -> None:
    """Pretty-print + sorted keys + 2-space indent for diff review."""
    rdr = _NoErosionReader(
        frames={1: (0.0, _disp([[1, 0, 0]]))}
    )
    mf = build_manifest(rdr, solver_name="X")
    j = mf.to_json()
    parsed = json.loads(j)
    assert parsed["solver"] == "X"
    assert parsed["unit_system"] == "SI_mm"
    assert parsed["has_erosion_data"] is False
    assert len(parsed["frames"]) == 1
    # Pretty-printed (presence of newlines + indentation).
    assert "\n  " in j


def test_manifest_write_creates_parent_dir(tmp_path: Path) -> None:
    rdr = _NoErosionReader(
        frames={1: (0.0, _disp([[0, 0, 0]]))}
    )
    mf = build_manifest(rdr, solver_name="X")
    target = tmp_path / "deep" / "nested" / "manifest.json"
    out = mf.write(target)
    assert out == target
    assert target.is_file()
    parsed = json.loads(target.read_text())
    assert parsed["solver"] == "X"


def test_animation_manifest_roundtrip_preserves_frames() -> None:
    """to_json → json.loads produces a dict equivalent to asdict.
    Pins the dataclass field order so a future schema change is a
    visible diff, not a silent drift."""
    mf = AnimationManifest(
        solver="X",
        unit_system="SI_mm",
        has_erosion_data=True,
        frames=[
            AnimationFrame(
                step_id=1, time=0.0, max_displacement_magnitude=0.0,
                eroded_facet_count=0,
            ),
            AnimationFrame(
                step_id=2, time=0.5, max_displacement_magnitude=3.5,
                eroded_facet_count=2,
            ),
        ],
    )
    parsed = json.loads(mf.to_json())
    assert parsed["frames"][1]["eroded_facet_count"] == 2
    assert parsed["frames"][1]["max_displacement_magnitude"] == 3.5


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
def test_gs100_manifest_has_three_frames(gs100_reader) -> None:
    mf = build_manifest(gs100_reader, solver_name="OpenRadioss")
    assert len(mf.frames) == 3
    assert mf.solver == "OpenRadioss"
    assert mf.unit_system == "SI_mm"


@needs_parser
def test_gs100_manifest_erosion_all_zero(gs100_reader) -> None:
    """GS-100 is contact-only (74/74 alive across all frames) — pin
    the erosion-flag passthrough so a future Protocol-discovery bug
    surfaces immediately."""
    mf = build_manifest(gs100_reader, solver_name="OpenRadioss")
    assert mf.has_erosion_data is True
    assert all(f.eroded_facet_count == 0 for f in mf.frames)


@needs_parser
def test_gs100_manifest_displacement_grows_monotonically(gs100_reader) -> None:
    mf = build_manifest(gs100_reader, solver_name="OpenRadioss")
    mags = [f.max_displacement_magnitude for f in mf.frames]
    assert mags[0] == pytest.approx(0.0, abs=1e-12)
    for prev, nxt in zip(mags, mags[1:]):
        assert nxt >= prev, f"max-disp regressed: {mags}"
    assert mags[-1] > 0.0


@needs_parser
def test_gs100_manifest_write_roundtrip(gs100_reader, tmp_path: Path) -> None:
    mf = build_manifest(gs100_reader, solver_name="OpenRadioss")
    out = mf.write(tmp_path / "manifest.json")
    parsed = json.loads(out.read_text())
    assert parsed["solver"] == "OpenRadioss"
    assert parsed["has_erosion_data"] is True
    assert len(parsed["frames"]) == 3
