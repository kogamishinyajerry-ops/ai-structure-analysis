# Phase 15 B TAA — slice audit

Commit: 51799ac
Date: 2026-05-17
Auditor: independent general-purpose agent (Opus 4.7 1M, no prior knowledge of the implementation conversation)

## Scope

Slice B of FM-04a Phase 15: 3-snapshot degradation arc across the explicit_dynamics cohort (canonical + stiff + energy-leak).

Artifacts reviewed:
* `.planning/FM-04A_PHASE15_BLUEPRINT.md` §3.B
* `tests/test_phase15_explicit_dynamics_cohort_arc.py` (415 lines, 11 tests)
* (delta only — no source changes; tests exercise existing `cohort_snapshot.write_cohort_snapshot` + `trust_score_timeline.build_trust_score_timeline` against tmp_path)

Verification:
* `uv run pytest tests/test_phase15_explicit_dynamics_cohort_arc.py -v` → 11 passed
* `uv run pytest tests/ -q` → 2413 passed, 7 skipped, 3 warnings (baseline 2402 + 11 = 2413; exact match)
* Real `reports/snapshots/` post-run: still the 5 pre-existing 2026-05-16 entries; no 2026-05-17 snapshot labels leaked into the real tree.
* `golden_samples/rod-wave-impact-energy-leak-candidate/data/ballistic_metrics.json` post-run: `energy_audit.status == "open_residual"` (Phase 15 A canonical state preserved; clean variant was written under tmp_path `phase15b_snap1_clean/`).
* `git diff HEAD~1 HEAD -- golden_samples/` → empty (zero fixture mutations).
* Independent TAA bucket-math reproduction (separate tmp_path repo + live `build_trust_score_timeline`):
  * canonical: 94 / 94 / 94 → HEALTHY × 3
  * stiff:     94 / 94 / 94 → HEALTHY × 3
  * leak:      94 / 55 / 47 → HEALTHY → WATCHING → REGRESSED
  * Per-snapshot bucket counts: {3,0,0} / {2,1,0} / {2,0,1} — exactly as pinned by the tests.
  * Snap-2 leak trust 55 sits in `[WATCHING_TRUST_SCORE_MIN=50, HEALTHY_TRUST_SCORE_MIN=80)`; snap-3 leak trust 47 < 50.

## Sub-rubric scoring

### M — Methodology (12/12)
* `EXPLICIT_DYNAMICS_COHORT_CASES` is a module-level `tuple[str, ...]` SSOT (lines 59–63); `SNAP_1/2/3_LABEL` are module-level typed string constants (lines 66–68).
* Snapshot writer reads schema_version via `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` imported from `app.services.reporting._schema_versions` (line 40–42, asserted at lines 261 + 398). Confirmed at runtime: `schema_version == "1.3.0"`.
* Bucket thresholds imported from `app.services.reporting.cohort_executive_summary` (`HEALTHY_TRUST_SCORE_MIN=80`, `WATCHING_TRUST_SCORE_MIN=50`) — never hand-coded.

### T — Testing (15/15)
* 11 test functions (`grep -c "^def test_"` = 11; rubric floor 10).
* Three-snapshot existence + Tier 1 trio per envelope: `test_three_snapshots_present_with_tier1_trio`.
* Chronological labels: `test_snapshot_labels_chronological`.
* Per-snapshot bucket counts EXACT (==): `test_snap1_all_three_healthy` `=={3,0,0}`, `test_snap2_two_healthy_one_watching` `=={2,1,0}`, `test_snap3_regressed_count_at_least_one` `=={2,0,1}` (with an additional `>=1` floor pin for the trigger semantics).
* Monotonic degradation pin: `test_arc_is_monotonically_degrading` asserts `snap1 > snap2 > snap3`.
* `regressed_count` fires on snap-3: covered + reproduced independently (47 < 50).
* Timeline 3 points / case oldest-first: `test_timeline_has_three_points_per_case`.
* SSOT schema_version pin per snapshot: `test_every_snapshot_uses_ssot_schema_version`.

