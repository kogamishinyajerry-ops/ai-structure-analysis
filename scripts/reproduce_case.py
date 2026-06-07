#!/usr/bin/env python3
"""Reproduce a committed cross-check case from its sealed inputs (ADR-027 V2-2).

This is the ``reproduce <case_id>`` CLI named by ADR-027 D3 V2-2 and tracked as
G-2 evidence-packet item 6 (``reproduce-CLI audit log``). It re-derives a case's
result + verdict from the committed-in-VC inputs and writes a structured
audit-trail log, so that a committed public-benchmark agreement is provably
reproducible *on demand with an audit trail*, not merely asserted by a static
``cross_check_verdict.yaml``.

Two reproduction kinds, chosen honestly per case and host:

* ``real_solve`` — for a case with a registered real-solver reproducer (the
  NAFEMS LE10 public-benchmark agreement) AND ``ccx`` on PATH: copy the sealed
  deck to a scratch dir, run a FRESH real CalculiX solve, extract the target
  quantity from the produced ``.frd``, re-grade against the published target,
  and compare the freshly-solved value against the committed pinned value.
* ``recompute`` — for any case (or LE10 when ``ccx`` is absent / ``--no-solve``):
  re-derive ``residual_pct`` from the committed observed/analytical values via
  the cohort magnitude formula and re-check it against the declared tolerance.
  This verifies the committed evidence is internally consistent; it does NOT
  re-run a solver, and the audit log says so plainly.

Every run also re-hashes the case's sealed artifacts against its
``artifact_manifest.json`` (when present) — reproduction from tampered inputs is
refused.

Honesty boundary: a green reproduction means the committed evidence reproduces
from sealed inputs. It is NOT signed validation — G-2 item 7 (independent
review/signoff, owner-authorized per ADR-023) remains open, so the case stays a
Tier-1 engineering candidate (registry overlay notwithstanding).

Usage:
    python scripts/reproduce_case.py nafems-le10-thick-plate-candidate
    python scripts/reproduce_case.py <case_id> --no-solve   # recompute only
    python scripts/reproduce_case.py <case_id> --output-dir reports/reproduce_audit

Exit code 0 iff the case reproduced; non-zero otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[1]

# Relative drift the freshly re-solved observed value may show against the
# committed pinned value before a real_solve reproduction is rejected. Mirrors
# ``real_le10.LE10_DRIFT_REL`` (the validated path's own re-solve drift bound).
REAL_SOLVE_DRIFT_REL = 5e-3
# Absolute pct-point slack when checking a recomputed residual against the
# rounded value recorded in the verdict file (verdicts round as coarsely as 3
# decimals). Matches ``tests/test_v2_0_residual_floor.RESIDUAL_RECOMPUTE_ABS_PCT``.
RESIDUAL_RECOMPUTE_ABS_PCT = 0.05

AUDIT_SCHEMA = "reproduce-audit/1.0"


def _ensure_paths(repo_root: Path) -> None:
    """Put repo root (for ``tools.*``) and ``backend`` (for ``app.*``) on sys.path."""
    for p in (repo_root, repo_root / "backend"):
        rp = p.resolve()
        if rp.is_dir() and str(rp) not in sys.path:
            sys.path.insert(0, str(rp))


def _load_mapping(path: Path) -> dict:
    """Verdict files are JSON-formatted or YAML (hertz-contact); try JSON first."""
    text = path.read_text()
    try:
        loaded: Any = json.loads(text)
    except json.JSONDecodeError:
        import yaml

        loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return loaded


def _scalar(payload: dict, key: str) -> Any:
    """Top-level first, then the nested ``verdict_outcome`` block (hertz schema)."""
    if key in payload:
        return payload[key]
    nested = payload.get("verdict_outcome")
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return None


def _observed_analytical_pair(payload: dict, case_id: str) -> tuple[float, float]:
    """Extract the (observed, analytical) pair the residual was computed from.

    Mirrors ``tests/test_v2_0_residual_floor`` deliberately (the floor test and
    this CLI must agree on what 'reproduce' means): flat ``observed_<suffix>`` /
    ``analytical_<suffix>`` paired by suffix, else the nested
    ``observed.* `` / ``analytical_reference.*`` shape.
    """
    observed = {
        k[len("observed_") :]: v
        for k, v in payload.items()
        if k.startswith("observed_") and isinstance(v, (int, float))
    }
    analytical = {
        k[len("analytical_") :]: v
        for k, v in payload.items()
        if k.startswith("analytical_") and isinstance(v, (int, float))
    }
    paired = sorted(set(observed) & set(analytical))
    if paired:
        if len(paired) != 1:
            raise ValueError(f"{case_id}: ambiguous observed/analytical suffixes {paired}")
        suffix = paired[0]
        return float(observed[suffix]), float(analytical[suffix])

    obs_block = payload.get("observed")
    ana_block = payload.get("analytical_reference")
    if isinstance(obs_block, dict) and isinstance(ana_block, dict):
        shared = sorted(
            k
            for k in set(obs_block) & set(ana_block)
            if isinstance(obs_block[k], (int, float)) and isinstance(ana_block[k], (int, float))
        )
        if len(shared) != 1:
            raise ValueError(f"{case_id}: nested observed/analytical share {shared}")
        return float(obs_block[shared[0]]), float(ana_block[shared[0]])

    raise ValueError(f"{case_id}: no observed/analytical pair found in verdict schema")


def _recompute_residual_pct(observed: float, analytical: float) -> float:
    """The one magnitude formula consistent across the whole cohort."""
    return (abs(observed) - abs(analytical)) / abs(analytical) * 100.0


def _check_integrity(case_dir: Path) -> dict:
    """Re-hash the case's sealed artifacts against its manifest (if present)."""
    manifest_path = case_dir / "artifact_manifest.json"
    if not manifest_path.is_file():
        return {"manifest_present": False, "all_hashes_match": None, "mismatches": []}
    manifest = json.loads(manifest_path.read_text())
    sealed = manifest.get("sealed_artifacts", {})
    mismatches: list[str] = []
    for rel, meta in sealed.items():
        p = case_dir / rel
        if not p.is_file():
            mismatches.append(f"{rel}: missing")
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != meta.get("sha256"):
            mismatches.append(f"{rel}: sha256 {digest[:12]}!=sealed {str(meta.get('sha256'))[:12]}")
        if p.stat().st_size != meta.get("bytes"):
            mismatches.append(f"{rel}: bytes {p.stat().st_size}!=sealed {meta.get('bytes')}")
    return {
        "manifest_present": True,
        "all_hashes_match": not mismatches,
        "mismatches": mismatches,
    }


