"""Layer-3 ballistic-derivation tests — RFC-001 §6.4 W7d.

Tier-1 tests use synthetic numpy arrays directly — they run regardless
of whether the optional ``openradioss`` extra is installed.

Tier-2 tests drive the OpenRadiossReader against the GS-100 smoke
fixture; they skip when ``vortex_radioss`` / ``lasso-python`` are
absent. GS-100 is a contact-only test (74/74 facets alive across all
3 frames), so the reader-level expectations are deliberately the
*degenerate* baseline — eroded count = 0, perforation event = None,
displacement history monotonic non-decreasing. GS-101 (W7e) will
exercise the live-erosion path once the bullet-vs-plate Johnson-Cook
deck lands.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from app.domain.ballistics import (
    count_alive,
    count_eroded,
    displacement_history,
    eroded_fraction,
    eroded_history,
    max_displacement_magnitude,
    perforation_event_step,
)

# ---------------------------------------------------------------------------
# Tier 1 — pure-array helpers
# ---------------------------------------------------------------------------


def test_count_alive_basic() -> None:
    flags = np.array([1, 1, 0, 1, 0], dtype=np.int8)
    assert count_alive(flags) == 3


def test_count_eroded_basic() -> None:
    flags = np.array([1, 1, 0, 1, 0], dtype=np.int8)
    assert count_eroded(flags) == 2


def test_eroded_fraction_basic() -> None:
    flags = np.array([1, 1, 0, 1, 0], dtype=np.int8)
    assert eroded_fraction(flags) == pytest.approx(0.4)


def test_eroded_fraction_all_alive() -> None:
    flags = np.ones(74, dtype=np.int8)
    assert eroded_fraction(flags) == pytest.approx(0.0)


def test_eroded_fraction_all_eroded() -> None:
    flags = np.zeros(10, dtype=np.int8)
    assert eroded_fraction(flags) == pytest.approx(1.0)


def test_eroded_fraction_empty_returns_zero() -> None:
    flags = np.zeros(0, dtype=np.int8)
    assert eroded_fraction(flags) == 0.0


def test_count_alive_rejects_2d() -> None:
    with pytest.raises(ValueError, match="must be 1-D"):
        count_alive(np.zeros((2, 3), dtype=np.int8))


def test_count_alive_rejects_wrong_dtype() -> None:
    with pytest.raises(ValueError, match="must be int8"):
        count_alive(np.array([1, 0], dtype=np.int32))


def test_count_alive_rejects_invalid_values() -> None:
    """Per ``SupportsElementDeletion`` contract: only 0 / 1 are valid.
    Catch a partial-corruption case so a future adapter bug doesn't
    silently slip through."""
    with pytest.raises(ValueError, match="0 \\(deleted\\) or 1 \\(alive\\)"):
        count_alive(np.array([1, 0, 2], dtype=np.int8))


def test_max_displacement_magnitude_unit_x() -> None:
    """Three nodes; one displaced 5 mm along x, two at rest. Max = 5."""
    disp = np.array(
        [[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64
    )
    assert max_displacement_magnitude(disp) == pytest.approx(5.0)


def test_max_displacement_magnitude_diagonal() -> None:
    """A single 3-4-5 triangle vector — max norm should be 5."""
    disp = np.array([[3.0, 4.0, 0.0]], dtype=np.float64)
    assert max_displacement_magnitude(disp) == pytest.approx(5.0)


def test_max_displacement_magnitude_empty_returns_zero() -> None:
    disp = np.zeros((0, 3), dtype=np.float64)
    assert max_displacement_magnitude(disp) == 0.0


def test_max_displacement_magnitude_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError, match="shape"):
        max_displacement_magnitude(np.zeros((3, 2), dtype=np.float64))


# ---------------------------------------------------------------------------
# Tier 2 — synthetic Reader stubs (no parser required)
# ---------------------------------------------------------------------------


class _StubSolutionState:
    """Minimal struct satisfying the SolutionState attribute access used
    by the Tier 2 step_id validation."""

    def __init__(self, step_id: int) -> None:
        self.step_id = step_id


class _StubReaderWithErosion:
    """Minimal ``SupportsElementDeletion`` + partial ``ReaderHandle``
    shim for unit tests. ``solution_states`` is required by the
    upfront step_id validation introduced after Codex R1 — without
    it ``displacement_history`` / ``eroded_history`` /
    ``perforation_event_step`` would not raise on unknown steps."""

    def __init__(self, by_step: dict[int, np.ndarray]) -> None:
        self._by_step = by_step
        self.solution_states = [
            _StubSolutionState(sid) for sid in sorted(by_step)
        ]

    def deleted_facets_for(self, step_id: int) -> "np.ndarray":
        if step_id not in self._by_step:
            raise KeyError(step_id)
        return self._by_step[step_id]


def test_eroded_history_synthetic() -> None:
    rdr = _StubReaderWithErosion(
        {
            1: np.ones(10, dtype=np.int8),
            2: np.array([1] * 9 + [0], dtype=np.int8),
            3: np.array([1] * 7 + [0, 0, 0], dtype=np.int8),
        }
    )
    h = eroded_history(rdr, [1, 2, 3])
    assert h == {1: 0, 2: 1, 3: 3}


def test_perforation_event_step_first_erosion() -> None:
    rdr = _StubReaderWithErosion(
        {
            1: np.ones(5, dtype=np.int8),
            2: np.ones(5, dtype=np.int8),
            3: np.array([1, 1, 0, 1, 1], dtype=np.int8),
            4: np.array([1, 0, 0, 1, 1], dtype=np.int8),
        }
    )
    assert perforation_event_step(rdr, [1, 2, 3, 4]) == 3


def test_perforation_event_step_no_erosion_returns_none() -> None:
    rdr = _StubReaderWithErosion(
        {1: np.ones(5, dtype=np.int8), 2: np.ones(5, dtype=np.int8)}
    )
    assert perforation_event_step(rdr, [1, 2]) is None


def test_perforation_event_step_skips_steps_not_in_list() -> None:
    """Step IDs not in the supplied list are not consulted — even if
    the reader holds erosion data for them. This pins the contract
    that callers control which states matter."""
    rdr = _StubReaderWithErosion(
        {
            1: np.ones(5, dtype=np.int8),
            2: np.array([0, 1, 1, 1, 1], dtype=np.int8),  # eroded but skipped
            3: np.ones(5, dtype=np.int8),
        }
    )
    assert perforation_event_step(rdr, [1, 3]) is None


def test_eroded_history_unknown_step_raises_keyerror() -> None:
    """Codex R1: unknown step_ids must fail upfront, not partial-process
    and silently mask the bad index."""
    rdr = _StubReaderWithErosion({1: np.ones(5, dtype=np.int8)})
    with pytest.raises(KeyError, match="999"):
        eroded_history(rdr, [1, 999])


def test_perforation_event_step_unknown_step_raises_keyerror() -> None:
    rdr = _StubReaderWithErosion({1: np.ones(5, dtype=np.int8)})
    with pytest.raises(KeyError, match="42"):
        perforation_event_step(rdr, [42])


# ---------------------------------------------------------------------------
# Tier 2 — synthetic Reader stubs for displacement_history validation
# ---------------------------------------------------------------------------


class _StubMesh:
    def __init__(self, n: int) -> None:
        self.node_id_array = np.arange(1, n + 1, dtype=np.int64)


class _StubFieldData:
    def __init__(self, vals: np.ndarray) -> None:
        self._vals = vals
        self.metadata = None  # not consulted by the orchestrator

    def values(self) -> np.ndarray:
        return self._vals


class _StubDispReader:
    """ReaderHandle-shaped stub that returns canned displacement fields."""

    def __init__(
        self,
        n_nodes: int,
        disp_by_step: dict[int, np.ndarray],
    ) -> None:
        self.mesh = _StubMesh(n_nodes)
        self._disp_by_step = disp_by_step
        self.solution_states = [
            _StubSolutionState(sid) for sid in sorted(disp_by_step)
        ]

    def get_field(self, name, step_id):  # type: ignore[no-untyped-def]
        if step_id not in self._disp_by_step:
            return None  # mimics adapter behaviour for unknown step
        return _StubFieldData(self._disp_by_step[step_id])


def _disp_arr(rows: list[list[float]]) -> np.ndarray:
    return np.asarray(rows, dtype=np.float64)


def test_displacement_history_basic() -> None:
    rdr = _StubDispReader(
        n_nodes=3,
        disp_by_step={
            1: _disp_arr([[0, 0, 0], [0, 0, 0], [0, 0, 0]]),
            2: _disp_arr([[1, 0, 0], [0, 2, 0], [0, 0, 3]]),
        },
    )
    h = displacement_history(rdr, [1, 2])
    assert h[1] == pytest.approx(0.0)
    assert h[2] == pytest.approx(3.0)


def test_displacement_history_unknown_step_raises_keyerror() -> None:
    """Codex R1: displacement_history must NOT silently fabricate 0.0
    for an unknown step — that flattens W7c/W7f plots without warning.
    """
    rdr = _StubDispReader(
        n_nodes=3, disp_by_step={1: _disp_arr([[1, 0, 0]])}
    )
    with pytest.raises(KeyError, match="999"):
        displacement_history(rdr, [1, 999])


def test_displacement_history_node_subset_basic() -> None:
    rdr = _StubDispReader(
        n_nodes=4,
        disp_by_step={
            1: _disp_arr([[10, 0, 0], [0, 0, 0], [0, 5, 0], [0, 0, 0]])
        },
    )
    # Restrict to indices [1, 3] — both zero rows. Max should be 0.
    h = displacement_history(
        rdr, [1], node_indices=np.array([1, 3], dtype=np.int64)
    )
    assert h[1] == pytest.approx(0.0)


def test_displacement_history_negative_index_rejected() -> None:
    """Codex R1: numpy advanced indexing wraps negative indices to the
    tail. node_indices is documented as 0-based array positions, so
    negative values are a usage bug — fail loudly."""
    rdr = _StubDispReader(
        n_nodes=3, disp_by_step={1: _disp_arr([[1, 0, 0]])}
    )
    with pytest.raises(ValueError, match="non-negative"):
        displacement_history(
            rdr, [1], node_indices=np.array([-1], dtype=np.int64)
        )


def test_displacement_history_out_of_bounds_index_rejected() -> None:
    rdr = _StubDispReader(
        n_nodes=3, disp_by_step={1: _disp_arr([[1, 0, 0]])}
    )
    with pytest.raises(ValueError, match="out of bounds"):
        displacement_history(
            rdr, [1], node_indices=np.array([5], dtype=np.int64)
        )


def test_displacement_history_2d_node_indices_rejected() -> None:
    rdr = _StubDispReader(
        n_nodes=3, disp_by_step={1: _disp_arr([[1, 0, 0]])}
    )
    with pytest.raises(ValueError, match="must be 1-D"):
        displacement_history(
            rdr, [1], node_indices=np.zeros((2, 2), dtype=np.int64)
        )


def test_displacement_history_non_integer_dtype_rejected() -> None:
    rdr = _StubDispReader(
        n_nodes=3, disp_by_step={1: _disp_arr([[1, 0, 0]])}
    )
    with pytest.raises(ValueError, match="integer dtype"):
        displacement_history(
            rdr, [1], node_indices=np.array([1.5], dtype=np.float64)
        )


def test_displacement_history_empty_subset_returns_zero() -> None:
    rdr = _StubDispReader(
        n_nodes=3, disp_by_step={1: _disp_arr([[1, 0, 0]])}
    )
    h = displacement_history(
        rdr, [1], node_indices=np.array([], dtype=np.int64)
    )
    assert h[1] == 0.0


# ---------------------------------------------------------------------------
# Tier 2 — integration against GS-100 (parser-required)
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
    """Open GS-100 smoke fixture; reused for the integration block."""
    if not _HAS_PARSER:
        pytest.skip("optional 'openradioss' extra not installed")
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    from app.adapters.openradioss import OpenRadiossReader
    from app.core.types import UnitSystem

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
def test_gs100_eroded_history_is_all_zero(gs100_reader) -> None:
    """GS-100 is a contact test — no erosion expected at any step.
    Pins the degenerate baseline so a future regression in the
    delEltA wiring shows up immediately."""
    step_ids = [s.step_id for s in gs100_reader.solution_states]
    history = eroded_history(gs100_reader, step_ids)
    assert all(v == 0 for v in history.values()), (
        f"GS-100 should report 0 eroded facets at every step; got {history}"
    )


@needs_parser
def test_gs100_perforation_event_step_is_none(gs100_reader) -> None:
    step_ids = [s.step_id for s in gs100_reader.solution_states]
    assert perforation_event_step(gs100_reader, step_ids) is None


@needs_parser
def test_gs100_displacement_history_monotonic(gs100_reader) -> None:
    """For BOULE1V5 (ball impact, no rebound during 0.5 ms window) the
    max nodal displacement magnitude should be monotonically
    non-decreasing across the 3 ship frames."""
    step_ids = [s.step_id for s in gs100_reader.solution_states]
    h = displacement_history(gs100_reader, step_ids)
    values = [h[sid] for sid in step_ids]
    # First state is the reference frame → 0 by construction.
    assert values[0] == pytest.approx(0.0, abs=1e-12)
    # Non-decreasing across the window.
    for prev, nxt in zip(values, values[1:]):
        assert nxt >= prev, f"max-disp regressed: {values}"
    # And actually moves at some point — otherwise the test passes
    # vacuously (e.g. if the reader returned None for every state).
    assert values[-1] > 0.0, f"final max-disp should be > 0; got {values}"


@needs_parser
def test_gs100_displacement_history_node_subset(gs100_reader) -> None:
    """``node_indices`` restricts the max to the supplied row indices.
    Sanity-check by comparing a 1-node subset to the global max ≥
    subset max."""
    step_ids = [s.step_id for s in gs100_reader.solution_states]
    n_nodes = gs100_reader.mesh.node_id_array.size
    # Pick one arbitrary node — index 0 — for the subset.
    subset = np.array([0], dtype=np.int64)
    global_h = displacement_history(gs100_reader, step_ids)
    subset_h = displacement_history(gs100_reader, step_ids, node_indices=subset)
    for sid in step_ids:
        assert subset_h[sid] <= global_h[sid] + 1e-9, (
            f"subset max should not exceed global max at step {sid}: "
            f"{subset_h[sid]} vs {global_h[sid]}"
        )
    assert n_nodes >= 1  # silence unused
