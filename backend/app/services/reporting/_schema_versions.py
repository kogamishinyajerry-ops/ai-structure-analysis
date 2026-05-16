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

COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION = "1.2.0"
"""``SNAPSHOT_MANIFEST.json`` at the root of a written cohort snapshot
directory (Phase 5 C; Phase 6 A + Phase 7 A MINOR bumps).

Builder: ``backend.app.services.reporting.cohort_snapshot``.

Bump history:
* ``1.0.0`` (Phase 5 C, commit ``f1aa09d``) — initial release.
* ``1.1.0`` (Phase 6 A, MINOR per bump policy) — added optional
  ``metrics/<case>.json`` sibling directory. The new ``members``
  entries are additive; consumers that read only the JSON files
  declared in 1.0.0 continue to work. The bump exists so the
  Phase 6 D timeline + Phase 6 A diff raw-value extension can
  distinguish snapshots that have / do not have ``metrics/``.
* ``1.2.0`` (Phase 7 A, MINOR per bump policy) — added optional
  ``convergence/<case>.json`` sibling directory. The snapshot writer
  now copies each case's live ``convergence_study.json`` into the
  snapshot so the timeline + diff can recover the convergence
  verdict directly from captured bytes rather than relying on an
  inlined ``convergence_summary`` block inside the metrics file.
  Consumers reading the 1.1.0 fields continue to work; the diff and
  timeline gracefully degrade when ``convergence/`` is absent.
  Closes Phase 6 retrospective carry-forward §1.
"""

COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION = "1.1.0"
"""``cohort_snapshot_diff`` HTTP response (Phase 5 D; Phase 6 A
MINOR bump).

Builder: ``backend.app.services.reporting.cohort_snapshot_diff``.

Bump history:
* ``1.0.0`` (Phase 5 D, commit ``4c6eeb3``) — initial release with
  cohort membership + completeness deltas + reproducibility deltas.
* ``1.1.0`` (Phase 6 A, MINOR per bump policy) — added optional
  ``numerical_deltas`` field listing per-case raw value diffs
  (residual_velocity_m_per_s, energy_balance_error_pct,
  convergence_combined_verdict, perforation_marker) for every case
  whose snapshot has a captured ``metrics/<case>.json``. Empty list
  when either snapshot is at manifest schema 1.0.0 (graceful
  fallback). Consumers reading the 1.0.0 fields continue to work.
"""

# ----- Phase 6 NEW contracts -----

TRUST_SCORE_SCHEMA_VERSION = "1.0.0"
"""``trust_score`` HTTP response (Phase 6 B).

Builder: ``backend.app.services.reporting.trust_score``.
"""

TRUST_SCORE_FORMULA_VERSION = "1.0.0"
"""Composite weights + per-axis sub-formulas used by
``trust_score.compute_trust_score``.

Versioned SEPARATELY from ``TRUST_SCORE_SCHEMA_VERSION``: the schema
governs the JSON shape, the formula governs the numerical meaning of
``trust_score``. A reviewer comparing two snapshots needs to know
whether the score difference came from a formula change or a real
evidence change. Bumping the formula version REQUIRES a retrospective
entry naming the rebalance + a SCORECARD note on the bump category.
"""

SNAPSHOT_NARRATIVE_SCHEMA_VERSION = "1.1.0"
"""``snapshot_narrative`` HTTP response (Phase 6 C; Phase 7 B MINOR bump).

Builder: ``backend.app.services.reporting.snapshot_narrative``.

Bump history:
* ``1.0.0`` (Phase 6 C, commit ``823040b``) — initial release with
  per-case templated narrative lines (16 enumerated templates,
  fixed severity, no LLM generation).
* ``1.1.0`` (Phase 7 B, MINOR per bump policy) — added optional
  ``locale`` envelope field surfacing the catalog used to render
  the narrative lines (defaults to ``"en-US"`` at the builder /
  endpoint default). The field is additive; consumers reading the
  1.0.0 fields continue to work. The bump exists so a downstream
  reviewer comparing two captured narrative payloads can tell which
  catalog produced each rendering. Closes Phase 6 retrospective
  carry-forward §3.
"""

TRUST_SCORE_TIMELINE_SCHEMA_VERSION = "1.0.0"
"""``trust_score_timeline`` HTTP response (Phase 6 D).

Builder: ``backend.app.services.reporting.trust_score_timeline``.
"""

# ----- Phase 7 NEW contracts -----

TRUST_SCORE_ALERTS_SCHEMA_VERSION = "1.0.0"
"""``trust_score_alerts`` HTTP response (Phase 7 C).

Builder: ``backend.app.services.reporting.trust_score_alerts``.

Tier 1 candidate regression-alarm surface: walks a case's timeline
and surfaces snapshot-to-snapshot trust score drops above a
configurable threshold. Carries its own ``schema_version`` separately
from ``TRUST_SCORE_TIMELINE_SCHEMA_VERSION`` because the alarm payload
shape is distinct from the timeline payload shape. Closes Phase 6
retrospective carry-forward §4.
"""

COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION = "1.0.0"
"""``cohort_executive_summary`` HTTP response (Phase 8 D).

Builder: ``backend.app.services.reporting.cohort_executive_summary``.

Tier 1 candidate cohort scorecard: aggregates latest trust score
+ latest alarm count + latest signoff verdict across all
``golden_samples/*-candidate/`` cases, buckets each into
``healthy`` / ``watching`` / ``regressed``. Surfaces aggregate counts
+ per-case rows. Explicit ``claim_impact`` states the summary does
NOT promote any case to Tier 2 or substitute for signed validation.
"""

COHORT_ANOMALIES_SCHEMA_VERSION = "1.0.0"
"""``cohort_anomalies`` HTTP response (Phase 8 E).

Builder: ``backend.app.services.reporting.cohort_anomalies``.

Tier 1 candidate cohort statistical outliers: for each
``*-candidate`` case + each of the 4 trust-score axes, computes
mean + standard deviation across the cohort and flags cases >2σ
from mean on any axis. Severity buckets at 2σ / 3σ / 4σ. Explicit
``claim_impact``: "anomalies surface statistical outliers from
cohort mean; they do NOT diagnose root cause, validate physics, or
authorize Tier 2 promotion."
"""

TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.0.0"
"""``trust_score_provenance`` HTTP response (Phase 8 C).

Builder: ``backend.app.services.reporting.trust_score_provenance``.

Tier 1 candidate provenance trace: given a case + snapshot label,
walks back to every input file SHA (metrics / convergence /
completeness / reproducibility / generator script), surfaces the
``formula_version`` that produced the trust score, the recomputed
score itself, and the per-axis breakdown — all from frozen
snapshot bytes so the reviewer gets a deterministic answer to
"exactly what produced this 87?"
"""

SIGNOFF_RECORD_SCHEMA_VERSION = "1.0.0"
"""``signoff_record.json`` (Phase 8 A).

Builder: ``backend.app.services.reporting.signoff_record``.

Tier 1 candidate review-judgment record: persists reviewer name,
UTC ISO 8601 timestamp, verdict from the whitelisted enum
(``watching`` / ``needs_more_evidence`` / ``needs_more_convergence``
/ ``blocked_pending_input``), and reviewer notes audited for
forbidden positive claims. The verdict enum DELIBERATELY excludes
every Tier 2 promotion verb (no ``ready_for_tier_2``, no
``signed_validation_ready``, no ``benchmark_agreement``); the module
import-time audit ``_audit_verdict_whitelist`` enforces this so no
future maintainer can add a Tier 2 vocabulary verdict without
breaking import.
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