def _reproduce_le10_real(timeout_s: int) -> dict:
    """Fresh real-ccx re-solve of the sealed LE10 deck → re-graded benchmark."""
    import tempfile

    from app.services.workflow import real_le10

    with tempfile.TemporaryDirectory(prefix="reproduce_le10_") as td:
        solve = real_le10.run_le10_solve(Path(td), timeout_s=timeout_s)
        frd = solve.get("frd_path")
        if not frd:
            raise RuntimeError("LE10 re-solve produced no .frd (incomplete solve)")
        bench = real_le10.extract_le10_benchmark(Path(solve["deck_path"]), Path(frd))
    return {
        "observed_pa": float(bench["sigma_yy_pa"]),
        "analytical_pa": float(bench["target_pa"]),
        "residual_pct": float(bench["residual_pct"]),
        "tolerance_pct": float(bench["tolerance_pct"]),
        "verdict": bench["verdict"],
        "node_d": bench["node_d"],
        "point_d_m": bench["point_d_m"],
        "sigma_yy_mpa": float(bench["sigma_yy_pa"]) / 1e6,
        "ccx_version": solve.get("ccx_version"),
        "converged": solve.get("converged"),
    }


# Cases with a registered REAL-solver reproducer (re-run the solver from scratch).
# Anything not listed reproduces via the ccx-free recompute path.
_REAL_SOLVERS = {"nafems-le10-thick-plate-candidate": _reproduce_le10_real}


