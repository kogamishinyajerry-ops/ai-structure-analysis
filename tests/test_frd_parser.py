"""Tests for tools/frd_parser.py — FRD parsing and field extraction."""

import numpy as np
import pytest

from tools.frd_parser import extract_field_extremes, parse_frd

# Minimal synthetic FRD content mimicking CalculiX ASCII output.
SAMPLE_FRD = """\
    1C
    2C                                                                   1
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.00000E+00 0.00000E+00 0.00000E+00
 -1         3 5.00000E-01 8.66025E-01 0.00000E+00
 -3
 100CL 101         1           1PDISP               1  1
 -4  D1
 -4  D2
 -4  D3
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.50000E-03 0.00000E+00-2.00000E-04
 -1         3 7.50000E-04 1.00000E-03 0.00000E+00
 -3
 100CL 102         1           1PSTRESS             1  1
 -4  SXX
 -4  SYY
 -4  SZZ
 -4  SXY
 -4  SYZ
 -4  SZX
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.20000E+06 3.00000E+05 0.00000E+00 1.50000E+05 0.00000E+00 0.00000E+00
 -1         3 6.00000E+05 1.50000E+05 0.00000E+00 7.50000E+04 0.00000E+00 0.00000E+00
 -3
 9999
"""


class TestParseFrd:
    def test_parse_nodes(self, tmp_path):
        frd = tmp_path / "test.frd"
        frd.write_text(SAMPLE_FRD)

        result = parse_frd(frd)
        nodes = result["nodes"]

        assert len(nodes) == 3
        np.testing.assert_allclose(nodes[1], [0, 0, 0])
        np.testing.assert_allclose(nodes[2], [1, 0, 0])

    def test_parse_fields(self, tmp_path):
        frd = tmp_path / "test.frd"
        frd.write_text(SAMPLE_FRD)

        result = parse_frd(frd)
        fields = result["fields"]

        assert len(fields) == 2
        assert "displacement" in fields
        assert "stress" in fields

    def test_displacement_values(self, tmp_path):
        frd = tmp_path / "test.frd"
        frd.write_text(SAMPLE_FRD)

        result = parse_frd(frd)
        disp = result["fields"]["displacement"]

        assert len(disp["values"]) == 3
        assert len(disp["component_names"]) == 3
        # Node 2 should have the largest displacement
        np.testing.assert_allclose(disp["values"][2][:3], [1.5e-3, 0, -2e-4], atol=1e-10)

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_frd(tmp_path / "nonexistent.frd")


class TestExtractFieldExtremes:
    def test_displacement_extremes(self, tmp_path):
        frd = tmp_path / "test.frd"
        frd.write_text(SAMPLE_FRD)

        parsed = parse_frd(frd)
        extremes = extract_field_extremes(parsed, "displacement")

        assert extremes["field"] == "displacement"
        assert extremes["max_node"] == 2  # Node 2 has largest displacement
        assert extremes["max_magnitude"] > 0
        assert extremes["min_node"] == 1  # Node 1 is fixed (zero disp)
        np.testing.assert_almost_equal(extremes["min_magnitude"], 0.0)

    def test_missing_field(self, tmp_path):
        frd = tmp_path / "test.frd"
        frd.write_text(SAMPLE_FRD)

        parsed = parse_frd(frd)
        extremes = extract_field_extremes(parsed, "temperature")

        assert extremes["max_magnitude"] is None

    def test_empty_frd(self, tmp_path):
        frd = tmp_path / "empty.frd"
        frd.write_text("    1C\n 9999\n")

        parsed = parse_frd(frd)
        assert len(parsed["nodes"]) == 0
        assert len(parsed["fields"]) == 0

    def test_stress_uses_von_mises_metric(self, tmp_path):
        frd = tmp_path / "test.frd"
        frd.write_text(SAMPLE_FRD)

        parsed = parse_frd(frd)
        extremes = extract_field_extremes(parsed, "stress")

        assert extremes["metric"] == "von_mises"
        assert extremes["max_node"] == 2
        assert extremes["max_magnitude"] > 1.0e6
