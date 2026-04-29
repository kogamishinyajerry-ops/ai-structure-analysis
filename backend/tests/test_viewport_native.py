"""Tests for the W8b PyVista native viewport entrypoint.

Covers:

1. Manifest contract refusals: missing file, bad JSON, schema mismatch,
   empty states list, missing per-state vtu file.
2. CLI shape: usage on no args, ``--snapshots`` requires a value,
   ``--field`` requires a value.
3. Snapshot rendering against the GS-101 demo: emits one PNG per
   state into the requested directory; total size is non-trivial
   (sanity).
4. ``main()`` exit codes match the CLI contract: 2 on argparse
   errors, 3 on ViewportError, 0 on snapshot success.

The interactive ``open_viewport`` path itself is NOT tested here —
opening a real GUI window in CI is fragile / blocked. ``open_viewport``
shares its load path with ``render_snapshots`` so the manifest /
state-loading branches are exercised by Bucket 1.
"""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import pytest

from app.viz.vtu_exporter import SCHEMA_VERSION, export_run
from app.viz.viewport_native import ViewportError, main, render_snapshots


_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_GS101_DECK_DIR: Path = (
    _REPO_ROOT / "golden_samples" / "GS-101-demo-unsigned" / "data"
)


@pytest.fixture
def gs101_viewport_manifest(tmp_path: pytest.TempPathFactory) -> Path:
    """Bake GS-101 + run the W8a exporter; return the manifest path.
    Skips when docker / openradioss image / GS-101 deck are unavailable.
    """
    pytest.importorskip("pyvista")
    import subprocess

    if shutil.which("docker") is None:
        pytest.skip("docker not on PATH")
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
        "docker", "run", "--rm", "-v", f"{bake_dir}:/work",
        "openradioss:arm64", "bash", "-c",
        "cd /work && starter_linuxa64 -i model_00_0000.rad -np 1 "
        "&& engine_linuxa64 -i model_00_0001.rad",
    ]
    if subprocess.run(cmd, capture_output=True, timeout=120).returncode != 0:
        pytest.skip("openradioss bake failed in fixture")

    for frame in sorted(bake_dir.glob("model_00A0[0-9][0-9]")):
        with open(frame, "rb") as src, gzip.open(str(frame) + ".gz", "wb") as dst:
            shutil.copyfileobj(src, dst)
        frame.unlink()

    viewport_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    return export_run(
        openradioss_root=bake_dir,
        rootname="model_00",
        output_dir=viewport_dir,
    )


# ---------------------------------------------------------------------------
# Bucket 1 — manifest contract refusals
# ---------------------------------------------------------------------------


def test_missing_manifest_raises(tmp_path: pytest.TempPathFactory) -> None:
    pytest.importorskip("pyvista")
    out = tmp_path / "out"  # type: ignore[attr-defined]
    with pytest.raises(ViewportError, match="manifest not found"):
        render_snapshots(
            tmp_path / "nope.json",  # type: ignore[attr-defined]
            out,
        )


def test_bad_json_manifest_raises(tmp_path: pytest.TempPathFactory) -> None:
    pytest.importorskip("pyvista")
    bad = tmp_path / "bad.json"  # type: ignore[attr-defined]
    bad.write_text("{this is not json")
    with pytest.raises(ViewportError, match="not valid JSON"):
        render_snapshots(bad, tmp_path / "out")  # type: ignore[attr-defined]


def test_wrong_schema_version_raises(tmp_path: pytest.TempPathFactory) -> None:
    pytest.importorskip("pyvista")
    m = tmp_path / "m.json"  # type: ignore[attr-defined]
    m.write_text(json.dumps({"schema_version": "999", "states": []}))
    with pytest.raises(ViewportError, match="schema version"):
        render_snapshots(m, tmp_path / "out")  # type: ignore[attr-defined]


def test_empty_states_list_refused(tmp_path: pytest.TempPathFactory) -> None:
    """Codex R1 PR #112 MEDIUM — schema-valid empty states must refuse,
    not return success with zero PNGs."""
    pytest.importorskip("pyvista")
    m = tmp_path / "m.json"  # type: ignore[attr-defined]
    m.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "states": []}))
    with pytest.raises(ViewportError, match="no states"):
        render_snapshots(m, tmp_path / "out")  # type: ignore[attr-defined]


