"""Tests for tools/inp_linter.py — P1-06 Gate-Solve static lint."""

from __future__ import annotations

from pathlib import Path

import pytest

from schemas.sim_state import FaultClass
from tools.inp_linter import (
    KNOWN_ELEMENT_TYPES,
    KNOWN_KEYWORDS,
    LintReport,
    lint_inp,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "deck.inp"
    path.write_text(body, encoding="utf-8")
    return path


MINIMAL_VALID_DECK = """\
*HEADING
Minimal deck
*NODE
1, 0.0, 0.0, 0.0
2, 1.0, 0.0, 0.0
*ELEMENT, TYPE=C3D8, ELSET=BEAM
1, 1, 2, 1, 1, 1, 1, 1, 1
*MATERIAL, NAME=STEEL
*ELASTIC
210000.0, 0.3
*SOLID SECTION, ELSET=BEAM, MATERIAL=STEEL
*BOUNDARY
1, 1, 6, 0.0
*STEP
*STATIC
*CLOAD
2, 2, -100.0
*NODE FILE
U
*END STEP
"""


class TestHappyPath:
    def test_minimal_deck_is_clean(self, tmp_path):
        deck = _write(tmp_path, MINIMAL_VALID_DECK)
        report = lint_inp(deck)
        assert report.ok
        assert report.errors == []

    def test_gs001_canonical_deck_is_clean(self):
        deck = REPO_ROOT / "golden_samples" / "GS-001" / "gs001.inp"
        report = lint_inp(deck)
        assert report.ok, f"Canonical GS-001 deck must pass lint: {[f.code for f in report.errors]}"


class TestKeywordChecks:
    def test_typo_cload_detected(self, tmp_path):
        deck = _write(tmp_path, MINIMAL_VALID_DECK.replace("*CLOAD", "*CLAOD"))
        report = lint_inp(deck)
        codes = [f.code for f in report.errors]
        assert "E-TYPO-KEYWORD" in codes
        finding = next(f for f in report.errors if f.code == "E-TYPO-KEYWORD")
        assert "CLOAD" in finding.message
        assert finding.fault_class_hint == FaultClass.SOLVER_SYNTAX

    def test_unknown_keyword_detected(self, tmp_path):
        deck = _write(tmp_path, MINIMAL_VALID_DECK + "\n*FROBNICATE\n1, 2, 3\n")
        report = lint_inp(deck)
        assert any(f.code == "E-UNKNOWN-KEYWORD" for f in report.errors)

    def test_known_keyword_catalog_covers_common_blocks(self):
        # Guard against someone accidentally shrinking the catalog.
        for kw in ("NODE", "ELEMENT", "MATERIAL", "ELASTIC", "STEP", "STATIC", "CLOAD", "END STEP"):
            assert kw in KNOWN_KEYWORDS


class TestRequiredBlocks:
    def test_missing_step_flagged(self, tmp_path):
        deck = _write(tmp_path, MINIMAL_VALID_DECK.replace("*STEP\n*STATIC\n", "").replace("*END STEP\n", ""))
        report = lint_inp(deck)
        assert any(f.code == "E-MISSING-STEP" for f in report.errors)

    def test_missing_material_flagged(self, tmp_path):
        body = MINIMAL_VALID_DECK.replace("*MATERIAL, NAME=STEEL\n*ELASTIC\n210000.0, 0.3\n", "")
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        codes = [f.code for f in report.errors]
        assert "E-MISSING-MATERIAL" in codes
        # SOLID SECTION references an undefined material as a secondary error.
        assert "E-UNDEFINED-MATERIAL" in codes

    def test_unbalanced_step_flagged(self, tmp_path):
        # Extra *STEP with no *END STEP
        body = MINIMAL_VALID_DECK.replace("*END STEP\n", "") + "*STEP\n*STATIC\n*END STEP\n"
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        assert any(f.code == "E-UNBALANCED-STEP" for f in report.errors)


class TestElementTypeCheck:
    def test_unknown_element_type_flagged(self, tmp_path):
        body = MINIMAL_VALID_DECK.replace("TYPE=C3D8", "TYPE=C3B8")
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        assert any(f.code == "E-UNKNOWN-ELEMENT-TYPE" for f in report.errors)

    def test_element_missing_type_flagged(self, tmp_path):
        body = MINIMAL_VALID_DECK.replace("*ELEMENT, TYPE=C3D8, ELSET=BEAM", "*ELEMENT, ELSET=BEAM")
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        assert any(f.code == "E-ELEMENT-NO-TYPE" for f in report.errors)

    def test_element_catalog_covers_common_types(self):
        for t in ("C3D8", "C3D8I", "C3D20R", "S4", "B31", "T3D2", "C3D10"):
            assert t in KNOWN_ELEMENT_TYPES


class TestReferenceIntegrity:
    def test_undefined_elset_on_section_flagged(self, tmp_path):
        body = MINIMAL_VALID_DECK.replace(
            "*SOLID SECTION, ELSET=BEAM, MATERIAL=STEEL",
            "*SOLID SECTION, ELSET=TRUSS, MATERIAL=STEEL",
        )
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        assert any(f.code == "E-UNDEFINED-ELSET" for f in report.errors)

    def test_undefined_material_on_section_flagged(self, tmp_path):
        body = MINIMAL_VALID_DECK.replace(
            "*SOLID SECTION, ELSET=BEAM, MATERIAL=STEEL",
            "*SOLID SECTION, ELSET=BEAM, MATERIAL=COPPER",
        )
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        assert any(f.code == "E-UNDEFINED-MATERIAL" for f in report.errors)


class TestDuplicateIDs:
    def test_duplicate_node_id_flagged(self, tmp_path):
        body = MINIMAL_VALID_DECK.replace(
            "*NODE\n1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0",
            "*NODE\n1, 0.0, 0.0, 0.0\n1, 1.0, 0.0, 0.0\n2, 2.0, 0.0, 0.0",
        )
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        assert any(f.code == "E-DUPLICATE-NODE-ID" for f in report.errors)

    def test_duplicate_element_id_flagged(self, tmp_path):
        body = MINIMAL_VALID_DECK.replace(
            "*ELEMENT, TYPE=C3D8, ELSET=BEAM\n1, 1, 2, 1, 1, 1, 1, 1, 1",
            "*ELEMENT, TYPE=C3D8, ELSET=BEAM\n1, 1, 2, 1, 1, 1, 1, 1, 1\n1, 1, 2, 1, 1, 1, 1, 1, 1",
        )
        deck = _write(tmp_path, body)
        report = lint_inp(deck)
        assert any(f.code == "E-DUPLICATE-ELEMENT-ID" for f in report.errors)


class TestReportSerialization:
    def test_report_to_dict_is_json_serializable(self, tmp_path):
        import json

        deck = _write(tmp_path, MINIMAL_VALID_DECK.replace("*CLOAD", "*CLAOD"))
        report = lint_inp(deck)
        payload = report.to_dict()
        # fault_class_hint is a StrEnum — must round-trip through json.
        serialized = json.dumps(payload)
        assert "solver_syntax" in serialized
        assert payload["ok"] is False
        assert payload["error_count"] >= 1

    def test_report_ok_when_only_warnings(self, tmp_path):
        deck = _write(tmp_path, MINIMAL_VALID_DECK)
        report = lint_inp(deck)
        assert isinstance(report, LintReport)
        assert report.ok

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            lint_inp(tmp_path / "does_not_exist.inp")
