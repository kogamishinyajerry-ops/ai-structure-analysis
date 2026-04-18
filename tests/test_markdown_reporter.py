"""Tests for reporters/markdown.py — report generation."""

from reporters.markdown import generate_report


class TestGenerateReport:
    def test_basic_report(self, tmp_path):
        results = {
            "case_id": "AI-FEA-P0-09",
            "description": "Cantilever beam static analysis",
            "verdict": "Accept",
            "fields": [
                {
                    "field": "displacement",
                    "metric": "displacement",
                    "max_magnitude": 1.5e-3,
                    "max_node": 42,
                    "min_magnitude": 0.0,
                    "min_node": 1,
                },
                {
                    "field": "stress",
                    "metric": "von_mises",
                    "max_magnitude": 1.2e6,
                    "max_node": 10,
                    "min_magnitude": 100.0,
                    "min_node": 3,
                },
            ],
            "reference_values": {"displacement": 1.6e-3},
            "wall_time_s": 12.5,
        }

        path = generate_report(results, tmp_path)

        assert path.exists()
        assert path.name == "report.md"

        content = path.read_text(encoding="utf-8")
        assert "AI-FEA-P0-09" in content
        assert "✅" in content
        assert "displacement" in content
        assert "von_mises" in content
        assert "12.5" in content
        assert "Reference Comparison" in content

    def test_fail_verdict(self, tmp_path):
        results = {
            "case_id": "FAIL-001",
            "verdict": "Reject",
            "fields": [],
            "reference_values": {},
        }

        path = generate_report(results, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "❌" in content
        assert "FAIL" in content

    def test_mesh_quality_section(self, tmp_path):
        results = {
            "case_id": "MQ-001",
            "verdict": "Accept",
            "fields": [],
            "reference_values": {},
            "mesh_quality": {
                "min_jacobian": 0.85,
                "max_aspect_ratio": 3.2,
            },
        }

        path = generate_report(results, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "Mesh Quality" in content
        assert "0.85" in content
        assert "3.2" in content

    def test_no_fields(self, tmp_path):
        results = {
            "case_id": "EMPTY-001",
            "verdict": "Needs Review",
            "fields": [],
            "reference_values": {},
        }

        path = generate_report(results, tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "No field data available" in content
