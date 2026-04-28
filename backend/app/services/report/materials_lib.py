"""Built-in material library + free-input material loader (RFC-001
W6a / ADR-019).

The library lives at ``backend/app/data/materials.json`` and is
intentionally a JSON file, not a Python module: the eventual
maintainers are mechanical engineers (RFC-001 §3 seed users), not
Python programmers, and a JSON file is auditable by them.

Two entry points:

* :func:`lookup_builtin` — pick a built-in by ``code_grade``
  (e.g. ``"Q345B"``). Returns ``None`` if not found.
* :func:`load_user_supplied_json` — load a free-input material from a
  user-supplied JSON file. The returned :class:`Material` carries
  ``is_user_supplied=True`` so the DOCX renderer flags it.

Schema (per ADR-019 §6 frozen list):

.. code-block:: json

   {
     "code_grade": "Q345B",
     "code_standard": "GB",
     "youngs_modulus": 206000,
     "poissons_ratio": 0.30,
     "yield_strength": 345,
     "ultimate_strength": 470,
     "density": 7.85e-9,
     "source_citation": "GB/T 1591-2018 §6.2 Table 7"
   }

The ``materials.json`` library wraps these entries under a top-level
``materials`` key plus metadata. ``load_user_supplied_json`` accepts
a single bare entry **or** the wrapped form (so an engineer can
copy-paste a built-in row, edit it, and feed the same shape).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.core.types import Material, UnitSystem


__all__ = [
    "MaterialLookupError",
    "load_builtin_library",
    "lookup_builtin",
    "load_user_supplied_json",
    "BUILTIN_LIBRARY_PATH",
]


# Repo-root-anchored — beats __file__-relative because the package may
# be installed via ``pip install -e .`` and we want the same library
# either way. ``app/data/`` is the package's data dir per ADR-019.
BUILTIN_LIBRARY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "materials.json"
)


_REQUIRED_FIELDS: tuple[str, ...] = (
    "code_grade",
    "code_standard",
    "youngs_modulus",
    "poissons_ratio",
    "yield_strength",
    "ultimate_strength",
    "source_citation",
)


class MaterialLookupError(ValueError):
    """Raised on malformed JSON, missing fields, or invalid numeric
    values. The CLI surfaces this as exit code 4 so the engineer sees
    a precise validation message instead of a generic crash."""


def _validate_entry(entry: Mapping[str, Any], *, source_label: str) -> None:
    """Reject entries missing required fields or carrying non-finite
    numerics. ``source_label`` is the path / library name that scopes
    the error message."""
    missing = [f for f in _REQUIRED_FIELDS if f not in entry]
    if missing:
        raise MaterialLookupError(
            f"{source_label}: material entry is missing required field(s) "
            f"{missing!r}; required = {list(_REQUIRED_FIELDS)!r}"
        )
    for fld in (
        "youngs_modulus",
        "poissons_ratio",
        "yield_strength",
        "ultimate_strength",
    ):
        v = entry[fld]
        if not isinstance(v, (int, float)) or v != v or v <= 0:  # NaN check + positivity
            raise MaterialLookupError(
                f"{source_label}: field {fld!r} must be a positive finite "
                f"number; got {v!r}"
            )
    # ν ∈ (0, 0.5) for physical solids; reject obvious garbage.
    nu = entry["poissons_ratio"]
    if not (0 < nu < 0.5):
        raise MaterialLookupError(
            f"{source_label}: poissons_ratio must be in (0, 0.5); got {nu!r}"
        )
    if entry["code_standard"] not in ("GB", "ASME", "EN"):
        raise MaterialLookupError(
            f"{source_label}: code_standard must be one of "
            f"{{'GB','ASME','EN'}}; got {entry['code_standard']!r}"
        )


def _entry_to_material(
    entry: Mapping[str, Any],
    *,
    is_user_supplied: bool,
) -> Material:
    """Convert a validated dict entry to an immutable :class:`Material`."""
    return Material(
        # ``name`` is the human-readable label; default to code_grade
        # when an explicit ``name`` isn't provided. Built-in entries
        # carry ``display_name_zh``; we route that into ``name`` so the
        # DOCX renderer has a Chinese label to show.
        name=str(
            entry.get("display_name_zh")
            or entry.get("name")
            or entry["code_grade"]
        ),
        youngs_modulus=float(entry["youngs_modulus"]),
        poissons_ratio=float(entry["poissons_ratio"]),
        density=(
            float(entry["density"]) if entry.get("density") is not None else None
        ),
        yield_strength=float(entry["yield_strength"]),
        ultimate_strength=float(entry["ultimate_strength"]),
        code_standard=str(entry["code_standard"]),
        code_grade=str(entry["code_grade"]),
        source_citation=str(entry["source_citation"]),
        unit_system=UnitSystem.SI_MM,
        is_user_supplied=is_user_supplied,
    )


def load_builtin_library(
    library_path: Path | None = None,
) -> dict[str, Material]:
    """Load the bundled material library and return a dict keyed by
    ``code_grade``. Cached at module level for the common case (single
    library path); pass an explicit ``library_path`` to bypass the cache
    in tests.

    Raises :class:`MaterialLookupError` on malformed JSON or invalid
    entries — fail-fast at startup is preferable to silently rendering
    a broken library.
    """
    path = library_path or BUILTIN_LIBRARY_PATH
    if path == BUILTIN_LIBRARY_PATH and _BUILTIN_CACHE:
        return _BUILTIN_CACHE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MaterialLookupError(
            f"built-in material library missing at {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise MaterialLookupError(
            f"built-in material library {path} is not valid JSON: {exc}"
        ) from exc

    entries: Iterable[Mapping[str, Any]] = raw.get("materials", [])
    out: dict[str, Material] = {}
    for entry in entries:
        _validate_entry(entry, source_label=str(path))
        mat = _entry_to_material(entry, is_user_supplied=False)
        if mat.code_grade in out:
            raise MaterialLookupError(
                f"built-in material library {path}: duplicate code_grade "
                f"{mat.code_grade!r}"
            )
        out[mat.code_grade] = mat
    if path == BUILTIN_LIBRARY_PATH:
        _BUILTIN_CACHE.update(out)
    return out


_BUILTIN_CACHE: dict[str, Material] = {}


def lookup_builtin(code_grade: str) -> Material | None:
    """Return the built-in material with the given ``code_grade`` or
    ``None`` if not in the library. Case-sensitive — ``Q345B`` is
    distinct from ``q345b`` because the standards-citation values are
    keyed off the literal grade designation."""
    return load_builtin_library().get(code_grade)


def list_builtin_grades() -> list[str]:
    """Return all built-in code grades. Used by the Electron renderer
    to populate its dropdown without re-parsing the JSON itself."""
    return sorted(load_builtin_library().keys())


def load_user_supplied_json(path: Path) -> Material:
    """Load a free-input material from a user-supplied JSON file.

    Accepts both bare-entry shape and the wrapped library shape (with
    a single entry under ``materials``). Returns a :class:`Material`
    flagged ``is_user_supplied=True`` so the DOCX renderer attaches a
    ``[需工程师确认]`` caveat (RFC-001 §2.4 rule 4).

    Why allow both shapes: an engineer maintaining their own
    institute-specific library should be able to copy-paste either form.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MaterialLookupError(
            f"user-supplied material JSON missing at {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise MaterialLookupError(
            f"user-supplied material JSON {path} is not valid JSON: {exc}"
        ) from exc

    entry: Mapping[str, Any]
    if isinstance(raw, dict) and "materials" in raw:
        materials = raw["materials"]
        if not isinstance(materials, list) or len(materials) != 1:
            raise MaterialLookupError(
                f"user-supplied material JSON {path}: when using the "
                f"wrapped 'materials' shape, exactly one entry is required "
                f"(found {len(materials) if isinstance(materials, list) else 'non-list'})"
            )
        entry = materials[0]
    elif isinstance(raw, dict):
        entry = raw
    else:
        raise MaterialLookupError(
            f"user-supplied material JSON {path}: top-level must be an "
            f"object (bare entry or {{'materials': [...]}}); got "
            f"{type(raw).__name__}"
        )

    _validate_entry(entry, source_label=str(path))
    return _entry_to_material(entry, is_user_supplied=True)
