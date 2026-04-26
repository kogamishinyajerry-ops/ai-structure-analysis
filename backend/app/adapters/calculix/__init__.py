"""CalculiX (.frd) Layer-1 adapter — RFC-001 §4.5 W2.

Lands the first concrete ``ReaderHandle`` implementation per
``docs/RFC-001-strategic-pivot-and-mvp.md`` §6.4 W2 done-criterion:
GS-001 σ_max within 5 % of the analytical solution.

ADR-001/003/004 enforced: no derived quantities, no UNIT inference,
no IO caching at this layer.
"""

from .reader import CalculiXReader

__all__ = ["CalculiXReader"]