def _ccx_available() -> bool:
    """Whether ccx is on PATH (presence only; the exact version is recorded from
    an actual solve, never fabricated on the recompute path)."""
    try:
        from app.services.workflow import real_le10

        return bool(real_le10.le10_available())
    except Exception:
        return False


def reproduce_case(
    case_id: str,
    *,
    repo_root: Path,
    do_solve: bool,
    timeout_s: int,
    now: datetime,
) -> dict:
    """Build the structured audit record for one reproduction attempt."""
    # case_id must be a single directory name: never let "../" or an absolute
    # path escape golden_samples/ and select an arbitrary file (path traversal).
    if (
        not case_id
        or case_id in (".", "..")
        or "/" in case_id
        or "\\" in case_id
        or Path(case_id).is_absolute()
    ):
        raise ValueError(
            f"invalid case_id {case_id!r}: must be a bare golden_samples/ directory name "
            "(no path separators, no '..', not absolute)"
        )
    case_dir = repo_root / "golden_samples" / case_id
    verdict_path = case_dir / "cross_check_verdict.yaml"
    if not verdict_path.is_file():
        raise FileNotFoundError(
            f"no committed verdict for {case_id!r}: {verdict_path} (is the case id correct?)"
        )

    committed = _load_mapping(verdict_path)
    c_observed, c_analytical = _observed_analytical_pair(committed, case_id)
    c_residual = _scalar(committed, "residual_pct")
    c_tolerance = _scalar(committed, "tolerance_pct")
    c_verdict = _scalar(committed, "verdict")

    integrity = _check_integrity(case_dir)
    ccx_ok = _ccx_available()
    ccx_version: str | None = None  # recorded only from an actual solve, never fabricated

    real_solver = _REAL_SOLVERS.get(case_id)
    use_real = bool(real_solver) and do_solve and ccx_ok
    kind = "real_solve" if use_real else "recompute"

    rederived: dict
    notes: list[str] = []
    if use_real:
        rederived = real_solver(timeout_s)  # type: ignore[misc]
        ccx_version = rederived.get("ccx_version")
        drift = abs(rederived["observed_pa"] - c_observed) / abs(c_observed)
        within_drift = drift <= REAL_SOLVE_DRIFT_REL
        verdict_matches = rederived["verdict"] == c_verdict
        agreement = {
            "committed_observed_pa": c_observed,
            "rederived_observed_pa": rederived["observed_pa"],
            "observed_rel_drift": drift,
            "drift_tolerance_rel": REAL_SOLVE_DRIFT_REL,
            "within_drift_tolerance": within_drift,
            "verdict_matches_committed": verdict_matches,
        }
        # reproduced only when sealed + freshly-solved within drift + verdict
        # matches committed AND is itself a PASS (a both-FAIL match is not a
        # reproduced benchmark agreement) — mirrors the recompute-path gate.
        reproduced = (
            integrity.get("all_hashes_match") is True
            and within_drift
            and verdict_matches
            and rederived["verdict"] == "PASS"
        )
    else:
        if real_solver and not do_solve:
            notes.append("real solver available but --no-solve requested; recompute only")
        elif real_solver and not ccx_ok:
            notes.append("real-solver case but ccx absent; recompute only (NOT a fresh solve)")
        else:
            notes.append("no registered real-solver reproducer; verdict-consistency recompute")
        r_residual = _recompute_residual_pct(c_observed, c_analytical)
        r_verdict = "PASS" if abs(r_residual) <= float(c_tolerance) else "FAIL"
        rederived = {
            "observed_pa": c_observed,
            "analytical_pa": c_analytical,
            "residual_pct": r_residual,
            "tolerance_pct": float(c_tolerance),
            "verdict": r_verdict,
        }
        residual_matches = abs(r_residual - float(c_residual)) <= RESIDUAL_RECOMPUTE_ABS_PCT
        verdict_matches = r_verdict == c_verdict
        agreement = {
            "committed_residual_pct": float(c_residual),
            "rederived_residual_pct": r_residual,
            "residual_abs_slack_pct": RESIDUAL_RECOMPUTE_ABS_PCT,
            "residual_matches_committed": residual_matches,
            "verdict_matches_committed": verdict_matches,
        }
        # "Reproduced from SEALED inputs" requires a verified seal: a missing
        # manifest means the inputs cannot be proven canonical, so the claim is
        # withheld (reproduced=False) and the limitation is disclosed.
        if not integrity["manifest_present"]:
            notes.append(
                "no artifact_manifest.json: cannot verify inputs are the sealed set; "
                "recompute is internally consistent but NOT 'reproduced from sealed inputs'"
            )
        integrity_ok = integrity.get("all_hashes_match") is True
        reproduced = integrity_ok and residual_matches and verdict_matches and r_verdict == "PASS"

    return {
        "schema": AUDIT_SCHEMA,
        "case_id": case_id,
        "reproduced_at_utc": now.astimezone(UTC).isoformat(),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "reproduction_kind": kind,
        "ccx": {"available": ccx_ok, "version": ccx_version},
        "inputs_integrity": integrity,
        "committed": {
            "observed": c_observed,
            "analytical": c_analytical,
            "residual_pct": float(c_residual) if c_residual is not None else None,
            "tolerance_pct": float(c_tolerance) if c_tolerance is not None else None,
            "verdict": c_verdict,
        },
        "rederived": rederived,
        "agreement": agreement,
        "reproduced": bool(reproduced),
        "notes": notes,
        "claim_boundary": (
            "reproducibility evidence only; NOT signed validation "
            "(G-2 item 7 independent signoff remains open per ADR-023)"
        ),
    }


