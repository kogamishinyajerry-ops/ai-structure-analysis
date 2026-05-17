"""Analytical cross-check services — FM-04a Phase 19 B.

Cross-checks compare a real ccx solver result against an independent
analytical solution to substantiate a ``tier_2_validated`` claim
(per ADR-025 §2). The Phase 19 B cohort starts with one cross-check
implementation (thin-walled cylinder hoop stress via Lame); future
phases extend with beam-deflection, plate-bending, modal-frequency
analytical companions.

A cross-check produces a :class:`CrossCheckResult` carrying
``verdict in {"PASS", "FAIL"}`` + residual percentage + the analytical
value + the observed value + provenance. Verdicts are written to disk
(``golden_samples/<case_id>/cross_check_verdict.yaml``) so the
``CLAIM_TIER_REGISTRY`` can lift the case to ``tier_2_validated``
at module-load time without re-running the solver every import.
"""

from .cylinder_hoop import (
    CROSS_CHECK_TOLERANCE_PCT,
    CYLINDER_THIN_WALL_RATIO_MAX,
    CylinderHoopValidityError,
    compute_analytical_hoop_stress_pa,
)
from .cylinder_pv_runner import (
    CrossCheckResult,
    CrossCheckVerdict,
    VERDICT_YAML_FILENAME,
    load_verdict_yaml,
    run_cylinder_pv_cross_check,
    write_verdict_yaml,
)

__all__ = [
    "CROSS_CHECK_TOLERANCE_PCT",
    "CYLINDER_THIN_WALL_RATIO_MAX",
    "CylinderHoopValidityError",
    "compute_analytical_hoop_stress_pa",
    "CrossCheckResult",
    "CrossCheckVerdict",
    "VERDICT_YAML_FILENAME",
    "load_verdict_yaml",
    "run_cylinder_pv_cross_check",
    "write_verdict_yaml",
]
