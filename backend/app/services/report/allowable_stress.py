"""Allowable-stress lookup (RFC-001 W6b / ADR-020).

Compute room-temperature allowable stress [σ] from a `Material`'s
σ_y / σ_u plus a design code (GB / ASME). The simplified formulas
land here; the YAML side-files
``backend/app/data/allowable_stress_{gb,asme}.yaml`` carry the
safety factors and clause citations that the formulas need.

Refusals (per ADR-020 §1):

* Cross-standard requests refuse with ``ValueError``: asking for
  ``"GB"`` allowable on an ``"ASME"`` material is a sign-blocker, not
  an auto-cross-reference. The engineer must pick the standard
  explicitly.
* High-temperature requests (T > the YAML's
  ``temperature_range_celsius.max``) refuse with
  ``NotImplementedError``: the simplified path is room-temperature
  only, and silently extrapolating room-T factors to higher T
  produces non-conservative wrong numbers (M4+ work).

The returned ``AllowableStress`` carries full provenance — formula,
clause, inputs — so the W6c DOCX renderer can render it verbatim
without re-deriving anything.

Loaded once at import via :func:`_load_factor_table`; the YAML files
are read-only data and the resulting tables are exposed as immutable
dicts. A test that mutates the loaded dict would break the snapshot
for everything else in the test session — ADR-020 §6 explicitly
disallows it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, Literal

import yaml
from app.core.types import Material

__all__ = [
    "AllowableStress",
    "AllowableStressError",
    "compute_allowable_stress",
    "GB_FACTOR_TABLE",
    "ASME_FACTOR_TABLE",
]


# Anchored at the package data dir, same convention as
# ``materials_lib.BUILTIN_LIBRARY_PATH``.
_DATA_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "data"

_GB_YAML_PATH: Final[Path] = _DATA_DIR / "allowable_stress_gb.yaml"
_ASME_YAML_PATH: Final[Path] = _DATA_DIR / "allowable_stress_asme.yaml"


CodeStandard = Literal["GB", "ASME"]


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AllowableStress:
    """Result of one allowable-stress computation, with provenance.

    Every field is for the DOCX renderer (W6c §"许用应力"):

    * ``sigma_allow`` — the [σ] value, in the same stress unit as
      ``Material.yield_strength`` (MPa for the si-mm convention this
      project uses; the unit is **not** stored here because it must
      match ``material.unit_system`` and re-storing it invites drift).
    * ``code_standard`` — ``"GB"`` or ``"ASME"`` (matches the input
      argument; not the material's standard, in case W6c surfaces a
      cross-standard mode in the future — for now they always agree).
    * ``code_clause`` — verbatim citation string for the DOCX
      footnote.
    * ``formula_used`` — human-readable formula
      (``"min(σ_y / 1.5, σ_u / 3.0)"``), for the DOCX line that shows
      the substitution.
    * ``inputs`` — the actual numbers fed to the formula
      (``{"sigma_y": 345.0, "sigma_u": 470.0,
      "temperature_C": 20.0}``), for the DOCX substitution line.
    * ``is_simplified`` — always ``True`` for W6b; pinned in the
      schema so a future M4+ tabulated-lookup branch can flip it to
      ``False`` without an API break.
    """

    sigma_allow: float
    code_standard: str
    code_clause: str
    formula_used: str
    inputs: Mapping[str, float] = field(default_factory=lambda: MappingProxyType({}))
    is_simplified: bool = True


class AllowableStressError(ValueError):
    """Raised on cross-standard mismatch or malformed factor YAML.

    Subclasses ``ValueError`` so callers can ``except ValueError`` to
    catch both this and the constructor's own argument-validation
    errors. High-T refusal is signalled by ``NotImplementedError``
    instead — that's a "feature not yet built" failure, not a "your
    request is invalid" failure (per ADR-020).
    """


# ---------------------------------------------------------------------------
# YAML loader (called once at import)
# ---------------------------------------------------------------------------


_REQUIRED_TOP_KEYS: Final[tuple[str, ...]] = (
    "formula",
    "temperature_range_celsius",
    "clause_citation",
)
_REQUIRED_FORMULA_KEYS: Final[tuple[str, ...]] = (
    "expression",
    "yield_safety_factor",
    "ultimate_safety_factor",
)


def _deep_freeze(obj: Any) -> Any:
    """Recursively wrap dicts in MappingProxyType and lists in tuples.

    Codex R1 (gpt-5.4 xhigh) demonstrated that wrapping only the top
    level was insufficient — `GB_FACTOR_TABLE["formula"]` remained a
    plain dict and was therefore mutable, so a malicious or buggy
    caller could change `yield_safety_factor` mid-process and silently
    corrupt every subsequent allowable-stress computation. This
    helper walks the loaded YAML tree once at import and freezes
    every nested mapping; lists become tuples; primitives pass
    through unchanged.

    Sets are not expected in this YAML (yaml.safe_load doesn't emit
    them by default) but are converted to ``frozenset`` defensively
    in case a future schema introduces them.
    """
    if isinstance(obj, dict):
        return MappingProxyType({k: _deep_freeze(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return tuple(_deep_freeze(v) for v in obj)
    if isinstance(obj, set):
        return frozenset(_deep_freeze(v) for v in obj)
    return obj


def _load_factor_table(path: Path, *, code_label: str) -> Mapping[str, Any]:
    """Read one allowable-stress YAML and validate the schema fields
    this module actually consumes.

    The YAML carries other fields (``rationale``, ``docx_disclaimers``,
    etc.) that the DOCX layer reads directly; this function does NOT
    enforce their presence — only the keys the formula evaluator
    needs are required here.

    The returned mapping is **deep-frozen** so callers (including the
    DOCX layer) cannot mutate nested formula factors and silently
    corrupt downstream computations.
    """
    if not path.is_file():
        raise AllowableStressError(
            f"{code_label}: allowable-stress data file not found at {path!s}; "
            f"this is a packaging bug (the file ships under "
            f"backend/app/data/)"
        )

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise AllowableStressError(
            f"{code_label}: top-level YAML must be a mapping, got {type(raw).__name__}"
        )

    missing = [k for k in _REQUIRED_TOP_KEYS if k not in raw]
    if missing:
        raise AllowableStressError(
            f"{code_label}: missing required top-level key(s) {missing!r} in {path.name}"
        )

    formula = raw["formula"]
    if not isinstance(formula, dict):
        raise AllowableStressError(
            f"{code_label}: 'formula' must be a mapping, got {type(formula).__name__}"
        )
    f_missing = [k for k in _REQUIRED_FORMULA_KEYS if k not in formula]
    if f_missing:
        raise AllowableStressError(f"{code_label}: missing required 'formula' key(s) {f_missing!r}")

    for fld in ("yield_safety_factor", "ultimate_safety_factor"):
        v = formula[fld]
        if not isinstance(v, (int, float)) or v <= 0:
            raise AllowableStressError(
                f"{code_label}: formula.{fld} must be a positive number, got {v!r}"
            )

    temp = raw["temperature_range_celsius"]
    if (
        not isinstance(temp, dict)
        or not all(k in temp for k in ("min", "max"))
        or not isinstance(temp["min"], (int, float))
        or not isinstance(temp["max"], (int, float))
        or temp["min"] >= temp["max"]
    ):
        raise AllowableStressError(
            f"{code_label}: temperature_range_celsius must be "
            f"{{'min': float, 'max': float}} with min < max, got {temp!r}"
        )

    return _deep_freeze(raw)


GB_FACTOR_TABLE: Final[Mapping[str, Any]] = _load_factor_table(_GB_YAML_PATH, code_label="GB")
ASME_FACTOR_TABLE: Final[Mapping[str, Any]] = _load_factor_table(_ASME_YAML_PATH, code_label="ASME")

_CODE_TABLES: Final[Mapping[str, Mapping[str, Any]]] = MappingProxyType(
    {
        "GB": GB_FACTOR_TABLE,
        "ASME": ASME_FACTOR_TABLE,
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_allowable_stress(
    material: Material,
    code: CodeStandard,
    temperature_C: float = 20.0,
) -> AllowableStress:
    """Compute room-temperature allowable stress [σ] for ``material``
    under ``code`` (``"GB"`` or ``"ASME"``).

    See ADR-020 §1 for refusal contract. Quick reminder:

    * ``code`` must match ``material.code_standard``; cross-standard
      requests raise :class:`AllowableStressError`.
    * ``temperature_C`` must be within the YAML's documented validity
      range; outside that range raises :class:`NotImplementedError`.

    The returned [σ] is in the same stress unit as ``material``'s
    yield/ultimate (typically MPa). Callers must NOT apply weld
    efficiency / load-category multipliers here — those are W6c
    verdict-step decisions per ADR-020 §3 + §"What this does NOT
    decide".
    """
    if code not in _CODE_TABLES:
        raise AllowableStressError(
            f"unknown code standard {code!r}; expected one of {tuple(_CODE_TABLES.keys())!r}"
        )

    if material.code_standard != code:
        raise AllowableStressError(
            f"cross-standard request refused: material "
            f"{material.code_grade!r} has code_standard="
            f"{material.code_standard!r}, but caller requested "
            f"code={code!r}. Per ADR-020 §1 the wedge does not "
            f"auto-cross-reference between standards; the engineer "
            f"must explicitly choose the standard for the material."
        )

    table = _CODE_TABLES[code]
    temp_range = table["temperature_range_celsius"]
    if not (temp_range["min"] <= temperature_C <= temp_range["max"]):
        raise NotImplementedError(
            f"temperature_C={temperature_C} is outside the simplified "
            f"path's validity range "
            f"[{temp_range['min']}, {temp_range['max']}] °C for {code}; "
            f"high-temperature allowable stress requires Table 4 / "
            f"Table 5A lookup, which is M4+ work (per ADR-020 §"
            f'"What this does NOT decide").'
        )

    formula = table["formula"]
    n_s: float = float(formula["yield_safety_factor"])
    n_b: float = float(formula["ultimate_safety_factor"])

    # Defensive: Material is `frozen=True` and validated upstream by
    # ADR-019's loader, but if a hand-built Material slips in with a
    # non-positive σ_y / σ_u the formula returns a meaningless
    # negative or zero [σ]. Cleaner to fail loudly at the boundary.
    if material.yield_strength <= 0 or material.ultimate_strength <= 0:
        raise AllowableStressError(
            f"material {material.code_grade!r} has non-positive "
            f"yield_strength={material.yield_strength} or "
            f"ultimate_strength={material.ultimate_strength}; cannot "
            f"compute allowable stress"
        )

    sigma_allow = min(
        material.yield_strength / n_s,
        material.ultimate_strength / n_b,
    )

    inputs = MappingProxyType(
        {
            "sigma_y": float(material.yield_strength),
            "sigma_u": float(material.ultimate_strength),
            "temperature_C": float(temperature_C),
        }
    )

    return AllowableStress(
        sigma_allow=sigma_allow,
        code_standard=code,
        code_clause=str(table["clause_citation"]),
        formula_used=str(formula["expression"]),
        inputs=inputs,
        is_simplified=True,
    )
