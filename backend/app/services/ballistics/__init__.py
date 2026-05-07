"""FM-04a candidate-side ballistic metric extraction.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

This module is intentionally separate from ``backend.app.domain.ballistics``:

* ``domain.ballistics`` consumes Layer-2 ReaderHandle objects (real
  OpenRadioss reader output) and derives RFC-001 §6.4 W7d ballistic
  quantities.
* This package writes the FM-04a candidate spine sidecar
  (``ballistic_metrics.json``) from a flat structured input. It does NOT
  parse ``.h3d`` / ``.anim`` / ``.A001`` files; that parser layer is the
  reader-aware tier and remains in ``domain.ballistics``.

Decoupling keeps two concerns explicit:

1. The OpenRadioss reader stack (W7 / W7d / RFC-001 §6.4) is independent
   of the FM-04a candidate spine wiring.
2. The candidate spine sidecar (``backend/app/services/candidate_report_
   spine.py``) reads exactly the shape produced here, so claim-tier
   discipline is preserved end to end.
"""

from .convergence_writers import (
    ConvergenceRun,
    MeshConvergenceInput,
    TimeStepConvergenceInput,
    write_mesh_convergence,
    write_time_step_convergence,
)
from .metric_extraction import (
    BallisticEnergyAudit,
    BallisticExtractionInput,
    BallisticTimeSample,
    write_ballistic_metrics,
)

__all__ = [
    "BallisticEnergyAudit",
    "BallisticExtractionInput",
    "BallisticTimeSample",
    "ConvergenceRun",
    "MeshConvergenceInput",
    "TimeStepConvergenceInput",
    "write_ballistic_metrics",
    "write_mesh_convergence",
    "write_time_step_convergence",
]
