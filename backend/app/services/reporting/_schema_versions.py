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

CASE_COMPLETENESS_SCHEMA_VERSION = "1.2.0"
"""``<case>_completeness_scorecard.json`` top-level dict.

Builder: ``backend.app.services.reporting.case_completeness``.

Bump history:
* ``1.0.0`` (Phase 5 A) — initial release with the ballistic-only rubric.
* ``1.1.0`` (Phase 11 A, MINOR per bump policy) — added top-level
  ``analysis_type`` envelope field. Default value ``"ballistic"`` preserves
  back-compat: a consumer reading the 1.0.0 fields continues to work,
  and a 1.0.0-era payload that omits the key materializes as the
  ballistic rubric via the dataclass default. Closes the e2e-demo gap
  surfaced by the cylinder-pv-candidate case (PV linear-static
  evidence was being scored against an irrelevant rubric).
* ``1.2.0`` (Phase 12 B, MINOR per bump policy) — substantiated the
  ``modal`` rubric with four new modal-specific axes
  (``mode_count_coverage``, ``freq_convergence``, ``mode_shape_quality``,
  ``mass_participation``) read from a ``modal_summary`` block inside
  the metrics JSON, replacing the inherited ballistic optional-artifact
  axes that were not load-bearing for an eigenproblem (``animation_manifest``
  and ``result_mesh`` remain inside the modal universal axes at reduced
  weight; ``notes`` was dropped). Universal axes rebalanced to
  10+10+10+10+10 = 50 to make room for the 15+15+10+10 modal-specific
  block. A 1.1.0-era payload that omits the ``modal_summary`` block
  scores 0 on the four new axes (graceful degrade) rather than failing
  to parse. Consumers reading the 1.1.0 fields continue to work because
  the dispatch is keyed on ``analysis_type``. Closes the v1 blueprint
  #06 modal-placeholder gap at the rubric layer.
"""

COHORT_OVERVIEW_SCHEMA_VERSION = "1.1.0"
"""``cohort_overview`` HTTP response + on-disk serialization.

Builder: ``backend.app.services.reporting.cohort_overview``.

1.1.0 (FM-04a Phase 38 F): each ``entries[*]`` row gains an additive
``claim_tier`` field (the per-case tier resolved from the ``_claim_tier``
SSOT, ADR-025) so a real-solver promotion surfaces at the API boundary.
Backward-compatible — consumers that ignore the field still parse 1.1.0
payloads, and the minor bump lets snapshot diff/audit consumers
distinguish a 1.0.0 row (no per-case tier) from a 1.1.0 row.
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

CONVERGENCE_STUDY_SCHEMA_VERSION = "1.2.0"
"""``convergence_study.json`` payload.

Builder: ``backend.app.services.ballistics.convergence_orchestrator``.

Bump history:
* ``1.0.0`` (Phase 5 A) — initial release with mesh_sweep + dt_sweep
  axes assumed.
* ``1.1.0`` (Phase 11 A, MINOR per bump policy) — added optional
  top-level ``convergence_kind`` discriminator ∈ {``explicit_dynamics``,
  ``nonlinear_static``, ``linear_static``, ``modal``} naming which
  axes are meaningful. For ``linear_static`` cases the ``dt_sweep``
  is N/A (no time integration) and the trust-score convergence
  scorer treats its absence as "not applicable", not as failure.
  Consumers reading the 1.0.0 fields continue to work. Closes the
  e2e-demo gap surfaced by the cylinder-pv-candidate case.
* ``1.2.0`` (Phase 12 A, MINOR per bump policy) — added optional
  ``mode_count_sweep`` axis for ``convergence_kind == "modal"``
  payloads (eigenproblem cases). The trust-score scorer now routes
  modal cases through a dedicated branch that scores
  ``mode_count_sweep`` and treats ``mesh_sweep`` + ``dt_sweep`` as
  N/A. Consumers reading 1.1.0 fields continue to work because the
  new axis is additive; a modal case that omits ``mode_count_sweep``
  scores 0 (inconclusive) on convergence_stability rather than
  silently falling into the explicit_dynamics two-axis path it
  incorrectly inhabited at 1.1.0. Closes Phase 11 blueprint #06
  modal-placeholder gap.
"""

# ----- Phase 5 B/C/D NEW contracts -----

REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION = "1.0.0"
"""``reproducibility_manifest.json`` per-case manifest (Phase 5 B).

