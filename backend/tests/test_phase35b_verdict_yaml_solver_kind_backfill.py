"""FM-04a Phase 35 B — verdict YAML cohort-wide solver_kind invariant.

Closes Phase 34 D functional_tester R2 finding #29 (schema heterogeneity
+ solver_kind gap). Pins the cohort-wide invariant:

    For every `golden_samples/<case>-candidate/cross_check_verdict.yaml`
    file, `solver_kind` is one of the six known enum values.

Phase 35 B did NOT bump schema_versions (those vary 1.0.0..1.4.0 across
the cohort by historical evolution) — the strict additive interpretation
of L:-1 is to enrich each verdict with `solver_kind` without disturbing
the readers that pin specific schema_version labels (Phase 21/29/30
tests).

This test acts as a forward-going cohort gate: when a new candidate
case lands in golden_samples/, the runner must populate solver_kind
from the known enum or this test fails.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "golden_samples"


# Phase 34 C extended the enum to 6 values. Phase 35 B does NOT modify
# the enum — only backfills cases that were missing the field.
SOLVER_KIND_ENUM = frozenset(
    {
        "linear_static",
        "modal",
        "buckling",
        "dynamic",
        "heat_transfer_steady_state",
        "contact_pair_static",
    }
)


def _all_verdict_paths() -> list[Path]:
    if not GOLDEN_DIR.is_dir():
        return []
    return sorted(GOLDEN_DIR.glob("*-candidate/cross_check_verdict.yaml"))


def _load_verdict(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    # Phase 18-34 verdicts are JSON-style; Phase 34 C hertz-contact is
    # real YAML. Try JSON first, fall back to YAML.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        import yaml  # type: ignore[import-untyped]

        loaded = yaml.safe_load(raw)
        assert isinstance(loaded, dict), (
            f"verdict at {path} did not parse to a mapping"
        )
        return loaded


def test_cohort_verdict_yamls_exist() -> None:
    """Sanity: the cohort has the expected verdict-YAML count.

    Phase 34 D Dim 6 audit recorded 12 cohort verdict YAMLs after
    Phase 34 C added hertz-contact. Phase 35 B is enrichment-only; the
    file count must NOT decrease.
    """
    paths = _all_verdict_paths()
    assert len(paths) >= 12, (
        f"cohort verdict count regressed to {len(paths)} < 12; "
        f"Phase 35 B must not remove any verdict YAML"
    )


@pytest.mark.parametrize("path", _all_verdict_paths(), ids=lambda p: p.parent.name)
def test_every_cohort_verdict_has_solver_kind(path: Path) -> None:
    """Phase 35 B invariant — every verdict YAML carries `solver_kind`.

    Before Phase 35 B, 9 legacy verdicts at schema 1.0 lacked this
    field, leading to cohort-wide grep under-counts. Phase 35 B
    backfilled them additively (existing schema_versions preserved).
    """
    payload = _load_verdict(path)
    assert "solver_kind" in payload, (
        f"verdict at {path.parent.name} is missing the solver_kind field "
        f"after Phase 35 B backfill; cohort grep would under-count"
    )


@pytest.mark.parametrize("path", _all_verdict_paths(), ids=lambda p: p.parent.name)
def test_every_solver_kind_value_in_enum(path: Path) -> None:
    """Phase 35 B invariant — each solver_kind matches the 6-value enum.

    The enum was extended to 6 in Phase 34 C (added contact_pair_static).
    Phase 35 B does NOT widen the enum; if a future runner uses an
    unknown value, this test will flag it for explicit enum extension.
    """
    payload = _load_verdict(path)
    value = payload.get("solver_kind")
    assert value in SOLVER_KIND_ENUM, (
        f"verdict at {path.parent.name} has solver_kind={value!r}, "
        f"not in the Phase 34 C 6-value enum {sorted(SOLVER_KIND_ENUM)}; "
        f"extend the enum in this test + audit doc before merging"
    )


def test_solver_kind_distribution_matches_phase35_backfill() -> None:
    """Phase 35 B documentation pin — record the cohort distribution
    so a future regression that flips a kind (e.g. modal → dynamic)
    is caught immediately.

    Distribution post-Phase 38 B (13 cases total — Phase 38 B added
    wedge-c3d6-candidate, the 6th element class, as a real-solver
    linear_static cross-check):
      linear_static            : 6
      modal                    : 2
      buckling                 : 2
      dynamic                  : 1
      heat_transfer_steady_state : 1
      contact_pair_static      : 1
    """
    from collections import Counter

    paths = _all_verdict_paths()
    kinds: Counter[str] = Counter()
    for path in paths:
        payload = _load_verdict(path)
        kind = payload.get("solver_kind")
        assert isinstance(kind, str), f"{path}: solver_kind not a string"
        kinds[kind] += 1

    expected = {
        "linear_static": 6,
        "modal": 2,
        "buckling": 2,
        "dynamic": 1,
        "heat_transfer_steady_state": 1,
        "contact_pair_static": 1,
    }
    assert dict(kinds) == expected, (
        f"cohort solver_kind distribution drifted: got {dict(kinds)}, "
        f"expected {expected}"
    )


def test_schema_versions_preserved_for_existing_readers() -> None:
    """Phase 35 B L:-1 guard pin — strict additive interpretation.

    Existing schema_versions (mix of 1.0.0 / 1.1.0 / 1.2.0 / 1.3.0 /
    1.4.0 across the cohort) are NOT bumped by Phase 35 B. Phase 21 /
    29 / 30 tests pin specific schema_version labels per case;
    enrichment must not break those pins.

    This test pins the heterogeneity explicitly so a careless future
    "schema_version harmonisation" PR doesn't silently break the
    schema-1.0 reader contract.
    """
    expected_schemas = {
        "cantilever-beam-candidate": "1.0.0",
        "cantilever-beam-modal-candidate": "1.0.0",
        "cantilever-beam-modal-l50-candidate": "1.0.0",
        "cantilever-buckle-candidate": "1.0.0",
        "cantilever-dynamic-candidate": "1.2.0",
        "cylinder-pv-candidate": "1.0.0",
        "euler-column-candidate": "1.0.0",
        "heat-transfer-1d-candidate": "1.3.0",
        "hertz-contact-candidate": "1.4.0",
        "plate-simply-supported-candidate": "1.0.0",
        "plate-ss-shell-candidate": "1.1.0",
        "plate-with-hole-candidate": "1.0.0",
    }
    for case_id, expected in expected_schemas.items():
        path = GOLDEN_DIR / case_id / "cross_check_verdict.yaml"
        assert path.is_file(), f"missing verdict for {case_id}"
        payload = _load_verdict(path)
        actual = payload.get("schema_version")
        assert actual == expected, (
            f"{case_id}: schema_version drifted to {actual!r}; "
            f"Phase 35 B is strictly additive and must NOT bump "
            f"schema_version (existing Phase 21/29/30 tests pin these)"
        )