def _write_audit(record: dict, output_dir: Path, now: datetime, *, repo_root: Path) -> Path:
    out = output_dir.resolve()
    repo = repo_root.resolve()
    # Never write into the sealed-evidence area, and keep the audit trail inside
    # the repo tree (no absolute/escaped path can redirect the log elsewhere).
    if "golden_samples" in out.parts:
        raise SystemExit(f"refusing to write audit log under golden_samples/**: {out}")
    if out != repo and repo not in out.parents:
        raise SystemExit(f"refusing to write audit log outside the repo tree ({repo}): {out}")
    out.mkdir(parents=True, exist_ok=True)
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"{record['case_id']}_{stamp}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce a committed cross-check case from sealed inputs (ADR-027 V2-2)."
    )
    parser.add_argument("case_id", help="candidate dir name under golden_samples/")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="audit-log dir (default reports/reproduce_audit/). Refuses golden_samples/**.",
    )
    parser.add_argument(
        "--no-solve",
        action="store_true",
        help="skip the real solve; verdict-consistency recompute only",
    )
    parser.add_argument("--timeout", type=int, default=900, help="ccx solve timeout seconds")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    _ensure_paths(repo_root)
    now = datetime.now(UTC)

    record = reproduce_case(
        args.case_id,
        repo_root=repo_root,
        do_solve=not args.no_solve,
        timeout_s=args.timeout,
        now=now,
    )
    output_dir = args.output_dir or (repo_root / "reports" / "reproduce_audit")
    audit_path = _write_audit(record, output_dir, now, repo_root=repo_root)

    kind = record["reproduction_kind"]
    re = record["rederived"]
    print(f"reproduce {args.case_id}  [{kind}]")
    if kind == "real_solve":
        print(
            f"  sigma_yy@D = {re.get('sigma_yy_mpa'):+.4f} MPa  resid={re['residual_pct']:+.3f}%"
            f"  verdict={re['verdict']}  (ccx {record['ccx']['version']})"
        )
        print(
            f"  drift vs committed = {record['agreement']['observed_rel_drift'] * 100:.3f}%"
            f"  (tol {REAL_SOLVE_DRIFT_REL * 100:.1f}%)"
        )
    else:
        print(
            f"  residual_pct = {re['residual_pct']:+.4f}%  tol={re['tolerance_pct']}%"
            f"  verdict={re['verdict']}"
        )
        for n in record["notes"]:
            print(f"  note: {n}")
    integ = record["inputs_integrity"]
    print(
        f"  inputs_integrity: manifest={integ['manifest_present']} "
        f"hashes_match={integ['all_hashes_match']}"
    )
    print(f"  REPRODUCED = {record['reproduced']}")
    print(f"  audit log -> {audit_path}")
    return 0 if record["reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
