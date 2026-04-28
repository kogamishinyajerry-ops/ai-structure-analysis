"""Verdict tests — RFC-001 W6c / ADR-020 §"What this does NOT decide".

Test buckets:

1. PASS / FAIL by SF vs threshold (with boundary at threshold)
2. Threshold parameter (default 1.0, custom 1.5)
3. Margin percent calculation (positive / negative / zero)
4. Refusal contract (NaN / inf / zero / negative on every input)
5. Inputs tuple shape + immutability
"""

from __future__ import annotations

import math

import pytest
from app.services.report.verdict import (
    DEFAULT_THRESHOLD,
    compute_verdict,
)

# ---------------------------------------------------------------------------
# Bucket 1 — PASS / FAIL by SF vs threshold
# ---------------------------------------------------------------------------


def test_pass_when_sigma_allow_well_above_sigma_max() -> None:
    """SF=4.6 (the GS-001 demo case from the W6 roadmap §2 W6c
    end-state) — comfortably PASS at default threshold."""
    res = compute_verdict(sigma_max=50.0, sigma_allow=230.0)

    assert res.kind == "PASS"
    assert math.isclose(res.safety_factor, 4.6, rel_tol=1e-9)


def test_fail_when_sigma_max_exceeds_sigma_allow() -> None:
    res = compute_verdict(sigma_max=200.0, sigma_allow=150.0)

    assert res.kind == "FAIL"
    assert math.isclose(res.safety_factor, 0.75, rel_tol=1e-9)


def test_pass_at_exact_threshold_boundary() -> None:
    """SF == threshold counts as PASS, per the docstring contract
    (regulatory floor is inclusive at 1.0). The boundary is the
    most likely off-by-one in production — a strict ``>`` here
    would silently flip a marginal-but-acceptable design to FAIL."""
    res = compute_verdict(sigma_max=100.0, sigma_allow=100.0, threshold=1.0)

    assert res.kind == "PASS"
    assert math.isclose(res.safety_factor, 1.0, rel_tol=1e-12)
    assert math.isclose(res.margin_pct, 0.0, abs_tol=1e-12)


def test_fail_just_below_threshold() -> None:
    """SF = 0.9999... (one ulp below 1.0) must FAIL."""
    res = compute_verdict(sigma_max=100.0, sigma_allow=99.9999, threshold=1.0)

    assert res.kind == "FAIL"


# ---------------------------------------------------------------------------
# Bucket 2 — threshold parameter
# ---------------------------------------------------------------------------


def test_default_threshold_is_one() -> None:
    assert DEFAULT_THRESHOLD == 1.0


def test_custom_threshold_flips_marginal_to_fail() -> None:
    """SF=1.2 PASS at threshold=1.0, FAIL at threshold=1.5
    (institute-internal extra margin)."""
    res_default = compute_verdict(sigma_max=100.0, sigma_allow=120.0, threshold=1.0)
    res_strict = compute_verdict(sigma_max=100.0, sigma_allow=120.0, threshold=1.5)

    assert res_default.kind == "PASS"
    assert res_strict.kind == "FAIL"
    # Same SF either way — only the verdict flips with the threshold
    assert math.isclose(res_default.safety_factor, res_strict.safety_factor)


# ---------------------------------------------------------------------------
# Bucket 3 — margin percent
# ---------------------------------------------------------------------------


def test_margin_pct_positive_when_above_threshold() -> None:
    """SF=2.0 against threshold=1.0 → margin = (2.0/1.0 - 1)*100 = 100%."""
    res = compute_verdict(sigma_max=50.0, sigma_allow=100.0, threshold=1.0)

    assert math.isclose(res.margin_pct, 100.0, rel_tol=1e-9)


def test_margin_pct_negative_when_below_threshold() -> None:
    """SF=0.5 against threshold=1.0 → margin = (0.5/1.0 - 1)*100 = -50%."""
    res = compute_verdict(sigma_max=200.0, sigma_allow=100.0, threshold=1.0)

    assert math.isclose(res.margin_pct, -50.0, rel_tol=1e-9)


def test_margin_pct_uses_threshold_not_one() -> None:
    """SF=1.5, threshold=1.5 → margin_pct == 0 (right at the
    institute floor). NOT 50% — that would be (SF-1)*100, which
    measures vs regulatory floor, not the engineer's chosen
    threshold. The engineer sees the percent against THEIR
    decision."""
    res = compute_verdict(sigma_max=100.0, sigma_allow=150.0, threshold=1.5)

    assert math.isclose(res.margin_pct, 0.0, abs_tol=1e-12)


# ---------------------------------------------------------------------------
# Bucket 4 — refusal contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_sigma_max_refuses_non_positive_or_non_finite(bad_value: float) -> None:
    with pytest.raises(ValueError, match="sigma_max"):
        compute_verdict(sigma_max=bad_value, sigma_allow=100.0)


