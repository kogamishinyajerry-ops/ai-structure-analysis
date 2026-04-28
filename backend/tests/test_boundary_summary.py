"""W6d boundary-summary library tests — RFC-001 W6d.

Test buckets:

1. Loader happy path (valid bc.yaml → list[BoundaryCondition])
2. Schema refusals (missing keys / wrong types / duplicates)
3. Empty / partial files
4. Unit-system parsing (case-insensitive)
5. Component-value validation (numbers only, no booleans)
6. Summary aggregation (counts / unknown bucket / unit dedup)
7. Deep-immutability of BCSummary
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from app.core.types import BoundaryCondition, UnitSystem
from app.services.report.boundary_summary import (
    BCSummary,
    BCSummaryError,
    KNOWN_KINDS,
    load_boundary_conditions_yaml,
    summarize_boundary_conditions,
)


# ---------------------------------------------------------------------------
# Bucket 1 — loader happy path
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "bc.yaml"
    p.write_text(dedent(body), encoding="utf-8")
    return p


def test_loader_returns_two_bcs_in_source_order(tmp_path: Path) -> None:
    """GS-001 smoke: 1 fixed constraint + 1 pressure load. Source order
    must round-trip — the DOCX renderer cross-references the rows back
    to the engineer's notes by index."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: fixed_bottom
            kind: fixed
            target: NSET=bottom
            components: {ux: 0.0, uy: 0.0, uz: 0.0}
            unit_system: SI_mm
          - name: top_pressure
            kind: pressure
            target: ELSET=top_face
            components: {pressure: 5.0}
            unit_system: SI_mm
        """,
    )
    bcs = load_boundary_conditions_yaml(p)

    assert len(bcs) == 2
    assert all(isinstance(b, BoundaryCondition) for b in bcs)

    assert bcs[0].name == "fixed_bottom"
    assert bcs[0].kind == "fixed"
    assert bcs[0].target == "NSET=bottom"
    assert dict(bcs[0].components) == {"ux": 0.0, "uy": 0.0, "uz": 0.0}
    assert bcs[0].unit_system is UnitSystem.SI_MM

    assert bcs[1].name == "top_pressure"
    assert bcs[1].kind == "pressure"
    assert dict(bcs[1].components) == {"pressure": 5.0}


def test_loader_returns_empty_list_on_empty_yaml_file(tmp_path: Path) -> None:
    """An empty file is valid: it means the engineer has no BC yet.
    The DOCX renderer flags this with a [需工程师确认] placeholder
    rather than refusing — distinguishes "uploaded empty" from "did
    not upload"."""
    p = tmp_path / "bc.yaml"
    p.write_text("", encoding="utf-8")
    assert load_boundary_conditions_yaml(p) == []


