"""W6d boundary-condition summary library (RFC-001 W6d).

Parses a user-supplied ``bc.yaml`` into ``list[BoundaryCondition]``
(the Layer-2 schema in ``app.core.types.domain``) and renders a
``BCSummary`` suitable for the DOCX § 边界条件 table.

Why a separate YAML upload path:

* CalculiX ``.frd`` files do not carry boundary conditions — the BC
  deck lives in ``.inp``, which the W2 reader does not parse today
  (an explicit ADR-003 "do not fabricate" deferral, see
  ``backend/app/adapters/calculix/reader.py``).
* OpenRadioss ``.h3d`` may carry partial BC metadata, but the
  W7b reader has not surveyed the cross-solver translation table yet.
* The simplest universal fallback is "engineer hands the wizard a
  ``bc.yaml``" — every solver workflow can produce one.

This library does *not* parse ``.inp`` directly; that's a separate
adapter-side feature. RFC-001 W6d §"L1 reader option" leaves both
paths open and explicitly approves the YAML-only MVP for the wedge.

Refusal contract (per ADR-019 / ADR-020 §1):

* ``BCSummaryError`` (subclass of ``ValueError``) on malformed YAML:
  missing top-level mapping, missing ``boundary_conditions`` list,
  missing required keys, duplicate ``name``, unknown ``unit_system``,
  non-numeric component values.
* ``kind`` is stringly typed and accepts unknown values (per the
  ``BoundaryCondition`` docstring); the renderer groups unknown
  kinds under "其他" rather than refusing.
* Empty file or empty ``boundary_conditions: []`` returns an empty
  list — the DOCX renderer flags this with a "无边界条件数据
  [需工程师确认]" placeholder, never silently fabricates BCs.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

import yaml
from app.core.types import BoundaryCondition, UnitSystem

__all__ = [
    "BCSummary",
    "BCSummaryError",
    "KNOWN_KINDS",
    "load_boundary_conditions_yaml",
    "summarize_boundary_conditions",
]


# Open-set discriminator. The ``BoundaryCondition`` docstring keeps
# ``kind`` stringly typed pending a cross-solver translation survey;
# this tuple lists the kinds the wedge knows how to group / render.
# Unknown kinds bucket into ``"其他"`` in the summary's ``counts_by_kind``.
KNOWN_KINDS: Final[tuple[str, ...]] = (
    "fixed",
    "force",
    "pressure",
    "displacement",
    "thermal",
    "moment",
    "acceleration",
    "velocity",
)


_OTHER_KIND: Final[str] = "其他"


class BCSummaryError(ValueError):
    """Raised on malformed ``bc.yaml`` schema.

    Subclasses ``ValueError`` so callers can catch both this and the
    constructor argument-validation errors with one ``except``. File-
    not-found uses this class too (rather than ``FileNotFoundError``)
    so the error surface stays consistent with W6b/W6c loaders.
    """


# ---------------------------------------------------------------------------
# Public dataclass — what the DOCX renderer consumes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BCSummary:
    """Aggregated view of a list of ``BoundaryCondition`` for the DOCX
    § 边界条件 section.

    Field semantics:

    * ``rows`` — one immutable dict per BC, in the order they appeared
      in the source. Keys: ``name``, ``kind``, ``target``,
      ``components`` (rendered as ``"key=value, ..."``), ``unit_system``
      (the enum's ``.value``). The DOCX renderer iterates this for the
      table body.
    * ``counts_by_kind`` — ``{kind: count}`` for the summary line above
      the table. Unknown kinds bucket into ``"其他"`` so the renderer
      does not have to special-case them.
    * ``unit_systems`` — distinct unit systems encountered, in source
      order. The DOCX renderer surfaces a warning if more than one
      shows up (mixed-unit BC sets are almost always a wizard bug).

    All fields are deeply immutable: ``rows`` is a tuple of
    ``MappingProxyType`` instances, ``counts_by_kind`` is wrapped in
    ``MappingProxyType``, and ``unit_systems`` is a tuple. A future
    addition of mutable fields must preserve this contract — the
    DOCX renderer must not be able to corrupt the audit trail between
    extraction and template substitution.
    """

    rows: tuple[Mapping[str, str], ...]
    counts_by_kind: Mapping[str, int]
    unit_systems: tuple[str, ...]


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------


_REQUIRED_BC_KEYS: Final[tuple[str, ...]] = (
    "name",
    "kind",
    "target",
    "components",
    "unit_system",
)


# IEEE-754 binary64 represents every integer in ``[-2**53, +2**53]``
# exactly; integers outside that range round to the nearest even
# representable double when coerced to ``float``. Codex R1 (PR #101)
# demonstrated ``9007199254740993`` (= 2**53 + 1) silently loading as
# ``9007199254740992.0`` — exactly the audit-trail corruption ADR-012
# forbids. We refuse such inputs at the boundary rather than letting
# them slip through ``float(int_value)``.
_INT_FLOAT_SAFE_MAX: Final[int] = 2**53


def _strip_required_str(idx: int, key: str, raw: Any) -> str:
    """Validate-and-strip a required string field.

    Codex R1 PR #101 demonstrated that ``not v`` accepted whitespace-
    only values (``name: "   "``), letting a corrupt BoundaryCondition
    through. Strip first, then refuse blank — and use the stripped
    value everywhere downstream (duplicate-name check, BC.name).
    """
    if not isinstance(raw, str):
        raise BCSummaryError(
            f"bc[{idx}].{key} must be a string, got {type(raw).__name__}"
        )
    stripped = raw.strip()
    if not stripped:
        raise BCSummaryError(
            f"bc[{idx}].{key} must be a non-empty string (got {raw!r}, "
            f"empty after stripping whitespace)"
        )
    return stripped


def _check_finite_component(
    idx: int, comp_key: str, raw: Any
) -> float:
    """Validate-and-coerce one component value.

    Codex R1 PR #101 demonstrated three silent-acceptance paths
    through ``float(cv)``:

    * ``.nan`` loaded and rendered as ``fx=nan``
    * ``.inf`` / ``-.inf`` loaded and rendered as ``fx=inf`` / ``fx=-inf``
    * ``2**53 + 1 = 9007199254740993`` loaded as ``9007199254740992.0``
      due to IEEE-754 rounding

    All three are audit-trail corruption — the engineer signs a DOCX
    that quotes a load value materially different from what they
    typed. Refuse all three at the boundary.
    """
    # bool is a subclass of int — explicit guard, since ``True`` would
    # otherwise become ``1.0`` and silently corrupt the BC.
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise BCSummaryError(
            f"bc[{idx}].components[{comp_key!r}] must be a real number, "
            f"got {raw!r} ({type(raw).__name__})"
        )
    # Reject ints beyond the exact-float range *before* coercion.
    if isinstance(raw, int) and abs(raw) > _INT_FLOAT_SAFE_MAX:
        raise BCSummaryError(
            f"bc[{idx}].components[{comp_key!r}]: integer {raw!r} exceeds "
            f"the exact-float range (±2**53 = ±{_INT_FLOAT_SAFE_MAX}); "
            f"coercion would silently lose precision. Provide the value "
            f"as a string-quoted decimal or a smaller magnitude."
        )
    coerced = float(raw)
    if not math.isfinite(coerced):
        raise BCSummaryError(
            f"bc[{idx}].components[{comp_key!r}] must be finite, got {raw!r} "
            f"(rendered as {coerced!r}); NaN / ±inf have no engineering meaning "
            f"in a boundary-condition magnitude"
        )
    return coerced


def _parse_unit_system(label: object) -> UnitSystem:
    """Normalise a yaml string to a ``UnitSystem`` enum member.

    Case-insensitive matching on the enum's ``.value`` so engineer
    convenience labels ``"si_mm"`` / ``"SI_mm"`` / ``"si"`` all
    resolve. ``UNKNOWN`` is accepted but the DOCX renderer will flag
    it — per ADR-003, ``UNKNOWN`` means the wizard hasn't pinned a
    unit system, which in BC context is almost always a setup bug.
    """
    if not isinstance(label, str):
        raise BCSummaryError(
            f"unit_system must be a string, got {type(label).__name__}"
        )
    norm = label.strip()
    for u in UnitSystem:
        if norm == u.value or norm.lower() == u.value.lower():
            return u
    raise BCSummaryError(
        f"unknown unit_system {label!r}; expected one of "
        f"{[u.value for u in UnitSystem]!r}"
    )


@dataclass(frozen=True)
class _ValidatedBC:
    """Internal record produced by :func:`_validate_bc_dict`.

    Holds the *stripped* string fields and the *finite-checked,
    coerced* component values. The caller turns this into a
    ``BoundaryCondition`` without re-parsing — duplicate-name
    detection runs on the stripped name (Codex R1 PR #101 HIGH-1).
    """

    name: str
    kind: str
    target: str
    components: Mapping[str, float]
    unit_system: UnitSystem


def _validate_bc_dict(idx: int, raw: Any) -> _ValidatedBC:
    """Schema-check one entry of the ``boundary_conditions`` list and
    return a fully-validated, coerced record.

    Validates type + presence of every required key and raises
    ``BCSummaryError`` with the offending index + key on any failure.
    String fields are stripped (Codex R1 PR #101 HIGH-1: whitespace-
    only ``name``/``kind``/``target`` was previously accepted) and
    component values are checked for finiteness + exact-float
    representability (Codex R1 PR #101 HIGH-2: NaN, ±inf, and
    ``2**53 + 1`` were previously accepted with silent corruption).
    """
    if not isinstance(raw, dict):
        raise BCSummaryError(
            f"bc[{idx}] must be a mapping, got {type(raw).__name__}"
        )
    missing = [k for k in _REQUIRED_BC_KEYS if k not in raw]
    if missing:
        raise BCSummaryError(
            f"bc[{idx}] missing required key(s) {missing!r}; "
            f"required: {list(_REQUIRED_BC_KEYS)!r}"
        )

    name = _strip_required_str(idx, "name", raw["name"])
    kind = _strip_required_str(idx, "kind", raw["kind"])
    target = _strip_required_str(idx, "target", raw["target"])

    comps = raw["components"]
    if not isinstance(comps, dict) or not comps:
        raise BCSummaryError(
            f"bc[{idx}].components must be a non-empty mapping, got {comps!r}"
        )
    coerced_components: dict[str, float] = {}
    for ck, cv in comps.items():
        if not isinstance(ck, str):
            raise BCSummaryError(
                f"bc[{idx}].components has non-string key {ck!r}"
            )
        ck_stripped = ck.strip()
        if not ck_stripped:
            raise BCSummaryError(
                f"bc[{idx}].components has empty / whitespace-only key {ck!r}"
            )
        coerced_components[ck_stripped] = _check_finite_component(idx, ck_stripped, cv)

    return _ValidatedBC(
        name=name,
        kind=kind,
        target=target,
        components=coerced_components,
        unit_system=_parse_unit_system(raw["unit_system"]),
    )


def load_boundary_conditions_yaml(path: Path) -> list[BoundaryCondition]:
    """Read ``bc.yaml`` and return a validated ``list[BoundaryCondition]``.

    Schema (top-level YAML mapping, ``boundary_conditions`` is a list
    of mappings)::

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

    Returns ``[]`` for an empty list. Raises ``BCSummaryError`` on
    any schema violation; the file path appears in the error message
    so callers see which YAML failed.
    """
    if not path.is_file():
        raise BCSummaryError(f"bc.yaml not found at {path!s}")

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        # Empty YAML file → no BCs. The renderer flags this with the
        # placeholder. Distinguishes "engineer uploaded an empty file"
        # from "engineer didn't upload one" (caller's responsibility
        # not to call this when no file was uploaded).
        return []

    if not isinstance(raw, dict):
        raise BCSummaryError(
            f"bc.yaml top-level must be a mapping, got "
            f"{type(raw).__name__} at {path!s}"
        )

    bcs_raw = raw.get("boundary_conditions")
    if bcs_raw is None:
        raise BCSummaryError(
            f"bc.yaml at {path!s} has no top-level 'boundary_conditions' "
            f"key; got top-level keys {list(raw.keys())!r}"
        )
    if not isinstance(bcs_raw, list):
        raise BCSummaryError(
            f"bc.yaml 'boundary_conditions' must be a list, got "
            f"{type(bcs_raw).__name__} at {path!s}"
        )

    bcs: list[BoundaryCondition] = []
    seen_names: set[str] = set()
    for idx, raw_bc in enumerate(bcs_raw):
        v = _validate_bc_dict(idx, raw_bc)
        # Duplicate detection runs on the *stripped* name so
        # ``"dup"`` and ``"dup "`` are caught as collisions
        # (Codex R1 PR #101 HIGH-1 — duplicate-check used to operate
        # on unnormalised names).
        if v.name in seen_names:
            raise BCSummaryError(
                f"duplicate bc.name {v.name!r} at bc[{idx}]; names must be unique"
            )
        seen_names.add(v.name)
        bcs.append(
            BoundaryCondition(
                name=v.name,
                kind=v.kind,
                target=v.target,
                components=dict(v.components),
                unit_system=v.unit_system,
            )
        )
    return bcs


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _format_components(components: Mapping[str, float]) -> str:
    """Render ``{ux: 0.0, uy: 0.0}`` as ``"ux=0, uy=0"``.

    ``:g`` strips trailing zeros so ``0.0`` renders as ``0`` and ``5.0``
    as ``5`` — the audit line stays readable while preserving precision
    for non-integer values (``2.5`` stays ``2.5``).
    """
    return ", ".join(f"{k}={v:g}" for k, v in components.items())


def summarize_boundary_conditions(
    bcs: list[BoundaryCondition],
) -> BCSummary:
    """Aggregate a ``BoundaryCondition`` list into a ``BCSummary`` for
    the DOCX § 边界条件 renderer.

    Iteration order is preserved (``rows`` reflects the input order)
    so the engineer reading the DOCX sees the BCs in the same order
    they appear in the source ``bc.yaml`` — important for cross-
    referencing back to the engineer's notes.

    Unknown kinds (anything outside :data:`KNOWN_KINDS`) bucket into
    ``"其他"`` in ``counts_by_kind`` so the renderer's summary line
    stays bounded; the per-row ``kind`` column still shows the raw
    label so the engineer can see the original.
    """
    rows: list[Mapping[str, str]] = []
    counts: dict[str, int] = {}
    units_ordered: list[str] = []
    seen_units: set[str] = set()

    for bc in bcs:
        rows.append(
            MappingProxyType(
                {
                    "name": bc.name,
                    "kind": bc.kind,
                    "target": bc.target,
                    "components": _format_components(bc.components),
                    "unit_system": bc.unit_system.value,
                }
            )
        )
        bucket = bc.kind if bc.kind in KNOWN_KINDS else _OTHER_KIND
        counts[bucket] = counts.get(bucket, 0) + 1
        if bc.unit_system.value not in seen_units:
            seen_units.add(bc.unit_system.value)
            units_ordered.append(bc.unit_system.value)

    return BCSummary(
        rows=tuple(rows),
        counts_by_kind=MappingProxyType(dict(counts)),
        unit_systems=tuple(units_ordered),
    )
