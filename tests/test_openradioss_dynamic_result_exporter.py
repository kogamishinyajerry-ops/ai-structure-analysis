from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.viz.openradioss_dynamic_result_exporter import (  # noqa: E402
    DynamicFrameData,
    export_dynamic_result_mesh_from_frames,
)

SCRIPT_PATH = REPO_ROOT / "scripts" / "gs102_export_text_to_cae_result_mesh.py"


def _two_hex_frames() -> list[DynamicFrameData]:
    base_coords = np.asarray(
        [
            # projectile hex, part 1
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
            # plate hex, part 2
            [3.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
            [4.0, 1.0, 0.0],
            [3.0, 1.0, 0.0],
            [3.0, 0.0, 0.4],
            [4.0, 0.0, 0.4],
            [4.0, 1.0, 0.4],
            [3.0, 1.0, 0.4],
        ],
        dtype=float,
    )
    connect = np.asarray(
        [
            [0, 1, 2, 3, 4, 5, 6, 7],
            [8, 9, 10, 11, 12, 13, 14, 15],
        ],
        dtype=int,
    )
    stress_a = np.asarray(
        [
            [2.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [10.0, -2.0, 1.0, 1.0, 0.5, 0.25],
        ],
        dtype=float,
    )
    stress_b = np.asarray(
        [
            [4.0, 2.0, 0.0, 0.0, 0.0, 0.0],
            [25.0, -6.0, 2.0, 2.0, 1.0, 0.5],
        ],
        dtype=float,
    )
    shifted = base_coords.copy()
    shifted[:8, 0] += 0.75
    return [
        DynamicFrameData(
            source="model_00A001",
            timestep=0.0,
            coords=base_coords,
            element_node_indexes=connect,
            element_ids=np.asarray([101, 201], dtype=int),
            part_ids=np.asarray([1, 2], dtype=int),
            alive=np.asarray([True, True], dtype=bool),
            stress=stress_a,
            plastic_strain=np.asarray([0.01, 0.08], dtype=float),
        ),
        DynamicFrameData(
            source="model_00A002",
            timestep=0.04,
            coords=shifted,
            element_node_indexes=connect,
            element_ids=np.asarray([101, 201], dtype=int),
            part_ids=np.asarray([1, 2], dtype=int),
            alive=np.asarray([True, False], dtype=bool),
            stress=stress_b,
            plastic_strain=np.asarray([0.03, 0.22], dtype=float),
        ),
    ]


def test_result_mesh_json_contains_model_tree_full_parts_and_dynamic_frames(
    tmp_path: Path,
) -> None:
    result = export_dynamic_result_mesh_from_frames(
        _two_hex_frames(),
        output_dir=tmp_path,
        case_id="CASE-TEXT-TO-CAE",
        field="von_mises",
        source_root="project_state/runs/CASE-TEXT-TO-CAE/data",
    )

    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))

    assert payload["schemaVersion"] == 1
    assert payload["analysisType"] == "dynamic"
    assert payload["claimTier"] == "Tier 1 engineering candidate"
    assert payload["source"]["solver"] == "OpenRadioss"
    assert payload["fieldLabel"] == "von Mises stress"
    assert len(payload["dynamicFrames"]) == 2
    assert payload["nodes"] == payload["dynamicFrames"][0]["nodes"]
    assert payload["elements"] == payload["dynamicFrames"][0]["elements"]

    tree_children = payload["modelTree"]["children"]
    assert [child["partRole"] for child in tree_children] == ["projectile", "plate"]
    assert [child["elementCount"] for child in tree_children] == [1, 1]

    frame0, frame1 = payload["dynamicFrames"]
    assert frame0["timeMs"] == 0.0
    assert frame1["timeMs"] == 0.04
    assert frame1["fieldRanges"]["maxDisplacement"] > 0.0

    projectile_faces = [
        element for element in frame1["elements"] if element["partRole"] == "projectile"
    ]
    plate_faces = [element for element in frame1["elements"] if element["partRole"] == "plate"]
    assert projectile_faces, "projectile must be exported from solver part geometry"
    assert plate_faces, "plate faces must be present for contour cloud playback"
    assert all(element["visualOnly"] is False for element in projectile_faces)
    assert any(element["alive"] is False for element in plate_faces)
    assert any(element["sourceElement"] == 201 for element in plate_faces)

    assert payload["fieldRanges"]["valueMax"] >= payload["fieldRanges"]["valueMin"] >= 0.0
    assert payload["artifacts"]["vtuManifest"]["status"] == "available"


def test_vtu_sidecars_are_written_for_each_dynamic_frame(tmp_path: Path) -> None:
    result = export_dynamic_result_mesh_from_frames(
        _two_hex_frames(),
        output_dir=tmp_path,
        case_id="CASE-VTU",
        field="plastic_strain",
        write_vtu=True,
    )

    manifest = json.loads(result.vtu_manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "openradioss-dynamic-vtu-manifest.v1"
    assert manifest["case_id"] == "CASE-VTU"
    assert manifest["field"] == "plastic_strain"
    assert [frame["frame"] for frame in manifest["frames"]] == [0, 1]

    for frame in manifest["frames"]:
        vtu_path = tmp_path / frame["vtu_relpath"]
        body = vtu_path.read_text(encoding="utf-8")
        assert '<VTKFile type="UnstructuredGrid"' in body
        assert 'Name="part_id"' in body
        assert 'Name="alive"' in body
        assert 'Name="plastic_strain"' in body
        assert frame["n_cells"] == 2


def test_cli_rejects_golden_sample_output_path(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "gs102_export_text_to_cae_result_mesh",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    try:
        module._assert_safe_output_path(tmp_path / "golden_samples" / "bad", tmp_path)
    except ValueError as exc:
        assert "golden_samples" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected golden_samples output rejection")