Builder: ``backend.app.services.reporting.reproducibility_manifest``.
"""

COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION = "1.3.0"
"""``SNAPSHOT_MANIFEST.json`` at the root of a written cohort snapshot
directory (Phase 5 C; Phase 6 A / Phase 7 A / Phase 9 B MINOR bumps).

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
* ``1.3.0`` (Phase 9 B, MINOR per bump policy) — added optional
  ``generator/<case>.py`` sibling directory. The snapshot writer now
  copies each case's ``generator_script_path`` bytes into the
  snapshot so the trust-score-provenance trace can surface a SHA over
  the actual generator that produced the case rather than only over
  the rendered evidence. Consumers reading the 1.2.0 fields continue
  to work; the provenance walker gracefully degrades to
  ``present=False`` when ``generator/<case>.py`` is absent. Closes
  Phase 8 retrospective carry-forward §2.
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

TRUST_SCORE_TIMELINE_SCHEMA_VERSION = "1.2.0"
"""``trust_score_timeline`` HTTP response.

Builder: ``backend.app.services.reporting.trust_score_timeline``.

Bump history:

* ``1.0.0`` (Phase 6 D) — initial schema; per-snapshot
  ``TimelinePoint`` with ``trust_score`` + 4 axis-weighted scores +
  Tier 1 disclaimer trio.
* ``1.1.0`` (Phase 15 C · 2026-05-17) — additive MINOR bump:
  introduces the optional ``inter_snapshot_drift_attribution`` field
  carrying a per-consecutive-pair :class:`DriftAttribution`. A
  pre-1.1.0 consumer that ignores the new field continues to
  function; the new field defaults to an empty tuple when no
  consecutive snapshots are walked. Closes Phase 14 retro §1
  (per-axis drift attribution surface).
* ``1.2.0`` (Phase 16 A · 2026-05-17) — additive MINOR bump:
  introduces the optional ``cumulative_drift_attribution`` field
  carrying a single :class:`DriftAttribution` for the snap-1 →
  snap-N transition (distinct from the consecutive-pair tuple
  above). For 0/1-point timelines the field is ``null``. For
  2-point timelines it equals the single consecutive-pair entry's
  percentages (degenerate but correct). A pre-1.2.0 consumer that
  ignores the new field continues to function. Closes Phase 15
  retro §3 (drift attribution on more envelopes).
"""

# ----- Phase 7 NEW contracts -----

TRUST_SCORE_ALERTS_SCHEMA_VERSION = "1.1.0"
"""``trust_score_alerts`` HTTP response.

Builder: ``backend.app.services.reporting.trust_score_alerts``.

Tier 1 candidate regression-alarm surface: walks a case's timeline
and surfaces snapshot-to-snapshot trust score drops above a
configurable threshold. Carries its own ``schema_version`` separately
from ``TRUST_SCORE_TIMELINE_SCHEMA_VERSION`` because the alarm payload
shape is distinct from the timeline payload shape.

Bump history:

* ``1.0.0`` (Phase 7 C) — initial schema; per-alarm event with
  per-axis WEIGHTED delta breakdown + severity bucket + primary-axis
  shift.
* ``1.1.0`` (Phase 15 C · 2026-05-17) — additive MINOR bump:
  introduces the optional ``drift_attribution`` field on every
  alarm event carrying a :class:`DriftAttribution` (per-axis
  PERCENTAGE deltas + dominant_axis when the absolute delta exceeds
  the SSOT 5.0% floor). A pre-1.1.0 consumer that ignores the new
  field continues to function. Closes Phase 14 retro §1.
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

COHORT_ANOMALIES_SCHEMA_VERSION = "1.2.0"
"""``cohort_anomalies`` HTTP response (Phase 8 E).

Builder: ``backend.app.services.reporting.cohort_anomalies``.

Tier 1 candidate cohort statistical outliers: for each
``*-candidate`` case + each of the 4 trust-score axes, computes
mean + standard deviation across the cohort and flags cases >2σ
from mean on any axis. Severity buckets at 2σ / 3σ / 4σ. Explicit
``claim_impact``: "anomalies surface statistical outliers from
cohort mean; they do NOT diagnose root cause, validate physics, or
authorize Tier 2 promotion."

Bump history:

* ``1.0.0`` (Phase 8 E) — initial schema; z-score outliers across
  4 trust-score axes with 2σ/3σ/4σ severity buckets.
* ``1.1.0`` (Phase 16 B · 2026-05-17) — additive MINOR bump:
  introduces the optional ``cohort_drift_attribution`` field
  carrying a :class:`CohortDriftAttribution` summary (per-case
  drift_attribution between the cohort's latest 2 snapshots +
  cohort-level dominant axis-case pair). Pre-1.1.0 consumers
  that ignore the field continue to function; the z-score view
  is preserved (additive, parallel). The new field defaults to
  ``null`` when fewer than 2 cohort-wide snapshots exist. Closes
  Phase 15 retro §4 (per-axis percentage delta on cohort-scoped
  surfaces) + §6 (cross-axis-comparable cohort signal).
