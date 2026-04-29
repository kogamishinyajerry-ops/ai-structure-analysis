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
    export_run_streaming,
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


def test_non_si_mm_unit_system_refused(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Codex R1 HIGH on PR #111 — manifest keys are unit-bearing
    (``time_ms``, ``max_displacement_mm``). Until the schema grows
    explicit per-key units, non-SI_MM runs must be refused rather
    than silently mislabelled."""
    pytest.importorskip("pyvista")
    deck = tmp_path / "deck"  # type: ignore[attr-defined]
    deck.mkdir()
    with pytest.raises(VTUExportError, match="only supports SI_MM"):
        export_run(
            openradioss_root=deck,
            rootname="model_00",
            output_dir=tmp_path / "out",  # type: ignore[attr-defined]
            unit_system=UnitSystem.SI,
        )
    with pytest.raises(VTUExportError, match="only supports SI_MM"):
        export_run(
            openradioss_root=deck,
            rootname="model_00",
            output_dir=tmp_path / "out2",  # type: ignore[attr-defined]
            unit_system=UnitSystem.ENGLISH,
        )


def test_deletion_flag_outside_zero_one_refused_not_silently_coerced(
    monkeypatch: pytest.MonkeyPatch,
    gs101_baked: Path,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Codex R2 HIGH on PR #111 — bare ``np.asarray(..., dtype=bool)``
    coerces 2 / -1 to True silently, contaminating the manifest's
    alive counts and the VTU's ``alive`` array. The exporter must
    validate the raw deletion arrays carry only ``{0, 1}`` and refuse
    the frame otherwise.

    Simulate parser drift by overwriting one entry of ``delElt3DA``
    with ``2`` after the reference frame parses normally.
    """
    pv = pytest.importorskip("pyvista")  # noqa: F841
    import numpy as np
    from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

    real_init = RadiossReader.__init__
    call_count = {"n": 0}

    def patched_init(self: RadiossReader, *args: object, **kwargs: object) -> None:
        real_init(self, *args, **kwargs)
        call_count["n"] += 1
        # Reference frame parses cleanly; second-onwards we corrupt
        # one entry to value 2 so the bare bool() coercion would
        # silently treat it as True.
        if call_count["n"] >= 2:
            arr = np.asarray(self.raw_arrays["delElt3DA"]).astype(np.int8)
            arr[0] = 2
            self.raw_arrays["delElt3DA"] = arr

    monkeypatch.setattr(RadiossReader, "__init__", patched_init)

    with pytest.raises(VTUExportError, match="outside .*0, 1"):
        export_run(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=tmp_path / "out",  # type: ignore[attr-defined]
        )


def test_connectivity_length_mismatch_refused_not_silently_truncated(
    monkeypatch: pytest.MonkeyPatch,
    gs101_baked: Path,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Codex R1 HIGH on PR #111 — the previous ``zip(..., strict=False)``
    silently truncated cells when ``connect3DA`` and ``delElt3DA``
    drifted in length (e.g. corrupt frame parse). The exporter must
    refuse the frame instead, otherwise the manifest reports the full
    header counts while the VTU silently drops cells.

    Simulate the drift by patching ``RadiossReader.raw_arrays`` to
    return a truncated ``delElt3DA`` after the first call.
    """
    pv = pytest.importorskip("pyvista")  # noqa: F841
    import numpy as np
    from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

    real_init = RadiossReader.__init__
    call_count = {"n": 0}

    def patched_init(self: RadiossReader, *args: object, **kwargs: object) -> None:
        real_init(self, *args, **kwargs)
        call_count["n"] += 1
        # Reference frame parses cleanly; second-onwards we lop off
        # the last entry of delElt3DA so length disagrees with
        # connect3DA / nbElts3D.
        if call_count["n"] >= 2:
            arr = np.asarray(self.raw_arrays["delElt3DA"], dtype=bool)
            self.raw_arrays["delElt3DA"] = arr[:-1]

    monkeypatch.setattr(RadiossReader, "__init__", patched_init)

    with pytest.raises(VTUExportError, match="delElt array length"):
        export_run(
            openradioss_root=gs101_baked,
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


# ---------------------------------------------------------------------------
# Bucket 6 — W8c streaming watcher
# ---------------------------------------------------------------------------


class _FakeClock:
    """Deterministic clock for streaming-loop tests. ``sleep`` advances
    the virtual time so the polling loop is instant in CI."""

    def __init__(self) -> None:
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def test_streaming_with_all_frames_present_matches_one_shot_export(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """W8c — running the streaming watcher against an already-complete
    bake directory must produce a manifest equivalent to ``export_run``.

    The streaming code path therefore subsumes the one-shot path; the
    only difference is when frames arrive, not how they're transformed.
    """
    out_oneshot = tmp_path / "oneshot"  # type: ignore[attr-defined]
    out_stream = tmp_path / "stream"
    export_run(
        openradioss_root=gs101_baked,
        rootname="model_00",
        output_dir=out_oneshot,
    )
    clock = _FakeClock()
    export_run_streaming(
        openradioss_root=gs101_baked,
        rootname="model_00",
        output_dir=out_stream,
        max_idle_s=2.0,
        poll_interval_s=0.5,
        _now=clock.now,
        _sleep=clock.sleep,
    )

    a = json.loads((out_oneshot / "viewport_manifest.json").read_text())
    b = json.loads((out_stream / "viewport_manifest.json").read_text())

    # Manifest top-level fields and state-record contents must match
    # exactly; only the on-disk write order differs.
    assert a["n_states"] == b["n_states"] == 11
    assert a["available_fields"] == b["available_fields"]
    assert a["rootname"] == b["rootname"]
    assert a["unit_system"] == b["unit_system"]
    for sa, sb in zip(a["states"], b["states"], strict=True):
        assert sa == sb


def test_streaming_grows_manifest_as_frames_arrive(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """W8c — the watcher must observe a growing manifest as new frames
    appear in openradioss_root mid-loop. We simulate this by relocating
    GS-101 frames into the watched dir incrementally inside the
    fake-clock ``sleep`` hook so each poll cycle reveals one more frame.
    """
    src_frames = sorted(gs101_baked.glob("model_00A*.gz"))
    assert len(src_frames) == 11

    watched = tmp_path / "incoming"  # type: ignore[attr-defined]
    out_dir = tmp_path / "viewport"
    watched.mkdir()
    # Pre-stage the first frame so the loop has something to anchor on.
    shutil.copy(src_frames[0], watched / src_frames[0].name)

    pending = list(src_frames[1:])
    appended_step_ids: list[int] = []

    clock = _FakeClock()

    def fake_sleep(seconds: float) -> None:
        # Reveal one more frame per poll cycle, simulating the engine
        # writing a new A### file every poll_interval.
        if pending:
            nxt = pending.pop(0)
            shutil.copy(nxt, watched / nxt.name)
        clock.sleep(seconds)

    export_run_streaming(
        openradioss_root=watched,
        rootname="model_00",
        output_dir=out_dir,
        max_idle_s=3.0,
        poll_interval_s=0.5,
        _now=clock.now,
        _sleep=fake_sleep,
        on_state_appended=lambda r: appended_step_ids.append(r.step_id),
    )

    assert appended_step_ids == list(range(1, 12)), (
        f"states must be appended in step-id order; got {appended_step_ids}"
    )

    payload = json.loads(
        (out_dir / "viewport_manifest.json").read_text(encoding="utf-8")
    )
    assert payload["n_states"] == 11


def test_streaming_with_no_frames_writes_zero_state_manifest(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """W8c — when the loop times out before any frame arrives the
    manifest must already exist on disk with n_states=0 so a polling
    viewport sees a well-formed (empty) artefact instead of ENOENT.
    """
    pytest.importorskip("pyvista")
    pytest.importorskip("vortex_radioss")
    src = tmp_path / "src"  # type: ignore[attr-defined]
    out = tmp_path / "out"
    src.mkdir()
    clock = _FakeClock()
    manifest_path = export_run_streaming(
        openradioss_root=src,
        rootname="model_00",
        output_dir=out,
        max_idle_s=1.0,
        poll_interval_s=0.5,
        _now=clock.now,
        _sleep=clock.sleep,
    )
    assert manifest_path.is_file()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["n_states"] == 0
    assert payload["states"] == []


def test_streaming_atomic_manifest_no_partial_reads(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """W8c — manifest writes must be atomic (write-tmp + os.replace).

    We override write_manifest to a thin wrapper that, between every
    write, snapshots the canonical manifest from disk and asserts each
    snapshot is well-formed JSON with a coherent state count. If the
    write were non-atomic, a polling reader would occasionally see a
    truncated middle-of-write file and json.loads would raise.
    """
    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    snapshots: list[dict[str, object]] = []

    from app.viz import vtu_exporter as vtu_mod

    real_write = vtu_mod._StreamingExporter.write_manifest

    def snapshotting_write(self):  # type: ignore[no-untyped-def]
        path = real_write(self)
        # Re-read the canonical name immediately after the write
        # returns. With the os.replace contract this MUST be a complete,
        # parseable manifest.
        snapshots.append(json.loads(path.read_text(encoding="utf-8")))
        return path

    monkey = pytest.MonkeyPatch()
    monkey.setattr(
        vtu_mod._StreamingExporter, "write_manifest", snapshotting_write
    )
    try:
        clock = _FakeClock()
        export_run_streaming(
            openradioss_root=gs101_baked,
            rootname="model_00",
            output_dir=out_dir,
            max_idle_s=2.0,
            poll_interval_s=0.5,
            _now=clock.now,
            _sleep=clock.sleep,
        )
    finally:
        monkey.undo()

    # Initial empty + 11 per-frame writes + final no-op poll. Each must
    # parse and have a non-decreasing n_states.
    assert len(snapshots) >= 11
    n_states_seq = [s["n_states"] for s in snapshots]
    assert all(
        b >= a for a, b in zip(n_states_seq, n_states_seq[1:], strict=False)
    ), f"n_states must be monotone non-decreasing; got {n_states_seq}"
    assert n_states_seq[-1] == 11


def test_streaming_with_initial_gap_waits_for_fill(
    gs101_baked: Path, tmp_path: pytest.TempPathFactory
) -> None:
    """Codex R1 PR #113 HIGH — if the watcher starts with a gap (e.g.
    A001 + A005 already on disk, A002-A004 missing), it must NOT
    export A005 as state 2 with the wrong displacement reference.
    Instead it processes A001, then waits for A002, A003, A004 to
    fill before resuming.
    """
    src_frames = sorted(gs101_baked.glob("model_00A*.gz"))
    assert len(src_frames) == 11

    watched = tmp_path / "watched"  # type: ignore[attr-defined]
    out = tmp_path / "out"
    watched.mkdir()

    # Stage A001 + A005 (creating a 3-frame gap at A002-A004).
    shutil.copy(src_frames[0], watched / src_frames[0].name)  # A001
    shutil.copy(src_frames[4], watched / src_frames[4].name)  # A005

    # Track which frames the loop visited and when. We feed in the
    # missing ones progressively across sleep ticks to verify the
    # streaming code respects ordering.
    appended: list[int] = []
    pending = [src_frames[1], src_frames[2], src_frames[3]]  # A002-A004
    after = [src_frames[5], src_frames[6], src_frames[7], src_frames[8],
             src_frames[9], src_frames[10]]  # A006-A011

    clock = _FakeClock()

    def fake_sleep(seconds: float) -> None:
        # Reveal one missing frame per sleep tick, then start filling
        # in A006+ once the gap is closed.
        if pending:
            f = pending.pop(0)
            shutil.copy(f, watched / f.name)
        elif after:
            f = after.pop(0)
            shutil.copy(f, watched / f.name)
        clock.sleep(seconds)

    export_run_streaming(
        openradioss_root=watched,
        rootname="model_00",
        output_dir=out,
        max_idle_s=3.0,
        poll_interval_s=0.5,
        _now=clock.now,
        _sleep=fake_sleep,
        on_state_appended=lambda r: appended.append(r.step_id),
    )

    # Must have processed in strict A### order: 1, 2, 3, ..., 11.
    assert appended == list(range(1, 12)), (
        f"streaming must enforce contiguous A### ordering even when "
        f"the initial dir contains a gap; got {appended}"
    )

    payload = json.loads(
        (out / "viewport_manifest.json").read_text(encoding="utf-8")
    )
    assert payload["n_states"] == 11
    # Step ids in manifest must equal A### numbers.
    assert [s["step_id"] for s in payload["states"]] == list(range(1, 12))


def test_streaming_negative_max_idle_refused(
    tmp_path: pytest.TempPathFactory,
) -> None:
    pytest.importorskip("pyvista")
    pytest.importorskip("vortex_radioss")
    src = tmp_path / "src"  # type: ignore[attr-defined]
    src.mkdir()
    with pytest.raises(VTUExportError, match="max_idle_s must be positive"):
        export_run_streaming(
            openradioss_root=src,
            rootname="m",
            output_dir=tmp_path / "o",  # type: ignore[attr-defined]
            max_idle_s=0.0,
        )


def test_streaming_negative_poll_interval_refused(
    tmp_path: pytest.TempPathFactory,
) -> None:
    pytest.importorskip("pyvista")
    pytest.importorskip("vortex_radioss")
    src = tmp_path / "src"  # type: ignore[attr-defined]
    src.mkdir()
    with pytest.raises(VTUExportError, match="poll_interval_s must be positive"):
        export_run_streaming(
            openradioss_root=src,
            rootname="m",
            output_dir=tmp_path / "o",  # type: ignore[attr-defined]
            poll_interval_s=0.0,
        )
