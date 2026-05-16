"""Tier 1 candidate emitted-JSON schema version stamps (FM-04a Phase 5 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This module is the *single source of truth* for the ``schema_version`` field
that every Phase 3 / Phase 4 / Phase 5 emitted JSON now carries. Stamping a
schema version makes downstream diffs deterministic (Phase 4 D archived
packet diff) and lets cohort time-series (Phase 5 C/D) detect when a
schema changed underneath a snapshot.

Phase 5 deliberately ships *stamps only* — there is no migration layer here
yet. A reviewer reading two snapshots taken weeks apart can still cross-check
the ``schema_version`` against the manifests they were generated from, but
runtime code does not yet branch on the value.

============================================
Documented bump policy (binding for all Phase >= 5 work)
============================================

We use a 3-segment ``"MAJOR.MINOR.PATCH"`` scheme for each emitted-JSON
contract. The policy is intentionally narrow so we do not invent migration
work the project does not yet need:

* **MAJOR**: bump when a previously-emitted field is *renamed*, *removed*,
  or has its semantic meaning changed in a way a downstream reviewer cannot
  decode from the old name alone. Bumping MAJOR REQUIRES a retrospective
  entry naming the broken consumer (real or synthetic test) and the
  Phase >= 5 sub-phase that introduced the break.

* **MINOR**: bump when a *new* field is added, a new enum value is added to
  an existing field, or a nested object grows an additional key. Old
  consumers reading the JSON continue to work because they ignore the
  unknown field.

* **PATCH**: bump for purely-internal corrections that do not change the
  schema shape — for example, fixing a typo in a forbidden-claim audit
  haystack, or fixing the serialization order of an existing field
  without renaming it.

Concrete rules:

1.  Schema version constants live in this file ONLY. No builder may
    inline-declare its own version string.
2.  Every builder reads its constant by name (``from ._schema_versions import
    ACCEPTANCE_PACKET_SCHEMA_VERSION``) and stamps a ``"schema_version"`` key
    at the top of its emitted dict.
3.  When a constant changes here, the PR / commit MUST also amend the
    matching builder test that asserts the new value, AND include a
    SCORECARD line citing the bump category (MAJOR / MINOR / PATCH).
4.  Bumping MAJOR also REQUIRES amending the retrospective for the closing
    sub-phase. Bumping MINOR or PATCH does not require a retrospective
    entry but does require the SCORECARD note.
5.  These constants are public to the ``backend.app.services.reporting``
    namespace AND to the frontend via the typed clients. A frontend client
    that drops the field on the way to the UI panel is a Phase 5 X-axis
    defect (-2 per missing pass-through) per the binding rubric.

------------------------------------------------------------
Starting versions for Phase 5 A
------------------------------------------------------------

All builders enter Phase 5 A at ``"1.0.0"``. The convergence orchestrator
predates Phase 5 but is also Tier 1 candidate output, so it joins the
versioned set at ``"1.0.0"``. The completeness rubric is *separately*
versioned because its weights are part of the contract a reviewer cites.

If a Phase 5 sub-phase needs to add a brand-new top-level field, bump
MINOR (-> ``"1.1.0"``) and update the matching test.
"""

from __future__ import annotations

# ----- emitted-JSON contracts (Phase 3 + Phase 4 outputs) -----

ACCEPTANCE_PACKET_SCHEMA_VERSION = "1.0.0"
"""``acceptance_packet.json`` top-level dict.

Builder: ``backend.app.services.reporting.acceptance_packet``.
"""

CASE_COMPLETENESS_SCHEMA_VERSION = "1.0.0"
"""``<case>_completeness_scorecard.json`` top-level dict.

Builder: ``backend.app.services.reporting.case_completeness``.
"""

COHORT_OVERVIEW_SCHEMA_VERSION = "1.0.0"
"""``cohort_overview`` HTTP response + on-disk serialization.

Builder: ``backend.app.services.reporting.cohort_overview``.
"""

CASE_COMPARISON_SCHEMA_VERSION = "1.0.0"
"""``case_comparison`` HTTP response.

Builder: ``backend.app.services.reporting.case_comparison``.
"""

ARCHIVED_PACKET_DIFF_SCHEMA_VERSION = "1.0.0"
"""``archived_packet_diff`` HTTP response.

Builder: ``backend.app.services.reporting.archived_packet_diff``.
"""

REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION = "1.0.0"
"""``BUNDLE_MANIFEST.json`` inside a reviewer bundle zip.

Builder: ``backend.app.services.reporting.reviewer_bundle``.
"""

CONVERGENCE_STUDY_SCHEMA_VERSION = "1.0.0"
"""``convergence_study.json`` payload.

Builder: ``backend.app.services.ballistics.convergence_orchestrator``.
"""

# ----- Phase 5 B/C/D NEW contracts -----

REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION = "1.0.0"
"""``reproducibility_manifest.json`` per-case manifest (Phase 5 B).

Builder: ``backend.app.services.reporting.reproducibility_manifest``.
"""

COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION = "1.0.0"
"""``SNAPSHOT_MANIFEST.json`` at the root of a written cohort snapshot
directory (Phase 5 C).

Builder: ``backend.app.services.reporting.cohort_snapshot``.
"""

COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION = "1.0.0"
"""``cohort_snapshot_diff`` HTTP response (Phase 5 D).

Builder: ``backend.app.services.reporting.cohort_snapshot_diff``.
"""

# ----- rubric version (separate from emitted JSON contracts) -----

COMPLETENESS_RUBRIC_VERSION = "1.0.0"
"""Weights + axis structure used by ``case_completeness.score_case_completeness``.

Bumping this constant is a SEPARATE policy step (not coupled to
``CASE_COMPLETENESS_SCHEMA_VERSION``). A rubric change rebalances scores
on every case in the cohort; the binding rubric in Phase 4 / Phase 5
blueprints is treated as the contract a reviewer is citing, so the
constant exists for audit trail even if the on-disk JSON shape did not
change.
"""