* ``1.2.0`` (Phase 17 A · 2026-05-17) — additive MINOR bump:
  introduces the optional ``cohort_cumulative_drift_attribution``
  field carrying a :class:`CohortDriftAttribution` summary spanning
  the cohort's EARLIEST → LATEST snapshot pair (parallel to the
  Phase 16 B ``cohort_drift_attribution`` which spans the latest
  consecutive pair). Answers the reviewer question "which case
  dominated cohort-wide drift across the WHOLE arc?" distinct from
  "...on the latest pair?". The same SSOT renderer is reused; the
  new field defaults to ``null`` when fewer than 2 cohort-wide
  snapshots exist. Pre-1.2.0 consumers ignoring the field continue
  to function. Closes Phase 16 retro §6 (cohort-scoped cumulative
  drift attribution).
"""

TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.2.0"
"""``trust_score_provenance`` HTTP response (Phase 8 C; Phase 9 B + Phase 10 E MINOR bumps).

Builder: ``backend.app.services.reporting.trust_score_provenance``.

Tier 1 candidate provenance trace: given a case + snapshot label,
walks back to every input file SHA, surfaces the ``formula_version``
that produced the trust score, the recomputed score itself, and the
per-axis breakdown — all from frozen snapshot bytes so the reviewer
gets a deterministic answer to "exactly what produced this 87?"

Bump history:
* ``1.0.0`` (Phase 8 C, commit ``6e19def``) — initial release with
  four input kinds: ``metrics`` / ``convergence`` / ``completeness``
  / ``reproducibility``. (Earlier docstring mentioned "generator
  script" by mistake; the 1.0.0 tuple did not include it. Phase 9 B
  closes that drift by actually shipping it.)
* ``1.1.0`` (Phase 9 B, MINOR per bump policy) — added ``generator``
  as a fifth value to the ``PROVENANCE_INPUT_KINDS`` SSOT tuple. The
  walker emits a ``ProvenanceInput`` row for the generator script
  whether or not the snapshot captured one (``present=False`` when
  the snapshot pre-dates Phase 9 B). Consumers reading the 1.0.0
  fields continue to work because the new row is additive.
* ``1.2.0`` (Phase 10 E, MINOR per bump policy) — added three
  additive fields to every ``ProvenanceInput`` row:
  ``sha256_normalized``, ``normalization_method``, and
  ``normalization_error``. For ``kind == "generator"`` rows whose
  ``.py`` bytes parse successfully via ``ast.parse``, the canonical
  SHA is computed over ``ast.dump(tree, annotate_fields=True,
  include_attributes=False)`` — two generator scripts that differ
  only in comments / whitespace / docstring trivia therefore yield
  the SAME ``sha256_normalized`` even though their raw ``sha256``
  differs. For non-generator rows the three new fields are
  ``None``; for generator rows whose bytes fail to parse,
  ``sha256_normalized`` is ``None`` and ``normalization_error``
  carries the SyntaxError reason. Consumers reading the 1.1.0
  fields continue to work because the three new fields are
  additive. Closes Phase 9 retrospective carry-forward §5.
"""

COHORT_TREND_ANOMALIES_SCHEMA_VERSION = "1.1.0"
"""``cohort_trend_anomalies`` HTTP response (Phase 9 D; Phase 17 C MINOR bump).

Builder: ``backend.app.services.reporting.cohort_trend_anomalies``.

Tier 1 candidate cohort trend outliers: for each ``*-candidate``
case + each of the 4 trust-score axes, computes a least-squares
slope across the case's snapshot timeline (treating point index
``0..N-1`` as the x-axis), and flags negative drift below named
thresholds. Orthogonal to the Phase 8 E z-score anomaly endpoint —
that one walks the cohort's latest snapshot; this one walks each
case's own timeline through time. Severity buckets at slope <=
-0.5 / -1.5 / -3.0 weighted-points per snapshot. Cohort point-count
floor 3. Explicit ``claim_impact``: "trend anomalies surface
within-case degradation over time; they do NOT diagnose root
cause, validate physics, or authorize Tier 2 promotion."

Closes Phase 8 retrospective carry-forward §4.

Bump history:
* ``1.0.0`` (Phase 9 D) — initial schema: per-axis least-squares slope
  in weighted-axis-points per snapshot + severity bucket per event.
* ``1.1.0`` (Phase 17 C · 2026-05-17) — additive MINOR bump:
  every ``TrendEvent`` now carries an additional
  ``percentage_delta_slope: float`` field expressing the same slope
  as a percentage of the axis's total weight per snapshot
  (``raw_slope / TRUST_AXIS_WEIGHTS[axis] * 100.0``). The raw
  ``slope`` field is preserved verbatim (parallel view, NOT
  replacement). The new field makes slopes CROSS-AXIS COMPARABLE:
  a ``-10.0`` percentage_delta_slope means the same relative urgency
  on completeness (50-weight) as on energy_audit (15-weight), even
  though the raw weighted-point slopes differ by 3.33×. Closes
  Phase 16 retrospective carry-forward §1. Back-compat contract: a
  pre-1.1.0 consumer that ignores ``percentage_delta_slope``
  continues to function; the field is computed server-side from the
  SSOT ``TRUST_AXIS_WEIGHTS`` mapping so axis weight changes
  propagate without further bumps.
