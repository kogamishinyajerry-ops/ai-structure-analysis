"""Tier 1 candidate cohort snapshot diff (FM-04a Phase 5 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Given two snapshot labels written by Phase 5 C, surface what *changed*
between them at the reviewer-visible level:

* cohort membership additions / removals
* per-case completeness score deltas
* per-case reproducibility manifest drift (git SHA, dirty flag,
  generator script SHA-256, Python version, package version)

The diff does NOT re-execute cases and does NOT touch
``golden_samples/**``. It strictly reads the two snapshot directories
under ``reports/snapshots/``. Each snapshot is Tier 1 candidate;
their diff is also Tier 1 candidate.

What this is NOT:
* Not a signed-validation regression detector.
* Not a Tier 2 benchmark agreement check.
* Not a substitute for the FM-04b P8 sealed-packet comparison.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY
from .cohort_snapshot import (
    SNAPSHOT_LABEL_RE,
    SNAPSHOT_MANIFEST_FILENAME,
    snapshots_root,
)

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate cohort snapshot diff only; not signed validation; "
    "not benchmark agreement; not a regression detector; not a substitute "
    "for the FM-04b P8 sealed-packet comparison."
)


@dataclass
class CompletenessDelta:
    case_id: str
    a_score: int | None
    b_score: int | None
    delta: int | None


@dataclass
class ReproducibilityDelta:
    case_id: str
    a_git_sha: str | None
    b_git_sha: str | None
    git_sha_changed: bool
    a_git_dirty: bool | None
    b_git_dirty: bool | None
    dirty_changed: bool
    a_python_version: str | None
    b_python_version: str | None
    python_version_changed: bool
    package_version_changes: list[dict[str, Any]]
    script_sha_changes: list[dict[str, Any]]


@dataclass
class NumericalDelta:
    """Phase 6 A — per-case raw value diff sourced from each snapshot's
    captured ``metrics/<case>.json`` (snapshot manifest schema >= 1.1.0).

    Fields are ``None`` when the metric was absent from either snapshot.
    """

    case_id: str
    residual_velocity_m_per_s: dict[str, Any]
    energy_balance_error_pct: dict[str, Any]
    convergence_combined_verdict: dict[str, Any]
    perforation_marker: dict[str, Any]


@dataclass
class CohortSnapshotDiff:
    schema_version: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    snapshot_a_label: str
    snapshot_b_label: str
    a_cohort_count: int
    b_cohort_count: int
    cohort_added: list[str]
    cohort_removed: list[str]
    cohort_shared: list[str]
    completeness_deltas: list[CompletenessDelta]
    reproducibility_deltas: list[ReproducibilityDelta]
    numerical_deltas: list[NumericalDelta]
    claim_impact: str


def diff_cohort_snapshots(
    repo_root: Path, label_a: str, label_b: str
) -> CohortSnapshotDiff:
    """Diff two cohort snapshots already written under ``reports/snapshots/``.

    Raises ``FileNotFoundError`` if either snapshot is missing.
    Raises ``ValueError`` if a label is malformed.
    """
    for label in (label_a, label_b):
        if not SNAPSHOT_LABEL_RE.fullmatch(label):
            raise ValueError(
                f"invalid snapshot label {label!r}; expected YYYY-MM-DDTHHMMSSZ"
            )

    root = snapshots_root(repo_root)
    dir_a = root / label_a
    dir_b = root / label_b
    if not dir_a.is_dir() or not (dir_a / SNAPSHOT_MANIFEST_FILENAME).is_file():
        raise FileNotFoundError(f"snapshot {label_a!r} not found under {root}")
    if not dir_b.is_dir() or not (dir_b / SNAPSHOT_MANIFEST_FILENAME).is_file():
        raise FileNotFoundError(f"snapshot {label_b!r} not found under {root}")

    manifest_a = _load_json(dir_a / SNAPSHOT_MANIFEST_FILENAME)
    manifest_b = _load_json(dir_b / SNAPSHOT_MANIFEST_FILENAME)
    cases_a = list(manifest_a.get("cases", []))
    cases_b = list(manifest_b.get("cases", []))
    set_a = set(cases_a)
    set_b = set(cases_b)
    shared = sorted(set_a & set_b)

    completeness_deltas: list[CompletenessDelta] = []
    reproducibility_deltas: list[ReproducibilityDelta] = []
    numerical_deltas: list[NumericalDelta] = []
    for case_id in shared:
        completeness_deltas.append(
            _diff_completeness(dir_a, dir_b, case_id)
        )
        reproducibility_deltas.append(
            _diff_reproducibility(dir_a, dir_b, case_id)
        )
        # Phase 6 A — only emit a numerical_delta when both snapshots
        # captured the case's metrics (manifest schema >= 1.1.0). When
        # either side is missing, fall through to a delta with all
        # values None — the downstream narrative templates will skip it.
        numerical = _diff_numerical(dir_a, dir_b, case_id)
        if numerical is not None:
            numerical_deltas.append(numerical)

    diff = CohortSnapshotDiff(
        schema_version=COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        snapshot_a_label=label_a,
        snapshot_b_label=label_b,
        a_cohort_count=len(cases_a),
        b_cohort_count=len(cases_b),
        cohort_added=sorted(set_b - set_a),
        cohort_removed=sorted(set_a - set_b),
        cohort_shared=shared,
        completeness_deltas=completeness_deltas,
        reproducibility_deltas=reproducibility_deltas,
        numerical_deltas=numerical_deltas,
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(diff)
    return diff


def render_cohort_snapshot_diff_json(diff: CohortSnapshotDiff) -> str:
    """Return the diff as a JSON string."""
    return json.dumps(_diff_to_dict(diff), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_completeness(dir_a: Path, dir_b: Path, case_id: str) -> CompletenessDelta:
    a_score = _read_score(dir_a / "completeness" / f"{case_id}.json")
    b_score = _read_score(dir_b / "completeness" / f"{case_id}.json")
    delta = None
    if a_score is not None and b_score is not None:
        delta = b_score - a_score
    return CompletenessDelta(
        case_id=case_id, a_score=a_score, b_score=b_score, delta=delta
    )


def _read_score(path: Path) -> int | None:
    if not path.is_file():
        return None
    payload = _load_json(path)
    raw = payload.get("score")
    if not isinstance(raw, int):
        return None
    return raw


def _diff_reproducibility(
    dir_a: Path, dir_b: Path, case_id: str
) -> ReproducibilityDelta:
    a = _load_optional(dir_a / "reproducibility" / f"{case_id}.json")
    b = _load_optional(dir_b / "reproducibility" / f"{case_id}.json")

    a_sha = _str_or_none(a, "git_commit_sha")
    b_sha = _str_or_none(b, "git_commit_sha")
    a_dirty = _bool_or_none(a, "git_dirty")
    b_dirty = _bool_or_none(b, "git_dirty")
    a_py = _str_or_none(a, "python_version")
    b_py = _str_or_none(b, "python_version")

    return ReproducibilityDelta(
        case_id=case_id,
        a_git_sha=a_sha,
        b_git_sha=b_sha,
        git_sha_changed=(a_sha is not None and b_sha is not None and a_sha != b_sha),
        a_git_dirty=a_dirty,
        b_git_dirty=b_dirty,
        dirty_changed=(
            a_dirty is not None and b_dirty is not None and a_dirty != b_dirty
        ),
        a_python_version=a_py,
        b_python_version=b_py,
        python_version_changed=(
            a_py is not None and b_py is not None and a_py != b_py
        ),
        package_version_changes=_diff_packages(a, b),
        script_sha_changes=_diff_scripts(a, b),
    )


def _diff_numerical(
    dir_a: Path, dir_b: Path, case_id: str
) -> NumericalDelta | None:
    """Phase 6 A — read each snapshot's captured metrics/<case>.json and
    surface raw value diffs. Returns ``None`` when neither side has the
    file (gracefully degrades for 1.0.0 snapshots).
    """
    a = _load_optional(dir_a / "metrics" / f"{case_id}.json")
    b = _load_optional(dir_b / "metrics" / f"{case_id}.json")
    if a is None and b is None:
        return None
    return NumericalDelta(
        case_id=case_id,
        residual_velocity_m_per_s=_numeric_pair(
            _extract_residual_velocity(a), _extract_residual_velocity(b)
        ),
        energy_balance_error_pct=_absolute_numeric_pair(
            _extract_energy_balance_error(a), _extract_energy_balance_error(b)
        ),
        convergence_combined_verdict=_verdict_pair(
            _extract_convergence_verdict(a), _extract_convergence_verdict(b)
        ),
        perforation_marker=_marker_pair(
            _extract_perforation_marker(a), _extract_perforation_marker(b)
        ),
    )


def _extract_residual_velocity(payload: dict[str, Any] | None) -> float | None:
    if payload is None:
        return None
    block = payload.get("perforation")
    if not isinstance(block, dict):
        return None
    value = block.get("residual_velocity_m_per_s")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_energy_balance_error(payload: dict[str, Any] | None) -> float | None:
    if payload is None:
        return None
    block = payload.get("energy_audit")
    if not isinstance(block, dict):
        return None
    value = block.get("energy_balance_error_pct")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_convergence_verdict(payload: dict[str, Any] | None) -> str | None:
    """The convergence verdict lives in convergence_study.json, not in
    ballistic_metrics.json. The snapshot writer copies only metrics; we
    surface the verdict here as None when absent — the completeness
    scorecard already carries this signal under a different name.
    """
    if payload is None:
        return None
    block = payload.get("convergence_summary")
    if isinstance(block, dict):
        verdict = block.get("combined_verdict")
        if isinstance(verdict, str):
            return verdict
    return None


def _extract_perforation_marker(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    block = payload.get("perforation")
    if not isinstance(block, dict):
        return None
    marker = block.get("marker")
    if isinstance(marker, str):
        return marker
    return None


def _numeric_pair(a: float | None, b: float | None) -> dict[str, Any]:
    if a is None or b is None:
        return {"a": a, "b": b, "delta": None, "delta_pct": None}
    delta = b - a
    delta_pct = None if a == 0 else (delta / a) * 100.0
    return {
        "a": a,
        "b": b,
        "delta": round(delta, 6),
        "delta_pct": None if delta_pct is None else round(delta_pct, 6),
    }


def _absolute_numeric_pair(a: float | None, b: float | None) -> dict[str, Any]:
    if a is None or b is None:
        return {"a": a, "b": b, "delta": None, "delta_abs_pct": None}
    delta = b - a
    return {
        "a": a,
        "b": b,
        "delta": round(delta, 6),
        "delta_abs_pct": round(abs(delta), 6),
    }


def _verdict_pair(a: str | None, b: str | None) -> dict[str, Any]:
    return {"a": a, "b": b, "same_verdict": a is not None and a == b}


def _marker_pair(a: str | None, b: str | None) -> dict[str, Any]:
    return {"a": a, "b": b, "same_marker": a is not None and a == b}


def _load_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return _load_json(path)


def _str_or_none(payload: dict[str, Any] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    if value is None or not isinstance(value, str):
        return None
    return value


def _bool_or_none(payload: dict[str, Any] | None, key: str) -> bool | None:
    if payload is None:
        return None
    value = payload.get(key)
    if not isinstance(value, bool):
        return None
    return value


def _diff_packages(
    a: dict[str, Any] | None, b: dict[str, Any] | None
) -> list[dict[str, Any]]:
    a_map = _packages_map(a)
    b_map = _packages_map(b)
    names = sorted(set(a_map.keys()) | set(b_map.keys()))
    out: list[dict[str, Any]] = []
    for name in names:
        a_ver = a_map.get(name)
        b_ver = b_map.get(name)
        if a_ver == b_ver:
            continue
        out.append({"name": name, "a_version": a_ver, "b_version": b_ver})
    return out


def _packages_map(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return {}
    out: dict[str, str] = {}
    for entry in payload.get("tracked_packages", []):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        version = entry.get("version")
        if isinstance(name, str) and isinstance(version, str):
            out[name] = version
    return out


def _diff_scripts(
    a: dict[str, Any] | None, b: dict[str, Any] | None
) -> list[dict[str, Any]]:
    a_map = _scripts_map(a)
    b_map = _scripts_map(b)
    paths = sorted(set(a_map.keys()) | set(b_map.keys()))
    out: list[dict[str, Any]] = []
    for relpath in paths:
        a_sha = a_map.get(relpath)
        b_sha = b_map.get(relpath)
        if a_sha == b_sha:
            continue
        out.append({"relpath": relpath, "a_sha256": a_sha, "b_sha256": b_sha})
    return out


def _scripts_map(payload: dict[str, Any] | None) -> dict[str, str]:
    if payload is None:
        return {}
    out: dict[str, str] = {}
    for entry in payload.get("scripts", []):
        if not isinstance(entry, dict):
            continue
        relpath = entry.get("relpath")
        sha = entry.get("sha256")
        if isinstance(relpath, str) and isinstance(sha, str):
            out[relpath] = sha
    return out


def _diff_to_dict(diff: CohortSnapshotDiff) -> dict[str, Any]:
    return {
        "schema_version": diff.schema_version,
        "generated_at_utc": diff.generated_at_utc,
        "claim_tier": diff.claim_tier,
        "claim_boundary": diff.claim_boundary,
        "snapshot_a_label": diff.snapshot_a_label,
        "snapshot_b_label": diff.snapshot_b_label,
        "a_cohort_count": diff.a_cohort_count,
        "b_cohort_count": diff.b_cohort_count,
        "cohort_added": diff.cohort_added,
        "cohort_removed": diff.cohort_removed,
        "cohort_shared": diff.cohort_shared,
        "numerical_deltas": [
            {
                "case_id": n.case_id,
                "residual_velocity_m_per_s": n.residual_velocity_m_per_s,
                "energy_balance_error_pct": n.energy_balance_error_pct,
                "convergence_combined_verdict": n.convergence_combined_verdict,
                "perforation_marker": n.perforation_marker,
            }
            for n in diff.numerical_deltas
        ],
        "completeness_deltas": [
            {
                "case_id": d.case_id,
                "a_score": d.a_score,
                "b_score": d.b_score,
                "delta": d.delta,
            }
            for d in diff.completeness_deltas
        ],
        "reproducibility_deltas": [
            {
                "case_id": d.case_id,
                "a_git_sha": d.a_git_sha,
                "b_git_sha": d.b_git_sha,
                "git_sha_changed": d.git_sha_changed,
                "a_git_dirty": d.a_git_dirty,
                "b_git_dirty": d.b_git_dirty,
                "dirty_changed": d.dirty_changed,
                "a_python_version": d.a_python_version,
                "b_python_version": d.b_python_version,
                "python_version_changed": d.python_version_changed,
                "package_version_changes": d.package_version_changes,
                "script_sha_changes": d.script_sha_changes,
            }
            for d in diff.reproducibility_deltas
        ],
        "claim_impact": diff.claim_impact,
    }


def _assert_no_overclaim(diff: CohortSnapshotDiff) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_diff_to_dict(diff), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"Cohort snapshot diff contains forbidden positive claim: {token!r}"
            )
