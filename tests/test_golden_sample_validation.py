"""P1-03 Golden-Sample theory-vs-FEA validation.

ADR-008 N-1: the 5% Golden-Sample accuracy threshold lives here, not in
P1-02. P1-02 only proves the real toolchain produces an FRD honestly;
P1-03 is the physics gate.

This test runs CalculiX on the canonical GS-001 cantilever deck inside
the P1-01 container image, parses the FRD, and asserts every metric in
the ``validation_refs_v2`` block is within its ``tolerance_pct``
(default 5%).

Regression sanity: the shear-locked ``gs001_c3d8_shearlock.inp`` deck is
ALSO run through the validator and must FAIL. That protects us against
silently "fixing" GS-001 by relaxing the tolerance — if the broken deck
ever starts passing, something is wrong with the validator itself.

Skipped unless ``AI_FEA_IN_CONTAINER=1`` because the real ccx is only
guaranteed on the P1-01 image.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.golden_sample_validator import validate_frd

IN_CONTAINER = os.getenv("AI_FEA_IN_CONTAINER", "").strip().lower() in {"1", "true", "yes"}
REPO_ROOT = Path(__file__).resolve().parent.parent
GS001_DIR = REPO_ROOT / "golden_samples" / "GS-001"

pytestmark = pytest.mark.skipif(
    not IN_CONTAINER,
    reason="P1-03 golden-sample validation requires the P1-01 container (AI_FEA_IN_CONTAINER=1).",
)


def _run_ccx(inp_name: str, workdir: Path) -> Path:
    ccx = shutil.which("ccx")
    assert ccx, "ccx missing inside container"
    src = GS001_DIR / inp_name
    assert src.exists(), f"Missing deck: {src}"
    shutil.copy2(src, workdir / inp_name)
    jobname = Path(inp_name).stem
    proc = subprocess.run(
        [ccx, "-i", jobname],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (
        f"ccx failed on {inp_name}: rc={proc.returncode}\n"
        f"stdout tail: {(proc.stdout or '')[-500:]}\n"
        f"stderr tail: {(proc.stderr or '')[-500:]}"
    )
    frd = workdir / f"{jobname}.frd"
    assert frd.exists(), f"{jobname}.frd not produced"
    return frd


def _load_refs() -> dict:
    er = json.loads((GS001_DIR / "expected_results.json").read_text(encoding="utf-8"))
    refs = er["validation_refs_v2"]
    return refs


def test_gs001_canonical_deck_passes_theory_5pct(tmp_path):
    """Canonical C3D8I deck must meet every validation_refs_v2 metric ≤5%."""
    refs = _load_refs()
    frd = _run_ccx("gs001.inp", tmp_path)

    result = validate_frd(frd, refs, case_id="GS-001")

    for line in result.summary_lines():
        print(line)

    assert result.passed, (
        "GS-001 canonical deck failed theory-vs-FEA validation.\n"
        + "\n".join(result.summary_lines())
    )


def test_gs001_shearlocked_deck_fails_as_regression_baseline(tmp_path):
    """The legacy C3D8 shear-locked deck MUST fail theory validation.

    If this test ever passes it means either: (a) the validator tolerance
    has been silently relaxed, (b) the shear-locked deck has been
    substituted, or (c) the theory reference is wrong. Any of these is a
    regression we must catch.
    """
    refs = _load_refs()
    frd = _run_ccx("gs001_c3d8_shearlock.inp", tmp_path)

    result = validate_frd(frd, refs, case_id="GS-001-shearlock-baseline")

    for line in result.summary_lines():
        print(line)

    failing = [m for m in result.metrics if not m.passed]
    assert failing, (
        "Regression guard broke: the shear-locked C3D8 deck unexpectedly "
        "passed every theory tolerance. Check validator component indices, "
        "tolerance_pct, and the legacy deck's element type."
    )

    uy_metric = next(
        (m for m in result.metrics if m.metric_id == "free_end_deflection_uy"),
        None,
    )
    assert uy_metric is not None
    assert uy_metric.error_pct < -10.0, (
        f"Expected shear-lock to under-predict free-end deflection by "
        f">10%, got {uy_metric.error_pct:+.2f}%. Deck may have been modified."
    )