"""

ADVISOR_CRITIQUE_SCHEMA_VERSION = "1.1.0"
"""``advisor_critique`` HTTP response + on-disk serialization (Phase 11 B; Phase 13 A MINOR bump).

Builder: ``backend.app.services.reporting.advisor_critique``.

Tier 1 candidate AI-advisor critique payload: emits a structured list of
mesh-quality concerns, boundary-condition questions, failure modes to
consider, and unhandled load cases. The advisor is ADVISORY only — never
the authority. Reviewer agency is preserved at every step; the critique
does NOT promote any case to Tier 2 or substitute for the FM-04b sealed
packet.

Closed-enum SSOTs live alongside this constant in the builder module:
* ``ADVISOR_STATUS_TUPLE = ("online", "offline", "stub")`` — pinned by
  ``test_advisor_status_tuple_closed_set``.
* ``FOUR_QUESTION_GATE_KEYS`` — the four LLM-offline / artifacts /
  trustgate / advisor-only question keys every payload answers.
* ``ADVISOR_FORBIDDEN_TOKENS`` — extends the Tier 1 base forbidden list
  with five advisor-specific positive verbs (``production ready``,
  ``certified``, ``approved for service``, ``ASME compliant``,
  ``signed off``); each new token is exercised by a dedicated test
  per Phase 11 anti-gaming guard T:-5.

Bump policy: same MAJOR / MINOR / PATCH scheme as every other
``schema_version`` in this file. Bumping MAJOR requires a retrospective
entry naming the broken consumer; MINOR/PATCH require only a SCORECARD
note.

Bump history:
* ``1.0.0`` (Phase 11 B) — initial schema; four content sections +
  ``four_question_gate`` + Tier 1 disclaimer trio + advisor_status /
  advisor_backend / degrade_reason envelope fields.
* ``1.1.0`` (Phase 13 A · 2026-05-16) — additive MINOR bump:
  introduces the optional ``refused_claims: tuple[str, ...]`` envelope
  field. When the underlying advisor produces content that would
  contain a forbidden positive claim, the offending entry is replaced
  with a structured *marker* string (``"refused: <token>"``) and the
  marker is appended to ``refused_claims``; the original positive
  claim never reaches the rendered surface. Closes Phase 11
  retrospective carry-forward §5. Back-compat contract: a pre-1.1.0
  consumer that ignores the new field continues to function;
  ``refused_claims`` defaults to an empty tuple when absent on the
  source payload.
"""

SIGNOFF_RECORD_SCHEMA_VERSION = "1.2.0"
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

Bump history:

* ``1.0.0`` (Phase 8 A) — initial schema; verdict + reviewer +
  signoff_utc + notes + Tier 1 disclaimer trio.
* ``1.1.0`` (Phase 16 C · 2026-05-17) — additive MINOR bump:
  introduces the optional ``drift_attribution_at_signoff_time``
  field carrying the per-case :class:`DriftAttribution` for the
  case's latest snapshot pair AT WRITE TIME. SERVER-COMPUTED
  (NOT trusted from a client POST body — A:-3 guard). ``null``
  when fewer than 2 snapshots exist for the case at write time.
  Closes the audit-trail gap between "WHAT regressed" (drift
  surface) and "WHO judged it" (signoff record). Pre-1.1.0
  consumers that ignore the field continue to function;
  back-compat reading defaults the field to ``None`` for older
  on-disk records.
* ``1.2.0`` (Phase 17 B · 2026-05-17) — additive MINOR bump:
  introduces the optional
  ``cumulative_drift_attribution_at_signoff_time`` field carrying
  the per-case :class:`DriftAttribution` for the case's
  CUMULATIVE arc (snap-1 → snap-N) AT WRITE TIME. Parallel to the
  Phase 16 C latest-pair pin; the cumulative pin answers "what
  had drifted across the WHOLE arc at signoff time" distinct from
  "what was drifting on the LATEST pair at signoff time".
  SERVER-COMPUTED (the A:-3 anti-gaming guard is extended to BOTH
  drift fields; ``write_signoff_record`` signature accepts NEITHER
  kwarg). ``null`` when fewer than 2 snapshots exist. Pre-1.2.0
  consumers ignoring the new field continue to function;
  pre-1.2.0 on-disk records read the cumulative field as ``None``
  via the back-compat reader. Closes Phase 16 retro §2.
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
