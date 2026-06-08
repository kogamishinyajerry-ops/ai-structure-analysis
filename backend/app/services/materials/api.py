"""Materials library API — FM-04a Phase 18 C.

Loader + lookup helpers over ``library.json`` (the JSON SSOT next to
this module). Layer-3 service: pure-functions on parsed JSON, no
network / no caching beyond an in-process lazy load.

Each :class:`Material` carries (id, name, mechanical props, citation).
Materials without a ``reference`` field are refused at load time
(per ADR-025 §3 C:-1 anti-gaming guard — silent property drift would
let the harness present unverified material data as authoritative).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

DEFAULT_LIBRARY_PATH: Final[Path] = (
    Path(__file__).resolve().parent / "library.json"
)
"""Absolute path to the JSON SSOT shipped with this module. Tests and
production code both read from this location; pass an explicit path
to :func:`load_library` to load an alternative."""


class MaterialLibraryError(ValueError):
    """Raised when the SSOT JSON fails validation (missing required
    field, duplicate id, malformed value)."""


class MaterialNotFoundError(KeyError):
    """Raised by :func:`get_material` when the requested id is not in
    the library."""


@dataclass(frozen=True)
class Material:
    """A single library entry.

    Attributes:
        id: kebab-case stable identifier (e.g., ``steel-s355``); never
            renamed without a schema MAJOR bump.
        name: human-readable display label.
        youngs_modulus_pa: Young's modulus in pascals; must be > 0.
        poisson_ratio: dimensionless; must satisfy 0 < ν < 0.5.
        density_kg_m3: mass density in kg/m³; must be > 0.
        yield_stress_pa: yield stress in pascals; optional; when present
            must be > 0.
        ultimate_stress_pa: ultimate tensile stress in pascals;
            optional; when present must be > 0 and ≥ yield_stress_pa.
        reference: citation string identifying the property source
            (textbook / standard / database). Required for every
            entry; loader refuses entries without it.
        plastic_hardening_curve: optional list of
            ``(plastic_strain, true_stress_pa)`` pairs ordered by
            ascending plastic strain (per CalculiX ``*PLASTIC``
            convention). The first row must be ``(0.0, yield_stress)``.
            Phase 20 B: when present, the INP writer emits a
            ``*PLASTIC`` block so ccx promotes to a nonlinear run.
    """

    id: str
    name: str
    youngs_modulus_pa: float
    poisson_ratio: float
    density_kg_m3: float
    yield_stress_pa: Optional[float]
    ultimate_stress_pa: Optional[float]
    reference: str
    plastic_hardening_curve: Optional[tuple[tuple[float, float], ...]] = None


def _validate_entry(entry: dict, *, index: int) -> Material:
    """Convert a JSON dict to a validated :class:`Material`.

    Args:
        entry: a single material dict from ``library.json``.
        index: 0-based position in the input list (for error messages).

    Returns:
        A :class:`Material` instance.

    Raises:
        MaterialLibraryError: on any validation failure.
    """
    required = {
        "id",
        "name",
        "youngs_modulus_pa",
        "poisson_ratio",
        "density_kg_m3",
        "reference",
    }
    missing = required - entry.keys()
    if missing:
        raise MaterialLibraryError(
            f"material entry #{index} is missing required field(s) "
            f"{sorted(missing)!r}"
        )
    mid = entry["id"]
    if not isinstance(mid, str) or not mid:
        raise MaterialLibraryError(
            f"material entry #{index} has invalid id {mid!r}"
        )
    reference = entry["reference"]
    if not isinstance(reference, str) or not reference.strip():
        raise MaterialLibraryError(
            f"material {mid!r} (#{index}) has empty/missing reference "
            f"field; every entry must cite a property source per "
            f"ADR-025 §3"
        )
    e_pa = float(entry["youngs_modulus_pa"])
    if e_pa <= 0:
        raise MaterialLibraryError(
            f"material {mid!r} (#{index}) youngs_modulus_pa must be "
            f"positive; got {e_pa}"
        )
    nu = float(entry["poisson_ratio"])
    if not (0.0 < nu < 0.5):
        raise MaterialLibraryError(
            f"material {mid!r} (#{index}) poisson_ratio must be in "
            f"(0, 0.5); got {nu}"
        )
    rho = float(entry["density_kg_m3"])
    if rho <= 0:
        raise MaterialLibraryError(
            f"material {mid!r} (#{index}) density_kg_m3 must be "
            f"positive; got {rho}"
        )
    sigma_y: Optional[float] = None
    if entry.get("yield_stress_pa") is not None:
        sigma_y = float(entry["yield_stress_pa"])
        if sigma_y <= 0:
            raise MaterialLibraryError(
                f"material {mid!r} (#{index}) yield_stress_pa must be "
                f"positive when present; got {sigma_y}"
            )
    sigma_u: Optional[float] = None
    if entry.get("ultimate_stress_pa") is not None:
        sigma_u = float(entry["ultimate_stress_pa"])
        if sigma_u <= 0:
            raise MaterialLibraryError(
                f"material {mid!r} (#{index}) ultimate_stress_pa must "
                f"be positive when present; got {sigma_u}"
            )
        if sigma_y is not None and sigma_u < sigma_y:
            raise MaterialLibraryError(
                f"material {mid!r} (#{index}) ultimate_stress_pa "
                f"({sigma_u}) must be >= yield_stress_pa ({sigma_y})"
            )
    # Phase 20 B — optional plastic hardening curve.
    hardening_curve: Optional[tuple[tuple[float, float], ...]] = None
    raw_curve = entry.get("plastic_hardening_curve")
    if raw_curve is not None:
        if sigma_y is None:
            raise MaterialLibraryError(
                f"material {mid!r} (#{index}) declares "
                f"plastic_hardening_curve but has no yield_stress_pa; "
                f"the curve's first row anchors at yield, so the "
                f"yield must be defined"
            )
        if not isinstance(raw_curve, list) or len(raw_curve) < 2:
            raise MaterialLibraryError(
                f"material {mid!r} (#{index}) plastic_hardening_curve "
                f"must be a list of >=2 [plastic_strain, stress] pairs"
            )
        validated_pairs: list[tuple[float, float]] = []
        prev_strain: Optional[float] = None
        for pair_idx, pair in enumerate(raw_curve):
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not all(isinstance(v, (int, float)) for v in pair)
            ):
                raise MaterialLibraryError(
                    f"material {mid!r} (#{index}) "
                    f"plastic_hardening_curve row {pair_idx} must be "
                    f"a 2-element [strain, stress] numeric pair; got "
                    f"{pair!r}"
                )
            strain = float(pair[0])
            stress = float(pair[1])
            if strain < 0:
                raise MaterialLibraryError(
                    f"material {mid!r} (#{index}) "
                    f"plastic_hardening_curve row {pair_idx} has "
                    f"negative plastic_strain {strain}; CalculiX "
                    f"*PLASTIC requires non-negative strains"
                )
            if stress <= 0:
                raise MaterialLibraryError(
                    f"material {mid!r} (#{index}) "
                    f"plastic_hardening_curve row {pair_idx} has "
                    f"non-positive stress {stress}"
                )
            if prev_strain is not None and strain <= prev_strain:
                raise MaterialLibraryError(
                    f"material {mid!r} (#{index}) "
                    f"plastic_hardening_curve plastic strains must be "
                    f"strictly increasing; row {pair_idx} strain "
                    f"{strain} <= row {pair_idx - 1} strain "
                    f"{prev_strain}"
                )
            prev_strain = strain
            validated_pairs.append((strain, stress))
        if validated_pairs[0][0] != 0.0:
            raise MaterialLibraryError(
                f"material {mid!r} (#{index}) "
                f"plastic_hardening_curve first row must anchor at "
                f"plastic_strain=0.0 (the yield point); got "
                f"{validated_pairs[0][0]}"
            )
        if abs(validated_pairs[0][1] - sigma_y) > 1.0:
            # 1 Pa tolerance covers JSON float round-trip noise.
            raise MaterialLibraryError(
                f"material {mid!r} (#{index}) "
                f"plastic_hardening_curve first row stress "
                f"({validated_pairs[0][1]} Pa) must equal "
                f"yield_stress_pa ({sigma_y} Pa)"
            )
        hardening_curve = tuple(validated_pairs)
    return Material(
        id=mid,
        name=str(entry["name"]),
        youngs_modulus_pa=e_pa,
        poisson_ratio=nu,
        density_kg_m3=rho,
        yield_stress_pa=sigma_y,
        ultimate_stress_pa=sigma_u,
        reference=reference.strip(),
        plastic_hardening_curve=hardening_curve,
    )


def load_library(path: Path = DEFAULT_LIBRARY_PATH) -> tuple[Material, ...]:
    """Parse + validate the materials library JSON at ``path``.

    Returns a frozen tuple of validated :class:`Material` entries in
    file order. Raises :class:`MaterialLibraryError` on any structural
    or value problem (missing field, duplicate id, invalid range).
    """
    if not path.is_file():
        raise MaterialLibraryError(
            f"materials library JSON not found at {path!s}"
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MaterialLibraryError(
            f"materials library JSON at {path!s} is malformed: {exc}"
        ) from exc
    if not isinstance(raw, dict) or "materials" not in raw:
        raise MaterialLibraryError(
            f"materials library JSON at {path!s} missing top-level "
            f"'materials' list"
        )
    entries = raw["materials"]
    if not isinstance(entries, list):
        raise MaterialLibraryError(
            f"materials library JSON at {path!s} 'materials' must be "
            f"a list; got {type(entries).__name__}"
        )
    materials: list[Material] = []
    seen_ids: set[str] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise MaterialLibraryError(
                f"materials library entry #{idx} is not a dict; got "
                f"{type(entry).__name__}"
            )
        mat = _validate_entry(entry, index=idx)
        if mat.id in seen_ids:
            raise MaterialLibraryError(
                f"duplicate material id {mat.id!r} at entry #{idx}"
            )
        seen_ids.add(mat.id)
        materials.append(mat)
    return tuple(materials)


def list_materials(
    path: Path = DEFAULT_LIBRARY_PATH,
) -> tuple[Material, ...]:
    """Return the full library as a frozen tuple in file order."""
    return load_library(path)


def get_material(
    material_id: str,
    *,
    path: Path = DEFAULT_LIBRARY_PATH,
) -> Material:
    """Look up a material by id.

    Raises:
        MaterialNotFoundError: if ``material_id`` is not in the library.
    """
    for mat in load_library(path):
        if mat.id == material_id:
            return mat
    raise MaterialNotFoundError(
        f"no material with id {material_id!r} in library {path!s}"
    )