@pytest.mark.parametrize(
    "bad_value",
    [
        0.0,
        -1.0,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_sigma_allow_refuses_non_positive_or_non_finite(
    bad_value: float,
) -> None:
    with pytest.raises(ValueError, match="sigma_allow"):
        compute_verdict(sigma_max=100.0, sigma_allow=bad_value)


@pytest.mark.parametrize(
    "bad_value",
    [
        0.0,
        -1.0,
        0.5,  # below regulatory floor — Codex R1 HIGH on PR #99
        0.999,  # marginally below 1.0 (not an ulp; just close enough to catch
        # an off-by-one in the comparator)
        float("nan"),
        float("inf"),
    ],
)
def test_threshold_refuses_below_regulatory_floor_or_non_finite(
    bad_value: float,
) -> None:
    """The contract floor is 1.0 (GB 150 / ASME VIII Div 2 already
    build SF into [σ]). Codex R1 on PR #99 demonstrated that an
    earlier `> 0` guard let `threshold=0.5` slip through and return
    PASS for SF=0.6 — the stricter `>= 1.0` validator closes that
    audit hole."""
    with pytest.raises(ValueError, match="threshold"):
        compute_verdict(sigma_max=100.0, sigma_allow=200.0, threshold=bad_value)


def test_threshold_at_exactly_one_succeeds() -> None:
    """The boundary is inclusive at 1.0 — exactly the regulatory
    floor. Off-by-one guard."""
    res = compute_verdict(sigma_max=100.0, sigma_allow=200.0, threshold=1.0)
    assert res.kind == "PASS"


def test_threshold_above_one_for_institute_margin_succeeds() -> None:
    """Engineers can pass threshold=1.5 (institute-internal margin).
    No upper bound — a 5x threshold is allowed in principle though
    physically unusual."""
    res_15 = compute_verdict(sigma_max=100.0, sigma_allow=200.0, threshold=1.5)
    res_5 = compute_verdict(sigma_max=100.0, sigma_allow=600.0, threshold=5.0)
    assert res_15.kind == "PASS"
    assert res_5.kind == "PASS"


def test_string_input_refuses() -> None:
    """Catches a caller passing an un-cast str (e.g. raw form input)."""
    with pytest.raises(ValueError, match="must be a real number"):
        compute_verdict(sigma_max="50", sigma_allow=200.0)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Bucket 5 — inputs tuple shape + immutability
# ---------------------------------------------------------------------------


def test_inputs_tuple_has_four_named_pairs() -> None:
    """The DOCX template (W6c.2) substitutes four numbers into the
    句式; the input tuple shape is part of this module's public
    contract."""
    res = compute_verdict(sigma_max=50.0, sigma_allow=230.0, threshold=1.0)

    keys = [k for k, _ in res.inputs]
    assert keys == ["sigma_max", "sigma_allow", "safety_factor", "threshold"]

    inputs_dict = dict(res.inputs)
    assert inputs_dict["sigma_max"] == 50.0
    assert inputs_dict["sigma_allow"] == 230.0
    assert inputs_dict["threshold"] == 1.0
    assert math.isclose(inputs_dict["safety_factor"], 4.6, rel_tol=1e-9)


def test_verdict_is_frozen() -> None:
    """A frozen dataclass — the DOCX renderer must not be able to
    mutate the verdict between extraction and template
    substitution. Catches an accidental ``frozen=False`` regression."""
    from dataclasses import FrozenInstanceError

    res = compute_verdict(sigma_max=50.0, sigma_allow=230.0)

    with pytest.raises(FrozenInstanceError):
        res.kind = "FAIL"  # type: ignore[misc]


def test_inputs_tuple_is_immutable() -> None:
    """Tuples are immutable by construction; pinning here so a
    future change to a list-typed inputs (which would break
    deep-immutability) trips this test."""
    res = compute_verdict(sigma_max=50.0, sigma_allow=230.0)

    assert isinstance(res.inputs, tuple)
    # Each pair is also a tuple, not a list
    for pair in res.inputs:
        assert isinstance(pair, tuple)
        assert len(pair) == 2


# ---------------------------------------------------------------------------
# Integration sanity — Verdict reads cleanly from compute_allowable_stress
# ---------------------------------------------------------------------------


def test_end_to_end_compute_verdict_from_allowable_stress() -> None:
    """The W6c handoff: feed compute_allowable_stress's
    sigma_allow into compute_verdict. This pins the integration
    point so a future change to AllowableStress.sigma_allow's
    type / unit can't silently break the verdict layer."""
    from app.core.types import Material, UnitSystem
    from app.services.report.allowable_stress import compute_allowable_stress

    mat = Material(
        name="Q345B",
        youngs_modulus=206_000.0,
        poissons_ratio=0.30,
        density=7.85e-9,
        yield_strength=345.0,
        ultimate_strength=470.0,
        code_standard="GB",
        code_grade="Q345B",
        source_citation="GB/T 1591-2018 §6.2 Table 7",
        unit_system=UnitSystem.SI_MM,
    )
    allowable = compute_allowable_stress(mat, "GB", temperature_C=20.0)
    # Q345B: min(345/1.5, 470/3.0) ≈ 156.67 MPa
    # Pretend FE found σ_max = 50 MPa → SF ≈ 3.13 → PASS
    res = compute_verdict(sigma_max=50.0, sigma_allow=allowable.sigma_allow)

    assert res.kind == "PASS"
    assert math.isclose(res.safety_factor, 156.67 / 50.0, rel_tol=1e-3)
