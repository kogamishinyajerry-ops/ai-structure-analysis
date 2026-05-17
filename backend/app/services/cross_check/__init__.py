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
# Phase 20 B — second analytical cross-check (Euler-Bernoulli
# cantilever tip deflection). The ccx-running runner is Phase 21+
# scope; Phase 20 B ships the analytical half + validity envelope.
from .cantilever_beam import (
    CANTILEVER_ASPECT_RATIO_MIN,
    SMALL_DEFLECTION_RATIO_MAX,
    CantileverValidityError,
    assert_slender_beam_envelope,
    compute_analytical_tip_deflection,
)
# Phase 21 A — meshed cross-check runners using Phase 20 C's
# `run_tier2_meshed_pipeline`. The cantilever runner promotes
# cantilever-beam-candidate; the plate-Kirsch runner promotes
# plate-with-hole-candidate (both → tier_2_validated via verdict file).
from .cantilever_runner import (
    CANTILEVER_CROSS_CHECK_TOLERANCE_PCT,
    CantileverCrossCheckResult,
    CantileverCrossCheckVerdict,
    run_cantilever_cross_check,
    write_cantilever_verdict_yaml,
)
from .plate_kirsch import (
    KIRSCH_INFINITE_K,
    PLATE_FINITE_RATIO_MAX,
    KirschValidityError,
    compute_kirsch_peak_stress_pa,
    kirsch_stress_concentration_factor,
)
from .plate_kirsch_runner import (
    PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT,
    PlateKirschCrossCheckResult,
    PlateKirschCrossCheckVerdict,
    run_plate_kirsch_cross_check,
    write_plate_kirsch_verdict_yaml,
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
    "CANTILEVER_ASPECT_RATIO_MIN",
    "SMALL_DEFLECTION_RATIO_MAX",
    "CantileverValidityError",
    "assert_slender_beam_envelope",
    "compute_analytical_tip_deflection",
    # Phase 21 A
    "CANTILEVER_CROSS_CHECK_TOLERANCE_PCT",
    "CantileverCrossCheckResult",
    "CantileverCrossCheckVerdict",
    "run_cantilever_cross_check",
    "write_cantilever_verdict_yaml",
    "KIRSCH_INFINITE_K",
    "PLATE_FINITE_RATIO_MAX",
    "KirschValidityError",
    "compute_kirsch_peak_stress_pa",
    "kirsch_stress_concentration_factor",
    "PLATE_KIRSCH_CROSS_CHECK_TOLERANCE_PCT",
    "PlateKirschCrossCheckResult",
    "PlateKirschCrossCheckVerdict",
    "run_plate_kirsch_cross_check",
    "write_plate_kirsch_verdict_yaml",
]