def test_unknown_field_refused(tmp_path: pytest.TempPathFactory) -> None:
    """Codex R1 PR #112 MEDIUM — unknown ``field`` must refuse rather
    than silently render gray geometry."""
    pytest.importorskip("pyvista")
    m = tmp_path / "m.json"  # type: ignore[attr-defined]
    m.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "states": [
                    {"step_id": 0, "vtu_relpath": "x.vtu", "time_ms": 0.0,
                     "max_displacement_mm": 0.0,
                     "n_solids_alive": 0, "n_solids_total": 0,
                     "n_facets_alive": 0, "n_facets_total": 0}
                ],
            }
        )
    )
    with pytest.raises(ViewportError, match="unknown field"):
        render_snapshots(
            m, tmp_path / "out", field="not_a_real_field"  # type: ignore[attr-defined]
        )


def test_corrupt_vtu_refused(tmp_path: pytest.TempPathFactory) -> None:
    """Codex R1 PR #112 MEDIUM — corrupt VTU bytes must surface as
    ViewportError, not raw pyvista IOError."""
    pytest.importorskip("pyvista")
    base = tmp_path  # type: ignore[attr-defined]
    (base / "broken.vtu").write_bytes(b"this is not VTU XML")
    m = base / "m.json"
    m.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "states": [
                    {
                        "step_id": 0,
                        "vtu_relpath": "broken.vtu",
                        "time_ms": 0.0,
                        "max_displacement_mm": 0.0,
                        "n_solids_alive": 0,
                        "n_solids_total": 0,
                        "n_facets_alive": 0,
                        "n_facets_total": 0,
                    }
                ],
            }
        )
    )
    with pytest.raises(ViewportError, match="failed to read"):
        render_snapshots(m, base / "out")


# ---------------------------------------------------------------------------
# Bucket 2 — CLI shape
# ---------------------------------------------------------------------------


def test_no_args_prints_usage_and_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main([])
    assert rc == 2
    err = capsys.readouterr().err
    assert "usage" in err.lower()


def test_snapshots_requires_value(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    m = tmp_path / "m.json"  # type: ignore[attr-defined]
    m.write_text("{}")
    rc = main([str(m), "--snapshots"])
    assert rc == 2
    assert "--snapshots requires" in capsys.readouterr().err


def test_field_requires_value(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    m = tmp_path / "m.json"  # type: ignore[attr-defined]
    m.write_text("{}")
    rc = main([str(m), "--field"])
    assert rc == 2
    assert "--field requires" in capsys.readouterr().err


def test_main_returns_three_on_viewport_error(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    """``main`` translates ViewportError → exit 3 (matches the CLI's
    domain-refusal class, parallels report-cli's exit codes)."""
    rc = main([str(tmp_path / "nope.json"), "--snapshots", str(tmp_path / "out")])  # type: ignore[attr-defined]
    assert rc == 3


# ---------------------------------------------------------------------------
# Bucket 3 — snapshot rendering on GS-101
# ---------------------------------------------------------------------------


def test_snapshots_emit_one_png_per_state(
    gs101_viewport_manifest: Path,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Confirms the snapshot path produces a PNG per manifest state and
    each file is plausibly an image (PNG signature header)."""
    snap_dir = tmp_path / "snaps"  # type: ignore[attr-defined]
    rc = main(
        [
            str(gs101_viewport_manifest),
            "--snapshots",
            str(snap_dir),
            "--field",
            "displacement_magnitude",
        ]
    )
    assert rc == 0

    payload = json.loads(gs101_viewport_manifest.read_text(encoding="utf-8"))
    written = sorted(snap_dir.glob("state_*.png"))
    assert len(written) == payload["n_states"]
    for png in written:
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", (
            f"{png} is not a valid PNG"
        )
        # Each frame should be at least a few KB; a corrupt off-screen
        # render typically produces a mostly-empty PNG.
        assert png.stat().st_size > 5000, (
            f"{png} is suspiciously small: {png.stat().st_size} bytes"
        )


def test_snapshots_default_field_when_not_specified(
    gs101_viewport_manifest: Path,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """The default field is ``displacement_magnitude`` — confirm
    omitting --field still works against the GS-101 manifest."""
    snap_dir = tmp_path / "snaps"  # type: ignore[attr-defined]
    rc = main([str(gs101_viewport_manifest), "--snapshots", str(snap_dir)])
    assert rc == 0
    written = list(snap_dir.glob("state_*.png"))
    assert len(written) > 0
