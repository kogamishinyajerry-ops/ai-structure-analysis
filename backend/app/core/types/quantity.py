"""Unit-aware scalar / array container — RFC-001 §4.3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional, Union

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

    QuantityValue = Union[float, "npt.NDArray[np.float64]"]
else:
    QuantityValue = object  # runtime placeholder; real type checked statically


# Registry hook: Layer 3 (``app.domain.units``) installs the actual
# conversion implementation here at import time. We keep ``Quantity``
# itself pure Layer 2 — no Layer 3 import — and use this module-level
# callable as a one-way injection point. ``Quantity.to`` raises
# ``NotImplementedError`` if no converter has been registered.
_TO_CONVERTER: Optional[Callable[["Quantity", str], "Quantity"]] = None


def _register_converter(
    fn: Callable[["Quantity", str], "Quantity"],
) -> None:
    """Install the Layer-3 implementation of :meth:`Quantity.to`.

    Idempotent — re-registering replaces the previous converter, which
    is what test isolation expects.
    """
    global _TO_CONVERTER
    _TO_CONVERTER = fn


def _unregister_converter() -> None:
    """Remove any registered converter (test-only helper)."""
    global _TO_CONVERTER
    _TO_CONVERTER = None


@dataclass(frozen=True)
class Quantity:
    """A value paired with its unit string.

    Conversion is delegated to Layer 3 (``app.domain.units``) via the
    module-level registry above; this class is purely a data carrier.
    Defining the unit-conversion table on the dataclass would couple
    Layer 2 to a Layer-3 implementation, violating §4.2 layer rules.
    """

    value: QuantityValue
    unit: str

    def to(self, unit: str) -> "Quantity":
        """Convert into a new unit. Implementation lives in Layer 3.

        Importing ``app.domain.units`` registers the converter; if that
        package has not been imported in this process, the method raises
        ``NotImplementedError`` rather than silently returning the wrong
        value (ADR-003: no silent assumptions).
        """
        if _TO_CONVERTER is None:
            raise NotImplementedError(
                "Quantity.to() requires app.domain.units to be imported "
                "(it registers the Layer-3 converter on import)."
            )
        return _TO_CONVERTER(self, unit)
