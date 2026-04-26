"""Unit-aware scalar / array container — RFC-001 §4.3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

    QuantityValue = Union[float, "npt.NDArray[np.float64]"]
else:
    QuantityValue = object  # runtime placeholder; real type checked statically


@dataclass(frozen=True)
class Quantity:
    """A value paired with its unit string.

    Conversion is delegated to Layer 3 (``app.domain.units``); this class
    is purely a data carrier. Defining ``to`` here would couple Layer 2
    to a unit-conversion implementation, violating §4.2 layer rules.
    """

    value: QuantityValue
    unit: str

    def to(self, unit: str) -> "Quantity":
        """Convert into a new unit. Implementation lives in Layer 3.

        Calling this on Layer 2 is a programmer error; the domain layer
        wires the actual conversion via a registered converter.
        """
        raise NotImplementedError(
            "Quantity.to is implemented in app.domain.units (Layer 3)."
        )