### C — Coverage (12/12)
* Tier 1 disclaimer trio re-audited per snapshot envelope: `test_three_snapshots_present_with_tier1_trio` asserts `claim_tier == "Tier 1 engineering candidate"` and that `claim_boundary` contains both `"not_signed_validation"` and `"not_benchmark_agreement"` markers at every label.

### A — Anti-gaming (8/8)
* **A:-3 enforced**: bucket transitions are derived by the helper `_per_snapshot_bucket_counts(repo, label)` (lines 347–359), which calls `build_trust_score_timeline(case_id, repo)` per case and bucketizes against the SSOT thresholds. The hand-rolled `SNAPSHOT_MANIFEST.json` payload is never read to determine bucket membership — only the live timeline route is. The tests `test_snap1/2/3_*` consume the helper output.
* T:-4 corroborated: per-snapshot counts asserted with `==`, not `>=`. (The `>=1` line in `test_snap3_regressed_count_at_least_one` is an additional floor on top of the exact pin one line below, not a substitute.)

### E — Evidence (8/8)
* Phase 12 D modal-cohort multi-snapshot pattern is explicitly cited in the module docstring (lines 5–7) and the seeded_repo fixture mirrors it (copy `golden_samples/` into tmp_path, drive generators, write snapshots into `tmp/reports/snapshots/`).
* No writes to the real `reports/snapshots/`: verified pre- and post-run (still 5 × 2026-05-16 entries; zero 2026-05-17 entries).
* `golden_samples/*-candidate/` NOT mutated: verified by `git diff HEAD~1 HEAD -- golden_samples/` empty and live post-run `energy_audit.status == "open_residual"`. Clean variant for snap-1 is written into a sibling tmp dir (`phase15b_snap1_clean/...`).
* Minor: the seeded_repo fixture invokes the 3 generator scripts against the **real** `REPO_ROOT` (lines 85–94) before copying fixtures into tmp_path. This is the documented Phase 12 D pattern (project_state/ is gitignored, so generators must run live), and it does not mutate `golden_samples/` (verified). Noted as observation, not a finding.

### V — Verification (8/8)
* Full backend sweep stays green at 2413 passed (baseline 2402 + 11 slice-B = 2413; exact). 7 skipped is identical to baseline. Zero regressions.

## Forbidden-token scan

`grep -niE "signed validation|benchmark agreement|production" tests/test_phase15_explicit_dynamics_cohort_arc.py` → 4 hits at lines 3, 153, 169, 172. All occur in `not <claim>` negation form within the Tier 1 disclaimer trio (or its synthesized rationale strings). Zero unconditional / promotional uses. PASS.

## Findings

None. No HIGH, no MEDIUM, no LOW.

Observation only: the seeded_repo fixture's reliance on `subprocess.check_call` against `REPO_ROOT/scripts/gen_*_deck.py` couples slice B to slice A's generator scripts running cleanly on the host. If those generators ever introduce side effects to `golden_samples/`, the slice-B isolation guarantee could degrade. Currently the generators only write into `project_state/` (gitignored) and `golden_samples/` (idempotent re-writes that match what's already on disk), so this is theoretical, not a present hazard.

## Score

| Axis | Score | Floor | Status |
|------|-------|-------|--------|
| M    | 12/12 | 10    | PASS   |
| T    | 15/15 | 10    | PASS   |
| C    | 12/12 | 10    | PASS   |
| A    | 8/8   | 6     | PASS   |
| E    | 8/8   | 7     | PASS   |
| V    | 8/8   | 7     | PASS   |
| **Total** | **63/63** | 60 | **PASS** |

## Verdict

**APPROVE** — 63/63, zero HIGH, zero MEDIUM, zero LOW. All axes at ceiling. Stop condition satisfied.
