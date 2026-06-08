from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.openradioss_animation import (  # noqa: E402
    OpenRadiossAnimationInput,
    write_openradioss_animation,
)


def test_write_openradioss_animation_accepts_array_timestep(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class FakeRadiossReader:
        def __init__(self, path: str) -> None:
            self.arrays = {
                "timesteps": np.asarray([0.0123], dtype=float),
                "node_coordinates": np.asarray(
                    [
                        [0.0, 0.0, 0.0],
                        [1.0, 0.0, 0.0],
                        [1.0, 1.0, 0.0],
                        [0.0, 1.0, 0.0],
                    ],
                    dtype=float,
                ),
                "element_shell_node_indexes": np.asarray([[0, 1, 2, 3]], dtype=int),
                "element_shell_is_alive": np.asarray([True], dtype=bool),
            }

    radioss_reader_module = types.ModuleType("vortex_radioss.animtod3plot.RadiossReader")
    radioss_reader_module.RadiossReader = FakeRadiossReader
    monkeypatch.setitem(sys.modules, "vortex_radioss", types.ModuleType("vortex_radioss"))
    monkeypatch.setitem(
        sys.modules,
        "vortex_radioss.animtod3plot",
        types.ModuleType("vortex_radioss.animtod3plot"),
    )
    monkeypatch.setitem(
        sys.modules,
        "vortex_radioss.animtod3plot.RadiossReader",
        radioss_reader_module,
    )

    frame = tmp_path / "model_00A001"
    frame.write_bytes(b"fake")
    manifest_path = write_openradioss_animation(
        OpenRadiossAnimationInput(
            case_id="CASE-ARRAY-TIME",
            anim_files=(frame,),
            deck_source="project_state/runs/CASE-ARRAY-TIME/data/model_00_0000.rad",
        ),
        tmp_path / "out",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["per_frame"][0]["timestep"] == 0.0123
    assert (manifest_path.parent / "openradioss_animation.gif").exists()
