"""SurrogateProvider abstract base + placeholder implementation (P1-07).

Per ADR-002, CalculiX is the only numerical truth source. The surrogate
provides hints only — never validation.

Architecture:

    SurrogateProvider (ABC)
    ├── PlaceholderSurrogate     — closed-form analytical hints, used as
    │                              the default until a real ML model is
    │                              registered. Always produces LOW confidence.
    └── (future) FNOSurrogate, DeepONetSurrogate, MLPSurrogate, ...

Real ML providers (FNO via `neuralop`, DeepONet via custom torch impl,
etc.) implement the same interface. The pipeline only knows about the
abstract class; provider selection is a config concern.

This module ships with PlaceholderSurrogate only. ML-backed providers
are follow-up PRs that pull in `torch` / `neuralop` as optional deps.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from schemas.surrogate_hint import HintConfidence, HintQuantity, SurrogateHint


class SurrogateProvider(ABC):
    """Abstract surrogate hint provider."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Identifier for this provider, e.g. 'fno-2d@v1'."""

    @abstractmethod
    def predict(self, sim_spec: dict[str, Any]) -> SurrogateHint:
        """Produce an informational hint for the given simulation spec.

        `sim_spec` is treated as a plain dict to keep the provider
        framework-agnostic (no SimPlan import; providers may run in
        a separate process). Required keys depend on provider; the
        contract is documented per provider.
        """


class PlaceholderSurrogate(SurrogateProvider):
    """Closed-form analytical surrogate — uses textbook formulas as hint source.

    Limited to the specific cases the project has theory scripts for
    (see golden_samples/<id>/*_theory.py). For unknown cases, returns
    an empty hint with a note.

    This exists so the pipeline has a working surrogate plug-in from
    day one without pulling torch/neuralop. ML-backed providers
    replace this in production deployments.
    """

    @property
    def provider_id(self) -> str:
        return "placeholder-analytical@v0"

    def predict(self, sim_spec: dict[str, Any]) -> SurrogateHint:
        case_id = str(sim_spec.get("case_id", "UNKNOWN"))
        case_type = str(sim_spec.get("structure_type") or sim_spec.get("beam_type") or "")

        quantities: list[HintQuantity] = []
        notes = ""

        if case_type == "cantilever":
            # Euler-Bernoulli closed form: δ = PL³/(3EI)
            try:
                p = float(sim_spec.get("load_N", 0))
                length = float(sim_spec.get("length_mm", 0))
                e_modulus = float(sim_spec.get("E_MPa", 0))
                inertia = float(sim_spec.get("I_mm4", 0))
                if all(v > 0 for v in (p, length, e_modulus, inertia)):
                    delta = p * length**3 / (3.0 * e_modulus * inertia)
                    quantities.append(
                        HintQuantity(
                            name="max_displacement",
                            value=round(delta, 6),
                            unit="mm",
                            location="free_end",
                            confidence=HintConfidence.LOW,
                        )
                    )
                else:
                    notes = "missing one or more of (load_N, length_mm, E_MPa, I_mm4)"
            except (TypeError, ValueError) as e:
                notes = f"input parsing failed: {e}"
        elif case_type == "":
            notes = "no `structure_type` or `beam_type` in sim_spec — placeholder cannot infer case"
        else:
            notes = (
                f"case_type={case_type!r} not handled by placeholder surrogate; "
                "register a real ML provider to handle this case"
            )

        return SurrogateHint(
            case_id=case_id,
            provider=self.provider_id,
            quantities=quantities,
            notes=notes,
        )


def default_provider() -> SurrogateProvider:
    """Return the active default provider.

    Currently PlaceholderSurrogate; a real ML provider can replace
    this once registered (via env var or config). Single source of
    truth for "which surrogate is currently active."
    """
    return PlaceholderSurrogate()


def hint_to_prompt_context(hint: SurrogateHint) -> str:
    """Convenience wrapper for the architect/solver prompt assembly."""
    return hint.to_prompt_block()