def test_loader_returns_empty_list_when_bcs_list_is_empty(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions: []
        """,
    )
    assert load_boundary_conditions_yaml(p) == []


# ---------------------------------------------------------------------------
# Bucket 2 — schema refusals
# ---------------------------------------------------------------------------


def test_loader_refuses_missing_file(tmp_path: Path) -> None:
    bogus = tmp_path / "does_not_exist.yaml"
    with pytest.raises(BCSummaryError, match="bc.yaml not found"):
        load_boundary_conditions_yaml(bogus)


def test_loader_refuses_top_level_list(tmp_path: Path) -> None:
    """Top level must be a mapping; a list at the top level is a
    common engineer typo (forgot the `boundary_conditions:` key)."""
    p = _write_yaml(
        tmp_path,
        """
        - name: x
          kind: fixed
          target: NSET=foo
          components: {ux: 0.0}
          unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="top-level must be a mapping"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_missing_boundary_conditions_key(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        bcs:
          - name: x
            kind: fixed
        """,
    )
    with pytest.raises(BCSummaryError, match="no top-level 'boundary_conditions' key"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_bcs_list_of_wrong_type(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          oops: not a list
        """,
    )
    with pytest.raises(BCSummaryError, match="must be a list"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_bc_missing_required_key(tmp_path: Path) -> None:
    """Missing ``components`` is a typical engineer mistake (forgot
    the load magnitude). Error message must call out the missing key
    by name so they see what's wrong without re-reading the schema."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: incomplete
            kind: fixed
            target: NSET=foo
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="missing required key.*components"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_duplicate_bc_name(tmp_path: Path) -> None:
    """Two BCs sharing a name silently merge in some downstream
    consumers; refuse loudly here rather than letting the engineer
    discover the merge in the DOCX table."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: dup
            kind: fixed
            target: NSET=a
            components: {ux: 0.0}
            unit_system: SI_mm
          - name: dup
            kind: pressure
            target: ELSET=b
            components: {pressure: 1.0}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="duplicate bc.name 'dup'"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_empty_name(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: ""
            kind: fixed
            target: NSET=foo
            components: {ux: 0.0}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be a non-empty string"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_empty_components(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: empty_comp
            kind: fixed
            target: NSET=foo
            components: {}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="non-empty mapping"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_unknown_unit_system(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: bad_unit
            kind: fixed
            target: NSET=foo
            components: {ux: 0.0}
            unit_system: cgs
        """,
    )
    with pytest.raises(BCSummaryError, match="unknown unit_system 'cgs'"):
        load_boundary_conditions_yaml(p)


# ---------------------------------------------------------------------------
# Bucket 2b — Codex R1 (PR #101) silent-acceptance refusals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "yaml_quoted",
    [
        '"   "',         # 3 spaces in double quotes
        '"\\t"',        # YAML double-quoted \t → tab character
        '"\\n"',        # YAML double-quoted \n → newline character
        '"  \\t  "',    # mixed whitespace
    ],
)
def test_loader_refuses_whitespace_only_name(
    tmp_path: Path, yaml_quoted: str
) -> None:
    """Codex R1 HIGH-1 (PR #101): ``not v`` accepted whitespace-only
    name/kind/target and produced a silently-corrupt
    BoundaryCondition. Strip-then-validate closes the hole.

    The parametrized values are YAML literals (double-quoted so
    ``\\t`` / ``\\n`` are interpreted as control characters by the
    YAML parser, matching what an engineer might paste from a
    spreadsheet copy)."""
    p = _write_yaml(
        tmp_path,
        f"""
        boundary_conditions:
          - name: {yaml_quoted}
            kind: fixed
            target: NSET=foo
            components: {{ux: 0.0}}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be a non-empty string"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_whitespace_only_kind(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: x
            kind: "   "
            target: NSET=foo
            components: {ux: 0.0}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be a non-empty string"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_whitespace_only_target(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: x
            kind: fixed
            target: "  \t  "
            components: {ux: 0.0}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be a non-empty string"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_post_strip_component_key_collision(tmp_path: Path) -> None:
    """Codex R2 PR #101 HIGH (regression in R1 fix): stripping
    component keys without a collision check silently overwrites
    the earlier value when two keys normalise to the same identifier.
    POC: ``fx: 1.0`` then ``" fx ": 2.0`` previously loaded as
    ``{'fx': 2.0}``. Refuse loudly — same class as the BC-name
    collision rule.

    YAML mappings preserve insertion order under PyYAML, so this
    test produces a deterministic ``fx`` first, ``" fx "`` second
    sequence the loader sees.
    """
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: collide
            kind: force
            target: NSET=x
            components:
              fx: 1.0
              " fx ": 2.0
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="duplicate key 'fx'"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_whitespace_only_component_key(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: x
            kind: fixed
            target: NSET=foo
            components: {"   ": 0.0}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="empty / whitespace-only key"):
        load_boundary_conditions_yaml(p)


def test_loader_strips_name_for_duplicate_detection(tmp_path: Path) -> None:
    """Codex R1 HIGH-1 follow-on: duplicate-detection used to operate
    on unnormalised names. After strip, ``"dup"`` and ``"dup "`` are
    the same name and must collide."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: "dup"
            kind: fixed
            target: NSET=a
            components: {ux: 0.0}
            unit_system: SI_mm
          - name: "dup  "
            kind: pressure
            target: ELSET=b
            components: {pressure: 1.0}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="duplicate bc.name 'dup'"):
        load_boundary_conditions_yaml(p)


def test_loader_strips_name_into_boundary_condition(tmp_path: Path) -> None:
    """The stripped name flows through into ``BoundaryCondition.name``
    so the DOCX renderer never sees stray whitespace."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: "  fixed_bottom  "
            kind: fixed
            target: NSET=bottom
            components: {ux: 0.0}
            unit_system: SI_mm
        """,
    )
    bcs = load_boundary_conditions_yaml(p)
    assert bcs[0].name == "fixed_bottom"


@pytest.mark.parametrize(
    "yaml_value,doc_label",
    [
        (".nan", "NaN"),
        (".inf", "+inf"),
        ("-.inf", "-inf"),
    ],
)
def test_loader_refuses_non_finite_component(
    tmp_path: Path, yaml_value: str, doc_label: str
) -> None:
    """Codex R1 HIGH-2 (PR #101): non-finite scalars silently rendered
    as ``fx=nan`` / ``fx=inf`` / ``fx=-inf`` in the DOCX. NaN / ±inf
    have no engineering meaning in a BC magnitude — refuse at the
    boundary, never let them reach the audit line."""
    _ = doc_label  # parametrize id only
    p = _write_yaml(
        tmp_path,
        f"""
        boundary_conditions:
          - name: bad_num
            kind: force
            target: NSET=x
            components: {{fx: {yaml_value}}}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be finite"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_int_beyond_exact_float_range(tmp_path: Path) -> None:
    """Codex R1 HIGH-2 (PR #101) POC: ``2**53 + 1 = 9007199254740993``
    silently coerces to ``9007199254740992.0`` because the IEEE-754
    binary64 mantissa can't represent it exactly. Reject before
    coercion so an engineer typing a 17-digit force value sees the
    error rather than discovering the silent rounding in the DOCX."""
    big = 2**53 + 1
    p = _write_yaml(
        tmp_path,
        f"""
        boundary_conditions:
          - name: too_big
            kind: force
            target: NSET=x
            components: {{fx: {big}}}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="exceeds the exact-float range"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_negative_int_beyond_exact_float_range(
    tmp_path: Path,
) -> None:
    """Symmetric to the positive case — the bound is ``±2**53``."""
    big_neg = -(2**53 + 1)
    p = _write_yaml(
        tmp_path,
        f"""
        boundary_conditions:
          - name: too_neg
            kind: force
            target: NSET=x
            components: {{fx: {big_neg}}}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="exceeds the exact-float range"):
        load_boundary_conditions_yaml(p)


def test_loader_accepts_int_at_exact_float_boundary(tmp_path: Path) -> None:
    """``2**53`` itself IS exactly representable; the bound is
    inclusive. Pin this so a future fix doesn't accidentally tighten
    the threshold to ``< 2**53``."""
    boundary = 2**53
    p = _write_yaml(
        tmp_path,
        f"""
        boundary_conditions:
          - name: at_bound
            kind: force
            target: NSET=x
            components: {{fx: {boundary}}}
            unit_system: SI_mm
        """,
    )
    bcs = load_boundary_conditions_yaml(p)
    assert dict(bcs[0].components) == {"fx": float(boundary)}


# ---------------------------------------------------------------------------
# Bucket 4 — unit_system parsing case-insensitivity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,expected",
    [
        ("SI_mm", UnitSystem.SI_MM),
        ("si_mm", UnitSystem.SI_MM),
        ("SI", UnitSystem.SI),
        ("si", UnitSystem.SI),
        ("English", UnitSystem.ENGLISH),
        ("english", UnitSystem.ENGLISH),
        ("unknown", UnitSystem.UNKNOWN),
    ],
)
def test_loader_parses_unit_system_case_insensitively(
    tmp_path: Path, label: str, expected: UnitSystem
) -> None:
    """Engineers writing bc.yaml by hand will mix cases — accept any
    canonical lower/upper-case spelling but always store the enum."""
    p = _write_yaml(
        tmp_path,
        f"""
        boundary_conditions:
          - name: t
            kind: fixed
            target: NSET=x
            components: {{ux: 0.0}}
            unit_system: {label}
        """,
    )
    bcs = load_boundary_conditions_yaml(p)
    assert bcs[0].unit_system is expected


# ---------------------------------------------------------------------------
# Bucket 5 — component-value validation
# ---------------------------------------------------------------------------


def test_loader_refuses_string_component_value(tmp_path: Path) -> None:
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: t
            kind: force
            target: NSET=x
            components: {fx: "not a number"}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be a real number"):
        load_boundary_conditions_yaml(p)


def test_loader_refuses_boolean_component_value(tmp_path: Path) -> None:
    """``True`` is technically ``int(1)`` in Python — without an
    explicit bool guard a YAML ``true`` would silently become 1.0
    and corrupt the audit trail."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: t
            kind: force
            target: NSET=x
            components: {fx: true}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be a real number"):
        load_boundary_conditions_yaml(p)


def test_loader_accepts_int_and_float_components(tmp_path: Path) -> None:
    """Both YAML int and float must round-trip as float in the
    BoundaryCondition (the dataclass field is ``Mapping[str, float]``)."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: mixed
            kind: force
            target: NSET=x
            components: {fx: 5, fy: 2.5, fz: 0}
            unit_system: SI_mm
        """,
    )
    bcs = load_boundary_conditions_yaml(p)
    comps = dict(bcs[0].components)
    assert comps == {"fx": 5.0, "fy": 2.5, "fz": 0.0}
    for v in comps.values():
        assert isinstance(v, float)


# ---------------------------------------------------------------------------
# Bucket 6 — summary aggregation
# ---------------------------------------------------------------------------


def _make_bc(
    name: str, kind: str, target: str, comps: dict[str, float],
    unit: UnitSystem = UnitSystem.SI_MM,
) -> BoundaryCondition:
    return BoundaryCondition(
        name=name, kind=kind, target=target, components=comps, unit_system=unit,
    )


def test_summary_rows_preserve_source_order() -> None:
    bcs = [
        _make_bc("c1", "fixed", "NSET=a", {"ux": 0.0}),
        _make_bc("c2", "pressure", "ELSET=b", {"pressure": 1.0}),
        _make_bc("c3", "force", "NSET=c", {"fx": 100.0, "fy": -50.0}),
    ]
    summary = summarize_boundary_conditions(bcs)

    names = [r["name"] for r in summary.rows]
    assert names == ["c1", "c2", "c3"]


def test_summary_components_render_as_key_value_string() -> None:
    bc = _make_bc("force", "force", "NSET=x", {"fx": 100.0, "fy": -50.0})
    summary = summarize_boundary_conditions([bc])

    assert summary.rows[0]["components"] == "fx=100, fy=-50"


def test_summary_counts_by_kind_buckets_known_kinds() -> None:
    bcs = [
        _make_bc("a", "fixed", "NSET=1", {"ux": 0.0}),
        _make_bc("b", "fixed", "NSET=2", {"ux": 0.0}),
        _make_bc("c", "pressure", "ELSET=1", {"pressure": 1.0}),
    ]
    for kind in ("fixed", "pressure"):
        assert kind in KNOWN_KINDS

    summary = summarize_boundary_conditions(bcs)
    assert dict(summary.counts_by_kind) == {"fixed": 2, "pressure": 1}


def test_summary_unknown_kind_buckets_into_other() -> None:
    """Stringly-typed ``kind`` accepts open-set values; unknown kinds
    must bucket into ``其他`` so the summary line stays bounded
    regardless of what the engineer types."""
    bcs = [
        _make_bc("a", "exotic_thing", "NSET=1", {"v": 1.0}),
        _make_bc("b", "another_unknown", "NSET=2", {"v": 1.0}),
        _make_bc("c", "fixed", "NSET=3", {"ux": 0.0}),
    ]
    summary = summarize_boundary_conditions(bcs)
    assert summary.counts_by_kind == {"其他": 2, "fixed": 1}
    # But the per-row kind still shows the raw label so the engineer
    # can see what they originally typed.
    raw_kinds = [r["kind"] for r in summary.rows]
    assert raw_kinds == ["exotic_thing", "another_unknown", "fixed"]


def test_summary_unit_systems_dedup_in_order() -> None:
    bcs = [
        _make_bc("a", "fixed", "NSET=1", {"ux": 0.0}, UnitSystem.SI_MM),
        _make_bc("b", "force", "NSET=2", {"fx": 1.0}, UnitSystem.SI_MM),
        _make_bc("c", "pressure", "ELSET=1", {"pressure": 1.0}, UnitSystem.SI),
    ]
    summary = summarize_boundary_conditions(bcs)
    assert summary.unit_systems == ("SI_mm", "SI")


def test_summary_empty_list_returns_empty_summary() -> None:
    summary = summarize_boundary_conditions([])
    assert summary.rows == ()
    assert dict(summary.counts_by_kind) == {}
    assert summary.unit_systems == ()


# ---------------------------------------------------------------------------
# Bucket 7 — deep immutability
# ---------------------------------------------------------------------------


def test_summary_is_frozen() -> None:
    """A frozen dataclass — the DOCX renderer must not be able to
    mutate the summary between extraction and template substitution."""
    from dataclasses import FrozenInstanceError

    bc = _make_bc("a", "fixed", "NSET=1", {"ux": 0.0})
    summary = summarize_boundary_conditions([bc])

    with pytest.raises(FrozenInstanceError):
        summary.rows = ()  # type: ignore[misc]


def test_summary_rows_are_immutable_mappings() -> None:
    """Each row is a MappingProxyType so attempting to mutate
    ``row[key] = ...`` raises rather than corrupts the audit trail."""
    bc = _make_bc("a", "fixed", "NSET=1", {"ux": 0.0})
    summary = summarize_boundary_conditions([bc])

    with pytest.raises(TypeError):
        summary.rows[0]["name"] = "tampered"  # type: ignore[index]


def test_summary_counts_by_kind_is_immutable() -> None:
    bc = _make_bc("a", "fixed", "NSET=1", {"ux": 0.0})
    summary = summarize_boundary_conditions([bc])

    with pytest.raises(TypeError):
        summary.counts_by_kind["tampered"] = 99  # type: ignore[index]


def test_loaded_boundary_condition_components_are_immutable(tmp_path: Path) -> None:
    """Round-trip the loader to confirm the BoundaryCondition
    dataclass's deep-freeze still applies — the W2 Codex MEDIUM-2 fix
    must survive the YAML round trip."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: t
            kind: fixed
            target: NSET=x
            components: {ux: 0.0, uy: 0.0}
            unit_system: SI_mm
        """,
    )
    bcs = load_boundary_conditions_yaml(p)

    with pytest.raises(TypeError):
        bcs[0].components["ux"] = 999.0  # type: ignore[index]


# ---------------------------------------------------------------------------
# Integration sanity — round-trip
# ---------------------------------------------------------------------------


def test_loader_then_summary_round_trip(tmp_path: Path) -> None:
    """End-to-end: bc.yaml → load → summarize. Pins the integration
    contract so a future schema change can't silently desync the two
    halves of the W6d library."""
    p = _write_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: fixed_bottom
            kind: fixed
            target: NSET=bottom
            components: {ux: 0.0, uy: 0.0, uz: 0.0}
            unit_system: SI_mm
          - name: top_pressure
            kind: pressure
            target: ELSET=top_face
            components: {pressure: 5.0}
            unit_system: SI_mm
        """,
    )
    bcs = load_boundary_conditions_yaml(p)
    summary = summarize_boundary_conditions(bcs)

    assert isinstance(summary, BCSummary)
    assert len(summary.rows) == 2
    assert summary.counts_by_kind == {"fixed": 1, "pressure": 1}
    assert summary.unit_systems == ("SI_mm",)
    assert summary.rows[0]["target"] == "NSET=bottom"
    assert summary.rows[1]["components"] == "pressure=5"
