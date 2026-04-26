"""Generate the P1-03 Golden-Sample validation diagnostic report.

Runs CalculiX on the canonical (C3D8I) and legacy (C3D8 shear-lock) GS-001
decks inside the P1-01 container and writes a Markdown report +
JSON artefact into ``runs/run-p1-03-gsv/``. Intended to be run via

    docker run --rm -v "$PWD:/repo" -w /repo -e PYTHONPATH=/repo \
        -e AI_FEA_IN_CONTAINER=1 ai-fea-engine:p1-base \
        python3 scripts/p1_03_generate_report.py

so that the PR reviewer (Kogami) can inspect the produced artefacts
without rerunning the container themselves.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from tools.golden_sample_validator import validate_case_dir

REPO_ROOT = Path(__file__).resolve().parent.parent
GS001_DIR = REPO_ROOT / "golden_samples" / "GS-001"
RUN_ID = "run-p1-03-gsv-gs001"
OUT_DIR = REPO_ROOT / "runs" / RUN_ID


def _run_ccx(inp_name: str, work_root: Path) -> Path:
    ccx = shutil.which("ccx")
    if not ccx:
        raise RuntimeError("ccx not on PATH — run this inside the P1-01 image.")
    work = work_root / Path(inp_name).stem
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy2(GS001_DIR / inp_name, work / inp_name)
    proc = subprocess.run(
        [ccx, "-i", Path(inp_name).stem],
        cwd=work,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ccx failed on {inp_name}: rc={proc.returncode}\n{proc.stdout}\n{proc.stderr}"
        )
    return work / f"{Path(inp_name).stem}.frd"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    work_root = OUT_DIR / "solver"
    work_root.mkdir(parents=True, exist_ok=True)

    canonical_frd = _run_ccx("gs001.inp", work_root)
    legacy_frd = _run_ccx("gs001_c3d8_shearlock.inp", work_root)

    canonical_res = validate_case_dir(GS001_DIR, canonical_frd)
    legacy_res = validate_case_dir(GS001_DIR, legacy_frd)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = {
        "run_id": RUN_ID,
        "generated_at": now,
        "case_id": "GS-001",
        "canonical": canonical_res.to_dict(),
        "legacy_shearlock": legacy_res.to_dict(),
    }
    (OUT_DIR / "validation.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Markdown report
    lines: list[str] = []
    lines.append("# P1-03 Golden-Sample Validation — GS-001 (Cantilever Beam)")
    lines.append("")
    lines.append(f"> Generated: {now}  \\n> Solver: CalculiX 2.20 (P1-01 container)")
    lines.append("")
    lines.append("## 1. Canonical deck — C3D8I (post P1-03 fix)")
    lines.append("")
    lines.append(f"**Overall:** {'✅ PASS' if canonical_res.passed else '❌ FAIL'}")
    lines.append("")
    lines.append("| Metric | Reference | Computed | Err % | Tol % | Verdict |")
    lines.append("|---|---|---|---|---|---|")
    for m in canonical_res.metrics:
        lines.append(
            f"| {m.metric_id} | {m.reference:.4f} {m.unit} | "
            f"{m.computed:.4f} {m.unit} | {m.error_pct:+.2f} | "
            f"{m.tolerance_pct:.1f} | {'PASS' if m.passed else 'FAIL'} |"
        )
    lines.append("")
    lines.append("## 2. Legacy shear-locked C3D8 deck (regression baseline)")
    lines.append("")
    lines.append(
        f"**Overall:** {'❌ FAIL (expected)' if not legacy_res.passed else '⚠️ unexpected PASS'}"
    )
    lines.append("")
    lines.append("| Metric | Reference | Computed | Err % | Tol % | Verdict |")
    lines.append("|---|---|---|---|---|---|")
    for m in legacy_res.metrics:
        lines.append(
            f"| {m.metric_id} | {m.reference:.4f} {m.unit} | "
            f"{m.computed:.4f} {m.unit} | {m.error_pct:+.2f} | "
            f"{m.tolerance_pct:.1f} | {'PASS' if m.passed else 'FAIL'} |"
        )
    lines.append("")
    lines.append("## 3. Root-cause analysis — why C3D8 underpredicted")
    lines.append("")
    lines.append("The legacy C3D8 (fully-integrated trilinear hex) element suffers from")
    lines.append("**shear locking** in pure bending when only one element is used through")
    lines.append("the beam thickness. Parasitic shear strains inflate the element stiffness,")
    lines.append("so the predicted tip deflection (0.4936 mm, -35.2% vs theory) and the")
    lines.append("fixed-end bending stress (190.1 MPa, -20.8% vs theory) are both")
    lines.append("systematically low.")
    lines.append("")
    lines.append("**Fix applied (`gs001.inp`):** switch element type to `C3D8I` —")
    lines.append("incompatible-modes trilinear hex — which adds internal deformation")
    lines.append("modes that cure the shear-locking pathology without changing the mesh")
    lines.append("node layout. Result: tip deflection 0.7567 mm (-0.68%), top fibre")
    lines.append("SXX +248.5 MPa (+3.54%). Both metrics under the 5% threshold.")
    lines.append("")
    lines.append("**Regression protection:** `gs001_c3d8_shearlock.inp` is preserved as a")
    lines.append("canonical failure fixture. `tests/test_golden_sample_validation.py`")
    lines.append("asserts the legacy deck must fail the validator — if it ever starts")
    lines.append("passing, either the validator tolerance has been relaxed silently or")
    lines.append("the reference values were miswritten.")
    lines.append("")
    lines.append("## 4. Traceability")
    lines.append("")
    lines.append("- PRD v0.2 §3.2 — Golden Sample ≤5% accuracy requirement")
    lines.append("- ADR-008 N-1 — 5% threshold moved from P1-02 to P1-03")
    lines.append("- ADR-002 — CalculiX as main solver (element type is a modelling knob")
    lines.append("  within the approved solver, not an ADR-level change)")
    lines.append("")
    lines.append("*Report generated by scripts/p1_03_generate_report.py*")

    report_path = OUT_DIR / "report.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"Wrote {OUT_DIR / 'validation.json'}")
    return 0 if canonical_res.passed and not legacy_res.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
