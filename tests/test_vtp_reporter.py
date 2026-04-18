"""Tests for reporters/vtp.py."""

from __future__ import annotations

from reporters.vtp import export_vtp


def test_export_vtp_writes_point_cloud(tmp_path):
    parsed = {
        "nodes": {
            1: [0.0, 0.0, 0.0],
            2: [1.0, 0.0, 0.0],
        },
        "fields": {
            "displacement": {
                "component_names": ["D1", "D2", "D3"],
                "values": {
                    1: [0.0, 0.0, 0.0],
                    2: [1.0e-3, 0.0, 0.0],
                },
            }
        },
    }

    vtp_path = export_vtp(parsed, tmp_path)

    assert vtp_path.exists()
    content = vtp_path.read_text(encoding="utf-8")
    assert "<VTKFile" in content
    assert 'Name="displacement"' in content
    assert "NumberOfPoints=\"2\"" in content
