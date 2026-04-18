from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from checkers.jacobian import (
    check_jacobian_positive,
    check_mesh_quality,
    compute_signed_tetra_volume,
    compute_tetra_volume,
)


def test_compute_tetra_volume():
    pts = [
        np.array([0, 0, 0]),
        np.array([1, 0, 0]),
        np.array([0.5, np.sqrt(3) / 2, 0]),
        np.array([0.5, np.sqrt(3) / 6, np.sqrt(2 / 3)]),
    ]
    expected = 1.0 / (6 * np.sqrt(2))
    np.testing.assert_almost_equal(compute_tetra_volume(pts), expected)


def test_compute_signed_tetra_volume_detects_inversion():
    pts = [
        np.array([0, 0, 0]),
        np.array([1, 0, 0]),
        np.array([0.5, np.sqrt(3) / 2, 0]),
        np.array([0.5, np.sqrt(3) / 6, np.sqrt(2 / 3)]),
    ]
    inverted = [pts[0], pts[2], pts[1], pts[3]]

    assert compute_signed_tetra_volume(pts) > 0
    assert compute_signed_tetra_volume(inverted) < 0


@patch("checkers.jacobian.MESHIO_AVAILABLE", False)
def test_check_mesh_quality_fallback(tmp_path):
    mesh_path = tmp_path / "model.inp"
    mesh_path.write_text("Hello mesh", encoding="utf-8")

    result = check_mesh_quality(mesh_path)
    assert result["ok"] is True
    assert result["min_scaled_jacobian"] == 0.8

    ok, bad_ids = check_jacobian_positive(mesh_path)
    assert ok is True
    assert bad_ids == []

    mesh_path.write_text("BAD_JACOBIAN triggers fail mock", encoding="utf-8")
    result = check_mesh_quality(mesh_path)
    assert result["ok"] is False
    assert result["min_scaled_jacobian"] == 0.05
    ok, bad_ids = check_jacobian_positive(mesh_path)
    assert ok is False
    assert bad_ids == [1]

    mesh_path.write_text("BAD_RESOLUTION triggers aspect-ratio fail mock", encoding="utf-8")
    result = check_mesh_quality(mesh_path)
    assert result["ok"] is False
    assert result["bad_element_ids"] == []
    assert result["resolution_element_ids"] == [1]


def test_check_mesh_quality_with_meshio_mock(tmp_path):
    mock_meshio = MagicMock()

    class MockMesh:
        def __init__(self):
            self.points = np.array(
                [
                    [0, 0, 0],
                    [1, 0, 0],
                    [0.5, np.sqrt(3) / 2, 0],
                    [0.5, np.sqrt(3) / 6, np.sqrt(2 / 3)],
                ]
            )

            class MockCellBlock:
                type = "tetra"
                data = np.array([[0, 1, 2, 3]])

            self.cells = [MockCellBlock()]

    mock_meshio.read.return_value = MockMesh()
    mesh_path = tmp_path / "model.inp"
    mesh_path.touch()

    with (
        patch.dict("sys.modules", {"meshio": mock_meshio}),
        patch("checkers.jacobian.MESHIO_AVAILABLE", True),
    ):
        import checkers.jacobian as jac

        jac.meshio = mock_meshio
        result = jac.check_mesh_quality(mesh_path, thresholds={"min_scaled_jacobian": 0.5})

        assert result["ok"] is True
        np.testing.assert_almost_equal(result["min_scaled_jacobian"], 1.0)
        np.testing.assert_almost_equal(result["max_aspect_ratio"], 1.0)
        assert result["degenerate_pct"] == 0.0

        ok, bad_ids = jac.check_jacobian_positive(mesh_path, min_scaled_jacobian=0.5)
        assert ok is True
        assert bad_ids == []


def test_check_mesh_quality_degenerate_and_skewed(tmp_path):
    mock_meshio = MagicMock()

    class MockBadMesh:
        def __init__(self):
            self.points = np.array(
                [
                    [0, 0, 0],
                    [1, 0, 0],
                    [0, 1, 0],
                    [1, 1, 0],
                ]
            )

            class MockCellBlock:
                type = "tetra"
                data = np.array([[0, 1, 2, 3]])

            self.cells = [MockCellBlock()]

    mock_meshio.read.return_value = MockBadMesh()
    mesh_path = tmp_path / "model.inp"
    mesh_path.touch()

    with (
        patch.dict("sys.modules", {"meshio": mock_meshio}),
        patch("checkers.jacobian.MESHIO_AVAILABLE", True),
    ):
        import checkers.jacobian as jac

        jac.meshio = mock_meshio
        result = jac.check_mesh_quality(mesh_path)

        assert result["ok"] is False
        np.testing.assert_almost_equal(result["min_scaled_jacobian"], 0.0)
        assert result["bad_element_ids"] == [1]

        ok, bad_ids = jac.check_jacobian_positive(mesh_path)
        assert ok is False
        assert bad_ids == [1]


def test_check_mesh_quality_flags_resolution_issue_without_bad_jacobian(tmp_path):
    mock_meshio = MagicMock()

    class MockSkewedMesh:
        def __init__(self):
            self.points = np.array(
                [
                    [0.0, 0.0, 0.0],
                    [100.0, 0.0, 0.0],
                    [80.0, 5.0, 0.0],
                    [80.0, 0.0, 5.0],
                ]
            )

            class MockCellBlock:
                type = "tetra"
                data = np.array([[0, 1, 2, 3]])

            self.cells = [MockCellBlock()]

    mock_meshio.read.return_value = MockSkewedMesh()
    mesh_path = tmp_path / "model.inp"
    mesh_path.touch()

    with (
        patch.dict("sys.modules", {"meshio": mock_meshio}),
        patch("checkers.jacobian.MESHIO_AVAILABLE", True),
    ):
        import checkers.jacobian as jac

        jac.meshio = mock_meshio
        result = jac.check_mesh_quality(
            mesh_path,
            thresholds={"min_scaled_jacobian": 0.01, "max_aspect_ratio": 8.0},
        )

        assert result["ok"] is False
        assert result["bad_element_ids"] == []
        assert result["resolution_element_ids"] == [1]
