"""SimPlan → SurrogateProvider input dict adapter (P1-07 follow-up).

Translates a canonical SimPlan into the loosely-typed dict shape that
`SurrogateProvider.predict()` consumes. Handles unit conversion (Pa→MPa,
m→mm) so closed-form / ML surrogates can use the same input schema as
the textbook formulas in `golden_samples/<id>/*_theory.py`.

This module deliberately does NOT modify any agent. Callers (architect,
geometry, mesh, solver) opt in by calling `simplan_to_sim_spec(plan)`
and threading the result into `SurrogateProvider.predict()`.

Design choice — units in mm-N-MPa:

  PlaceholderSurrogate uses the same closed-form formula as the GS
  theory scripts (Euler-Bernoulli δ = PL³/(3EI)). Those scripts use
  mm-N-MPa for solid mechanics. SimPlan canonically stores SI
  (m/Pa/N), so the adapter converts.

  * length_m → length_mm     (×1000)
  * E_pa → E_MPa             (×1e-6)
  * I_m4 → I_mm4             (×1e12)

  Loads are kept in N (no conversion).
"""

from __future__ import annotations

import contextlib
from typing import Any

# Type-only import — avoid circular import at module load time.
try:
    from schemas.sim_plan import SimPlan
except ImportError:  # pragma: no cover — schemas[dev] required at runtime
    SimPlan = None  # type: ignore[assignment]

PA_TO_MPA = 1e-6
M_TO_MM = 1e3
M4_TO_MM4 = 1e12


def _infer_beam_type(plan: Any) -> str | None:
    """Pick a surrogate-recognized case type from SimPlan geometry.

    Recognized: 'cantilever' (Euler-Bernoulli closed-form is available).
    Future surrogates can add 'truss', 'plane_stress', etc.
    """
    geom = getattr(plan, "geometry", None)
    if geom is None:
        return None

    # Try the structural-style ref first.
    ref = (getattr(geom, "ref", "") or "").lower()
    if "cantilever" in ref:
        return "cantilever"

    # Fall back to params hints.
    params = getattr(geom, "params", None) or {}
    kind_hint = str(params.get("kind") or params.get("structure_type") or "").lower()
    if "cantilever" in kind_hint:
        return "cantilever"

    # Some legacy plans use `kind` property on GeometrySpec.
    kind = (getattr(geom, "kind", "") or "").lower()
    if "cantilever" in kind:
        return "cantilever"

    return None


def _extract_length_mm(plan: Any) -> float | None:
    """Return beam length in mm, or None if not parseable."""
    params = getattr(plan.geometry, "params", None) or {}
    for key, in_unit in (("length_m", "m"), ("length_mm", "mm"), ("length", "m"), ("L", "m")):
        if key in params:
            try:
                v = float(params[key])
            except (TypeError, ValueError):
                continue
            if in_unit == "m":
                return v * M_TO_MM
            return v
    return None


def _extract_inertia_mm4(plan: Any) -> float | None:
    """Return cross-section second moment of area in mm⁴."""
    params = getattr(plan.geometry, "params", None) or {}
    for key, in_unit in (("I_m4", "m4"), ("I_mm4", "mm4"), ("I", "m4"), ("inertia", "m4")):
        if key in params:
            try:
                v = float(params[key])
            except (TypeError, ValueError):
                continue
            if in_unit == "m4":
                return v * M4_TO_MM4
            return v
    return None


def _extract_load_N(plan: Any) -> float | None:
    """Return scalar tip-load magnitude in N.

    Picks the first load with `magnitude` set; component sums are not
    inferred (would conflate axial vs lateral). If no scalar load is
    present, returns None.
    """
    loads = getattr(plan, "loads", None) or []
    for load in loads:
        magnitude = getattr(load, "magnitude", None)
        if magnitude is not None:
            try:
                return float(magnitude)
            except (TypeError, ValueError):
                continue
    return None


def simplan_to_sim_spec(plan: Any) -> dict[str, Any]:
    """Translate a SimPlan into a SurrogateProvider input dict.

    Returns a dict with keys the PlaceholderSurrogate recognizes
    (case_id, beam_type, load_N, length_mm, E_MPa, I_mm4). Future
    surrogates can read additional keys.

    Missing fields are simply omitted; the surrogate will return an
    empty hint with a diagnostic note (see PlaceholderSurrogate.predict).
    """
    if plan is None:
        return {}

    spec: dict[str, Any] = {
        "case_id": getattr(plan, "case_id", "UNKNOWN"),
    }

    beam_type = _infer_beam_type(plan)
    if beam_type:
        spec["beam_type"] = beam_type

    material = getattr(plan, "material", None)
    if material is not None:
        e_pa = getattr(material, "youngs_modulus_pa", None)
        if e_pa is not None:
            with contextlib.suppress(TypeError, ValueError):
                spec["E_MPa"] = float(e_pa) * PA_TO_MPA

    length_mm = _extract_length_mm(plan)
    if length_mm is not None:
        spec["length_mm"] = length_mm

    inertia_mm4 = _extract_inertia_mm4(plan)
    if inertia_mm4 is not None:
        spec["I_mm4"] = inertia_mm4

    load_N = _extract_load_N(plan)
    if load_N is not None:
        spec["load_N"] = load_N

    return spec


def predict_for_simplan(plan: Any) -> Any:
    """Convenience: call default_provider().predict() on a SimPlan directly.

    Returns a SurrogateHint. Provided so callers can do one-liner
    integration:

        from agents.surrogate_adapter import predict_for_simplan
        hint = predict_for_simplan(plan)
        prompt += hint.to_prompt_block()
    """
    from agents.surrogate import default_provider

    spec = simplan_to_sim_spec(plan)
    return default_provider().predict(spec)
