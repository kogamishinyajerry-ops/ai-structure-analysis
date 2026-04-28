"""Tests for the W6a / ADR-019 material library loader.

Three buckets:

1. ``test_builtin_library_loads_and_validates`` — every JSON entry
   parses, all required fields present, numeric values sane.
2. ``test_lookup_builtin_round_trip`` — picking by code_grade returns
   the same Material the loader emitted.
3. ``test_user_supplied_json_flagged_and_validated`` — free-input
   path produces ``is_user_supplied=True`` and rejects malformed
   payloads with :class:`MaterialLookupError` (not a generic crash).

The library file itself is the authoritative data source; if its
content drifts these tests are the first thing that fires.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.core.types import UnitSystem
from app.services.report.materials_lib import (
    BUILTIN_LIBRARY_PATH,
    MaterialLookupError,
    list_builtin_grades,
    load_builtin_library,
    load_user_supplied_json,
    lookup_builtin,
)

# ---------------------------------------------------------------------------
# Bucket 1 — built-in library load + integrity
# ---------------------------------------------------------------------------


def test_builtin_library_path_exists() -> None:
    """The library JSON ships in the package; missing it is a build
    error, not a runtime fallback condition."""
    assert BUILTIN_LIBRARY_PATH.is_file(), f"materials.json must exist at {BUILTIN_LIBRARY_PATH}"


def test_builtin_library_loads_and_validates() -> None:
    """Every built-in entry must parse cleanly and produce a
    :class:`Material` whose numeric fields are positive finite, ν is
    in (0, 0.5), σ_y < σ_u (yield always below ultimate for
    structural steel — catches mistyped strengths)."""
    lib = load_builtin_library()
    assert len(lib) >= 12, (
        f"library should ship at least 12 grades (ADR-019 §6 frozen list); got {len(lib)}"
    )
    for grade, mat in lib.items():
        assert mat.code_grade == grade
        assert mat.youngs_modulus > 0
        assert 0 < mat.poissons_ratio < 0.5
        assert mat.yield_strength > 0
        assert mat.ultimate_strength > 0
        assert mat.yield_strength < mat.ultimate_strength, (
            f"{grade}: σ_y={mat.yield_strength} should be < σ_u="
            f"{mat.ultimate_strength} for structural steel"
        )
        assert mat.code_standard in ("GB", "ASME", "EN")
        assert mat.source_citation, f"{grade}: missing source_citation"
        assert mat.unit_system == UnitSystem.SI_MM
        assert mat.is_user_supplied is False


def test_builtin_library_anchors_q345b_specific_values() -> None:
    """Anchor test against the literal frozen values for Q345B
    (ADR-019 §6 row 2). If somebody silently shifts σ_y to 350 or
    swaps the citation, this test fires."""
    q = lookup_builtin("Q345B")
    assert q is not None
    assert q.code_standard == "GB"
    assert q.youngs_modulus == 206000
    assert q.poissons_ratio == 0.30
    assert q.yield_strength == 345
    assert q.ultimate_strength == 470
    assert q.source_citation == "GB/T 1591-2018 §6.2 Table 7"


def test_list_builtin_grades_returns_sorted_unique() -> None:
    grades = list_builtin_grades()
    assert grades == sorted(grades), "list_builtin_grades must be sorted"
    assert len(grades) == len(set(grades)), "no duplicates"
    # spot-check membership
    assert "Q345B" in grades
    assert "SA-516-70" in grades


# ---------------------------------------------------------------------------
# Bucket 2 — lookup round-trip
# ---------------------------------------------------------------------------


def test_lookup_builtin_known_grade_returns_material() -> None:
    mat = lookup_builtin("Q235B")
    assert mat is not None
    assert mat.code_grade == "Q235B"
    assert mat.code_standard == "GB"


def test_lookup_builtin_unknown_returns_none() -> None:
    assert lookup_builtin("UNKNOWN-GRADE") is None
    # case-sensitivity is documented (ADR-019): q345b ≠ Q345B
    assert lookup_builtin("q345b") is None


def test_lookup_builtin_is_idempotent() -> None:
    """Cache: repeated lookups must return the SAME Material instance
    (frozen dataclass equality is value-based, but we want to confirm
    no per-call reconstruction work)."""
    a = lookup_builtin("Q345B")
    b = lookup_builtin("Q345B")
    assert a is b


# ---------------------------------------------------------------------------
# Bucket 3 — user-supplied JSON
# ---------------------------------------------------------------------------


_VALID_USER_ENTRY = {
    "code_grade": "MY-CUSTOM-STEEL",
    "code_standard": "GB",
    "youngs_modulus": 210000,
    "poissons_ratio": 0.30,
    "yield_strength": 360,
    "ultimate_strength": 520,
    "density": 7.85e-9,
    "source_citation": "Engineer-supplied; institute-internal mat card",
}


def test_user_supplied_json_bare_entry_flagged(tmp_path: Path) -> None:
    p = tmp_path / "mat.json"
    p.write_text(json.dumps(_VALID_USER_ENTRY), encoding="utf-8")
    mat = load_user_supplied_json(p)
    assert mat.is_user_supplied is True
    assert mat.code_grade == "MY-CUSTOM-STEEL"
    assert mat.yield_strength == 360


def test_user_supplied_json_wrapped_form_accepted(tmp_path: Path) -> None:
    p = tmp_path / "mat.json"
    p.write_text(json.dumps({"materials": [_VALID_USER_ENTRY]}), encoding="utf-8")
    mat = load_user_supplied_json(p)
    assert mat.is_user_supplied is True
    assert mat.code_grade == "MY-CUSTOM-STEEL"


def test_user_supplied_json_missing_required_field_refuses(
    tmp_path: Path,
) -> None:
    bad = dict(_VALID_USER_ENTRY)
    del bad["yield_strength"]
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(MaterialLookupError, match="yield_strength"):
        load_user_supplied_json(p)


def test_user_supplied_json_negative_modulus_refuses(tmp_path: Path) -> None:
    bad = dict(_VALID_USER_ENTRY)
    bad["youngs_modulus"] = -1
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(MaterialLookupError, match="positive finite"):
        load_user_supplied_json(p)


def test_user_supplied_json_invalid_poisson_refuses(tmp_path: Path) -> None:
    bad = dict(_VALID_USER_ENTRY)
    bad["poissons_ratio"] = 0.7  # outside (0, 0.5) physical band
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(MaterialLookupError, match="poissons_ratio"):
        load_user_supplied_json(p)


def test_user_supplied_json_unknown_standard_refuses(tmp_path: Path) -> None:
    bad = dict(_VALID_USER_ENTRY)
    bad["code_standard"] = "XYZ"
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(MaterialLookupError, match="code_standard"):
        load_user_supplied_json(p)


def test_user_supplied_json_malformed_json_refuses(tmp_path: Path) -> None:
    p = tmp_path / "junk.json"
    p.write_text("not-json{{{", encoding="utf-8")
    with pytest.raises(MaterialLookupError, match="not valid JSON"):
        load_user_supplied_json(p)


def test_user_supplied_json_missing_file_refuses(tmp_path: Path) -> None:
    p = tmp_path / "nope.json"
    with pytest.raises(MaterialLookupError, match="missing"):
        load_user_supplied_json(p)


def test_user_supplied_json_wrapped_must_have_exactly_one(
    tmp_path: Path,
) -> None:
    """The wrapped form is a copy-paste convenience for engineers
    starting from materials.json. Two-or-more entries is ambiguous —
    refuse rather than silently pick the first."""
    p = tmp_path / "two.json"
    p.write_text(
        json.dumps({"materials": [_VALID_USER_ENTRY, _VALID_USER_ENTRY]}),
        encoding="utf-8",
    )
    with pytest.raises(MaterialLookupError, match="exactly one entry"):
        load_user_supplied_json(p)
