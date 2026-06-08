# Project Blueprints v1 — Phase 11 close (2026-05-16)

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

These 8 images are the visual anchor set for the project's final-state vision,
generated post-Phase 11 close from the prompts in the
`docs/CLAUDE_CODE_HANDOFF_PROMPT.md` follow-up conversation. They were
audited and approved as Phase 12+ visual reference (see chat history
2026-05-16, "8 blueprints visual review").

These blueprints are **vision artifacts**, not engineering deliverables.
They reflect the project's *target state*, NOT the state of the repo at the
time of upload. A future divergence between an image and the live code is
expected and should be resolved by either (a) extending the code to match
or (b) regenerating the image to match the new code reality.

## When to reference each image

| # | File | When to reference | When NOT to reference |
|---|------|-------------------|------------------------|
| 1 | `blueprint_01_system_architecture.png` | New conversation / new phase opening; project elevator-pitch | Per-slice implementation work |
| 2 | `blueprint_02_reviewer_workbench_ui.png` | UI/frontend slice planning; UI-SPEC visual diff baseline | Backend service work |
| 3 | `blueprint_03_data_flow_pipeline_dag.png` | Writing a new service or route; sanity-check pipeline placement | UI work; pure refactor |
| 4 | `blueprint_04_advisor_not_driver_constellation.png` | Any time someone proposes "let the AI do X automatically" | Routine debugging |
| 5 | `blueprint_05_trust_chain_cascade.png` | Schema-version bump; trust score formula change; provenance work | Pure UI work |
| 6 | `blueprint_06_analysis_type_coverage_matrix.png` | Phase-level planning; deciding which analysis type to ship next | Slice-level work |
| 7 | `blueprint_07_cohort_dashboard.png` | Cohort surface work; multi-case feature planning | Single-case work |
| 8 | `blueprint_08_day_in_the_life_workflow.png` | "Who is this for / why are we doing this" reality checks | Tactical code review |

## Known gaps between v1 vision and Phase 11 close reality

These gaps drive Phase 12+ scope. They are **deliberate** and not blueprint defects:

* Image #06 shows 4 SHIPPED analysis types (ballistic / linear_static_pv /
  explicit_dynamics / modal). At Phase 11 close, only ballistic and
  linear_static_pv have **real end-to-end runnable cases**;
  explicit_dynamics and modal have rubric slots but no real cases.
  **→ Phase 12 ships the modal real case + a 2nd PV case.**
* Image #07 shows a cohort dashboard with 8 cases, distributed across
  buckets, with real alarms firing. At Phase 11 close, the cohort has 1
  real case (`cylinder-pv-candidate`); alarms have correct code paths but
  no real data to trigger them. **→ Phase 12 builds 4 real cases + 3
  snapshots so the dashboard surfaces real alarms.**
* Image #02 truth chain footer shows 5 nodes; the real audit chain
  involves 5 input kinds × possibly per-snapshot deltas. **→ Phase 12+
  may extend the footer; not blocking.**
* Image #06 shows fatigue + thermal-structural as PLANNED rows. These are
  Phase 13+ candidates, not Phase 12 scope.

## Version + bump policy

This is `v1`. A future blueprint regeneration (e.g., after Phase 12 close)
lands as `v2_phase12_close/` under the same directory pattern. Old
versions are **never deleted** — they preserve the historical north-star
record. A README cross-reference table at `.planning/blueprints/README.md`
indexes the versions.

## Reference

Prompts that generated these images are in the chat history (2026-05-16
"8 蓝图 prompt" conversation). If a regeneration is needed, replay those
prompts via `gpt-image-1` / equivalent.
