"""Tests for the OpenRadioss → VTU exporter (W8a Layer-4-viz path).

Bucket layout (mirrors W6e wiring tests):

1. Manifest contract: schema_version, rootname, n_states, fields list,
   per-state record shape.
2. VTU file contract: file exists, valid VTU XML, point + cell counts
   match the manifest record.
3. Field correctness: displacement at t=0 is zero everywhere (anchor
   frame), grows monotonically, vmises_solid is finite for solids and
   NaN for facets, alive/cell_kind arrays span all cells.
4. Three-state contracts: missing root dir → VTUExportError;
   non-existent rootname → VTUExportError; ambiguous .gz/plain frame
   collision → VTUExportError; gzipped vs plain inputs both work.
5. End-to-end on GS-101: 11 states, displacement range matches the
   documented physics (peak 125 mm, 30 bricks eroded).
"""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import pytest

from app.core.types import UnitSystem
from app.viz.vtu_exporter import (
    SCHEMA_VERSION,
    VTUExportError,
    export_run,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_GS101_DECK_DIR: Path = (
    _REPO_ROOT / "golden_samples" / "GS-101-demo-unsigned" / "data"
)


@pytest.fixture
def gs101_baked(tmp_path: pytest.TempPathFactory) -> Path:
    """Bake the GS-101 demo deck via the docker openradioss image and
    return the directory holding the gzipped frames.

    Skips when docker is unavailable or the openradioss image is not
    present locally — the bake is the smoke-test prerequisite, not the
    unit under test, so the test must degrade gracefully on a fresh
    contributor checkout.
    """
    pytest.importorskip("pyvista", reason="pyvista required for VTU export")
    import subprocess

    if shutil.which("docker") is None:
        pytest.skip("docker not on PATH")

    # Probe for openradioss:arm64 image.
    probe = subprocess.run(
        ["docker", "image", "inspect", "openradioss:arm64"],
        capture_output=True,
    )
    if probe.returncode != 0:
        pytest.skip("openradioss:arm64 docker image not built locally")

    if not _GS101_DECK_DIR.is_dir():
        pytest.skip(f"GS-101 deck not found at {_GS101_DECK_DIR}")

    bake_dir = tmp_path / "bake"  # type: ignore[attr-defined]
    bake_dir.mkdir()
    for name in ("model_00_0000.rad", "model_00_0001.rad"):
        shutil.copy(_GS101_DECK_DIR / name, bake_dir / name)

    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{bake_dir}:/work",
        "openradioss:arm64",
        "bash",
        "-c",
        "cd /work && starter_linuxa64 -i model_00_0000.rad -np 1 "
        "&& engine_linuxa64 -i model_00_0001.rad",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        pytest.skip(
            f"openradioss bake failed (rc={result.returncode}): "
            f"{result.stderr.decode(errors='replace')[:200]}"
        )

    # Compress the animation frames so the exporter exercises its
    # gzip-decompress path.
    for frame in sorted(bake_dir.glob("model_00A0[0-9][0-9]")):
        with open(frame, "rb") as src, gzip.open(
            str(frame) + ".gz", "wb"
        ) as dst:
            shutil.copyfileobj(src, dst)
        frame.unlink()

    n_frames = len(list(bake_dir.glob("model_00A*.gz")))
    if n_frames == 0:
        pytest.skip("openradioss bake produced no animation frames")
    return bake_dir


# ---------------------------------------------------------------------------
# Bucket 1 — manifest contract
# ---------------------------------------------------------------------------


def test_manifest_top_level_schema(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    manifest_path = export_run(
        openradioss_root=gs101_baked,
        rootname="model_00",
        output_dir=out_dir,
    )

    assert manifest_path == out_dir / "viewport_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["rootname"] == "model_00"
    assert payload["unit_system"] == UnitSystem.SI_MM.value
    assert payload["n_states"] == len(payload["states"])
    assert payload["n_states"] >= 2  # at least t=0 and final state
    assert isinstance(payload["available_fields"], list)
    assert payload["available_fields"] == sorted(payload["available_fields"])


def test_manifest_state_record_shape(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )
    expected_keys = {
        "step_id",
        "time_ms",
        "vtu_relpath",
        "max_displacement_mm",
        "n_solids_alive",
        "n_solids_total",
        "n_facets_alive",
        "n_facets_total",
    }
    for state in payload["states"]:
        assert set(state.keys()) == expected_keys, (
            f"state record key mismatch: {set(state.keys()) ^ expected_keys}"
        )
        assert state["step_id"] >= 1
        assert state["time_ms"] >= 0.0
        assert state["max_displacement_mm"] >= 0.0
        assert 0 <= state["n_solids_alive"] <= state["n_solids_total"]
        assert 0 <= state["n_facets_alive"] <= state["n_facets_total"]


# ---------------------------------------------------------------------------
# Bucket 2 — VTU file contract
# ---------------------------------------------------------------------------


def test_every_state_has_vtu_file(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )

    for state in payload["states"]:
        vtu_path = out_dir / state["vtu_relpath"]
        assert vtu_path.is_file(), f"missing VTU at {vtu_path}"
        # VTU is XML — quick header check.
        head = vtu_path.read_bytes()[:200]
        assert b"<VTKFile" in head
        assert b'type="UnstructuredGrid"' in head


def test_vtu_files_are_loadable_by_pyvista(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """Round-trip: pyvista must read back what pyvista wrote."""
    pv = pytest.importorskip("pyvista")

    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )

    state0 = payload["states"][0]
    grid0 = pv.read(out_dir / state0["vtu_relpath"])
    expected_cells = (
        state0["n_solids_total"] + state0["n_facets_total"]
    )
    assert grid0.n_cells == expected_cells
    assert "displacement" in grid0.point_data
    assert "alive" in grid0.cell_data
    assert "cell_kind" in grid0.cell_data


# ---------------------------------------------------------------------------
# Bucket 3 — field correctness
# ---------------------------------------------------------------------------


def test_displacement_is_zero_at_anchor_frame(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """ADR-001: the first frame is the displacement reference, so
    every node's displacement vector at state 1 must be (0, 0, 0)."""
    pv = pytest.importorskip("pyvista")
    import numpy as np

    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )

    grid0 = pv.read(out_dir / payload["states"][0]["vtu_relpath"])
    disp = np.asarray(grid0.point_data["displacement"])
    assert disp.shape[1] == 3
    assert np.allclose(disp, 0.0), (
        f"anchor frame must have zero displacement; got max|d|="
        f"{np.linalg.norm(disp, axis=1).max()}"
    )


def test_displacement_grows_with_state(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """In the GS-101 demo the rigid driver pushes monotonically along
    +X, so peak |displacement| must be non-decreasing across states."""
    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )

    peaks = [s["max_displacement_mm"] for s in payload["states"]]
    assert peaks[0] == 0.0
    for prev, nxt in zip(peaks, peaks[1:]):
        assert nxt >= prev, (
            f"max displacement dropped from {prev} → {nxt}; physics says "
            f"this run is monotonic until the rigid body stops"
        )


def test_vmises_solid_field_handles_facet_cells_with_nan(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """vmises_solid is only defined on the brick cells; the facet
    cells (steel plate shells) must carry NaN so the vtk.js colormap
    can skip them rather than rendering a fake value."""
    pv = pytest.importorskip("pyvista")
    import numpy as np

    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )

    if "vmises_solid" not in payload["available_fields"]:
        pytest.skip("vmises_solid not in this run — solver did not emit Voigt-6")

    final = payload["states"][-1]
    grid = pv.read(out_dir / final["vtu_relpath"])
    vm = np.asarray(grid.cell_data["vmises_solid"])
    kind = np.asarray(grid.cell_data["cell_kind"])

    # cell_kind == 0 (solid) → vmises must be finite (>=0)
    solid_mask = kind == 0
    assert np.all(np.isfinite(vm[solid_mask]))
    assert np.all(vm[solid_mask] >= 0.0)

    # cell_kind == 1 (facet) → vmises must be NaN
    facet_mask = kind == 1
    assert facet_mask.sum() > 0
    assert np.all(np.isnan(vm[facet_mask]))


def test_alive_array_spans_all_cells_and_distinguishes_kinds(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    pv = pytest.importorskip("pyvista")
    import numpy as np

    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )
    final = payload["states"][-1]
    grid = pv.read(out_dir / final["vtu_relpath"])
    alive = np.asarray(grid.cell_data["alive"])
    kind = np.asarray(grid.cell_data["cell_kind"])

    assert alive.shape == (grid.n_cells,)
    assert set(np.unique(alive)).issubset({0, 1})
    assert set(np.unique(kind)).issubset({0, 1})

    # GS-101 documented behaviour: bricks erode (some 0s in solid
    # alive), facets do not (all 1s in facet alive).
    facet_alive = alive[kind == 1]
    assert int(facet_alive.sum()) == int(facet_alive.size), (
        "GS-101 plate facets are documented to stay intact in this run"
    )


# ---------------------------------------------------------------------------
# Bucket 4 — error contracts
# ---------------------------------------------------------------------------


def test_missing_root_dir_raises(tmp_path: pytest.TempPathFactory) -> None:
    pytest.importorskip("pyvista")
    with pytest.raises(VTUExportError, match="not a directory"):
        export_run(
            openradioss_root=Path("/nonexistent-vtu-export-test"),
            rootname="model_00",
            output_dir=tmp_path / "out",  # type: ignore[attr-defined]
        )


def test_no_frames_raises(tmp_path: pytest.TempPathFactory) -> None:
    pytest.importorskip("pyvista")
    empty = tmp_path / "empty"  # type: ignore[attr-defined]
    empty.mkdir()
    with pytest.raises(VTUExportError, match="no animation frames"):
        export_run(
            openradioss_root=empty,
            rootname="model_00",
            output_dir=tmp_path / "out",  # type: ignore[attr-defined]
        )


def test_ambiguous_frame_collision_raises(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """A stale ``A001`` next to a fresh ``A001.gz`` is ambiguous; the
    exporter must reject the run rather than silently picking one."""
    pytest.importorskip("pyvista")
    deck = tmp_path / "deck"  # type: ignore[attr-defined]
    deck.mkdir()
    (deck / "model_00A001").write_bytes(b"\0" * 16)
    (deck / "model_00A001.gz").write_bytes(b"\0" * 16)
    with pytest.raises(VTUExportError, match="ambiguous frame"):
        export_run(
            openradioss_root=deck,
            rootname="model_00",
            output_dir=tmp_path / "out",  # type: ignore[attr-defined]
        )


# ---------------------------------------------------------------------------
# Bucket 5 — physics smoke test (GS-101 documented behaviour)
# ---------------------------------------------------------------------------


def test_gs101_documented_physics_round_trips(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """The ``GS-101-demo-unsigned`` README documents:

      * 11 animation frames
      * peak displacement ≈ 125 mm
      * solid (aluminum impactor) erodes from 120 → ~90 elements
      * shell (steel plate) facets stay intact at 180/180

    Pin all four so a regression in either the deck, the OpenRadioss
    runtime, or this exporter shows up here.
    """
    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    payload = json.loads(
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
        ).read_text(encoding="utf-8")
    )

    assert payload["n_states"] == 11

    final = payload["states"][-1]
    # README: "peak displacement ≈ 125 mm"
    assert 100.0 < final["max_displacement_mm"] < 150.0, (
        f"peak displacement {final['max_displacement_mm']} mm outside "
        f"documented (100, 150) bracket"
    )
    # README: "30 bricks erode" → ~90/120 alive at final state
    assert 80 <= final["n_solids_alive"] <= 100, (
        f"final solid-alive count {final['n_solids_alive']} outside "
        f"documented (80, 100) bracket"
    )
    assert final["n_solids_total"] == 120
    # README: "no shell deletions"
    assert final["n_facets_alive"] == final["n_facets_total"] == 180
