import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gs102_render_cloud_animation.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gs102_render_cloud_animation", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _frame(module):
    return module.FrameData(
        source="model_00A001",
        timestep=0.0,
        coords=np.zeros((4, 3), dtype=float),
        node_indexes=np.asarray([[0, 1, 2, 3], [0, 1, 2, 3]], dtype=int),
        element_ids=np.asarray([1, 9], dtype=int),
        part_ids=np.asarray([1, 2], dtype=int),
        alive=np.asarray([True, True], dtype=bool),
        stress=np.asarray(
            [
                [9.0, 6.0, 3.0, 0.0, 0.0, 0.0],
                [-1.0, -2.0, -3.0, 0.5, 0.0, 0.0],
            ],
            dtype=float,
        ),
        plastic_strain=np.asarray([0.1, 0.2], dtype=float),
    )


def test_pressure_proxy_uses_absolute_hydrostatic_stress() -> None:
    module = _load_module()
    values = module.element_field_values(_frame(module), "pressure_proxy")

    assert values.tolist() == [6.0, 2.0]


def test_pressure_delta_subtracts_alive_plate_frame_baseline() -> None:
    module = _load_module()
    values = module.element_field_values(_frame(module), "pressure_delta")

    assert values.tolist() == [4.0, 0.0]


def test_masks_use_part_ids_and_limits_ignore_projectile() -> None:
    module = _load_module()
    frame = _frame(module)

    assert module._projectile_mask(frame).tolist() == [True, False]
    assert module._plate_mask(frame).tolist() == [False, True]
    assert module.global_field_limits([frame], "pressure_proxy") == (0.0, 2.0)


def test_cloud_renderer_rejects_golden_sample_output(tmp_path: Path) -> None:
    module = _load_module()

    try:
        module._assert_safe_output_path(tmp_path / "golden_samples" / "bad", tmp_path)
    except ValueError as exc:
        assert "golden_samples" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected golden_samples output rejection")
