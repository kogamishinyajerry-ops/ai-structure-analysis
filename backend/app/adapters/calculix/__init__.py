"""CalculiX (.frd) Layer-1 adapter.

* ``CalculiXReader`` — RFC-001 §4.5 W2 ``ReaderHandle`` over ``.frd``
  result files. ADR-001/003/004 enforced: no derived quantities, no
  UNIT inference, no IO caching at this layer.
* ``CalculiXRunner`` — FM-04a Phase 18 A subprocess runner that
  invokes the real ``ccx`` binary on a ``case_dir/<jobname>.inp``
  and returns paths to the produced ``.frd`` + ``.dat`` artifacts.
  The runner is paired with ``CalculiXReader`` (runner produces the
  ``.frd``; reader parses it).
* ``inp_writer`` — Phase 18 A minimal-hex INP writer for smoke runs.
"""

from .inp_writer import (
    DEFAULT_STEEL,
    MinimalHexMaterial,
    write_minimal_hex_inp,
)
from .reader import CalculiXReader
from .runner import (
    DEFAULT_CCX_BINARY,
    DEFAULT_TIMEOUT_SEC,
    CalculiXRunError,
    CalculiXRunner,
    CalculiXRunResult,
)

__all__ = [
    "CalculiXReader",
    "CalculiXRunner",
    "CalculiXRunResult",
    "CalculiXRunError",
    "DEFAULT_CCX_BINARY",
    "DEFAULT_TIMEOUT_SEC",
    "DEFAULT_STEEL",
    "MinimalHexMaterial",
    "write_minimal_hex_inp",
]
