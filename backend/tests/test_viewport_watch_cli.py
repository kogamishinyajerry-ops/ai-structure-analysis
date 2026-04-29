"""Tests for the W8d ``viewport-watch-cli`` console_script.

The heavy lifting is in ``export_run_streaming`` (covered by
``test_vtu_exporter.py`` Bucket 6); this file pins the CLI shape:

  1. Argparse refusals — missing required flags, bad types, empty values.
  2. End-to-end smoke: streams an already-baked GS-101 dir to a manifest
     and asserts exit 0 + manifest contents.
"""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import pytest

from app.viz.viewport_watch_cli import main


_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_GS101_DECK_DIR: Path = (
    _REPO_ROOT / "golden_samples" / "GS-101-demo-unsigned" / "data"
)


# ---------------------------------------------------------------------------
# Bucket 1 — argparse refusals
# ---------------------------------------------------------------------------


def test_no_args_prints_usage_and_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main([])
    assert rc == 2
    assert "usage:" in capsys.readouterr().err


def test_missing_root_refused(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    rc = main(
        ["--rootname", "model_00", "--output", str(tmp_path / "o")]  # type: ignore[attr-defined]
    )
    assert rc == 2
    assert "usage:" in capsys.readouterr().err


def test_missing_rootname_refused(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    rc = main(
        ["--root", str(tmp_path), "--output", str(tmp_path / "o")]  # type: ignore[attr-defined]
    )
    assert rc == 2
    assert "usage:" in capsys.readouterr().err


def test_missing_output_refused(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    rc = main(["--root", str(tmp_path), "--rootname", "model_00"])  # type: ignore[attr-defined]
    assert rc == 2
    assert "usage:" in capsys.readouterr().err


def test_empty_rootname_refused(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    rc = main(
        [
            "--root", str(tmp_path),  # type: ignore[attr-defined]
            "--rootname", "",
            "--output", str(tmp_path / "o"),  # type: ignore[attr-defined]
        ]
    )
    assert rc == 2
    assert "must be non-empty" in capsys.readouterr().err


def test_max_idle_must_be_number(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    rc = main(
        [
            "--root", str(tmp_path),  # type: ignore[attr-defined]
            "--rootname", "model_00",
            "--output", str(tmp_path / "o"),  # type: ignore[attr-defined]
            "--max-idle-s", "not-a-number",
        ]
    )
    assert rc == 2
    assert "must be a number" in capsys.readouterr().err


def test_unknown_argument_refused(
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    rc = main(
        [
            "--root", str(tmp_path),  # type: ignore[attr-defined]
            "--rootname", "model_00",
            "--output", str(tmp_path / "o"),  # type: ignore[attr-defined]
            "--bogus", "x",
        ]
    )
    assert rc == 2
    assert "unknown argument" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Bucket 2 — end-to-end smoke
# ---------------------------------------------------------------------------


@pytest.fixture
def gs101_baked(tmp_path: pytest.TempPathFactory) -> Path:
    """Bake GS-101 to gzipped frames for streaming tests.

    Reuses the same docker / openradioss / GS-101 deck guards as
    test_vtu_exporter::gs101_baked.
    """
    pytest.importorskip("pyvista")
    pytest.importorskip("vortex_radioss")
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
        "docker", "run", "--rm",
        "-v", f"{bake_dir}:/work",
        "openradioss:arm64",
        "bash", "-c",
        "cd /work && starter_linuxa64 -i model_00_0000.rad -np 1 "
        "&& engine_linuxa64 -i model_00_0001.rad",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        pytest.skip(
            f"openradioss bake failed (rc={result.returncode}): "
            f"{result.stderr.decode(errors='replace')[:200]}"
        )
    for frame in sorted(bake_dir.glob("model_00A0[0-9][0-9]")):
        with open(frame, "rb") as src, gzip.open(
            str(frame) + ".gz", "wb"
        ) as dst:
            shutil.copyfileobj(src, dst)
        frame.unlink()
    if not list(bake_dir.glob("model_00A*.gz")):
        pytest.skip("openradioss bake produced no animation frames")
    return bake_dir


def test_end_to_end_streams_gs101(
    gs101_baked: Path,
    capsys: pytest.CaptureFixture[str],
    tmp_path: pytest.TempPathFactory,
) -> None:
    """W8d — running viewport-watch-cli against a pre-baked GS-101 dir
    produces a complete manifest and exits 0.

    The CLI uses a real ``time.sleep`` loop, so we minimise wall clock
    by setting ``--max-idle-s 2`` and ``--poll-interval-s 0.5``. The
    bake dir is fully populated up front so the loop processes all 11
    frames in the first poll iteration, then idles out within 2s.
    """
    out_dir = tmp_path / "viewport"  # type: ignore[attr-defined]
    rc = main(
        [
            "--root", str(gs101_baked),
            "--rootname", "model_00",
            "--output", str(out_dir),
            "--max-idle-s", "2",
            "--poll-interval-s", "0.5",
            "--timeout-s", "60",
        ]
    )
    assert rc == 0, capsys.readouterr().err
    manifest_path = out_dir / "viewport_manifest.json"
    assert manifest_path.is_file()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["n_states"] == 11
