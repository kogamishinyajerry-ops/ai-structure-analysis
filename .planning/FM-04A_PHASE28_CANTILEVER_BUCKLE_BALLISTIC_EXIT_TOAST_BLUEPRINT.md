# FM-04a Phase 28 — Cantilever buckling + Ballistic extraction + Polish closure · BLUEPRINT

> Authorized by user 2026-05-17. 6 commits planned (blueprint + 5 slices).
> 绝对诚实客观 contract carried verbatim from Phase 18-27.

## Phase 27 → Phase 28 lift target

| Dimension | Phase 27 R1 (honest) | Phase 28 R1 projection |
|---|---|---|
| UX | 80.9/100 | 83.0-84.5 (+2-3) |
| FEA | 76.5/100 | 78.5-80.0 (+2-3) |
| UI | 77.6/100 | 80.0-81.5 (+2-3) |
| **Composite** | **78.5/100** | **80.5-82.0 (+2-3)** |

Honest expectation: the 99 target stays multi-phase. Phase 28 aims
to close 4 Phase 27 carry-forwards (Ballistic extraction, row exit
animation, restored toast, tour auto-promote) AND ship an 8th
validated case via the cheapest available analytical path.

## Slice plan (5 implementation slices + audit)

### Slice A — 8th validated case · cantilever Euler buckling (k = 2.0)

**Why**: Phase 22 A validated Euler buckling at pinned-pinned (k=1.0)
on a B31 beam. A second buckling case with a DIFFERENT effective-
length factor proves the `P_cr = π²EI/(kL)²` formula's k-factor
discipline (not just the numeric value at one BC). Cantilever
buckling is the easiest second BC: just remove the tip lateral
constraint. Same B31 element, same `*BUCKLE` solver kind, different
analytical (k=2.0 → P_cr = π²EI/(4L²), quarter of pinned-pinned).

**Plan**:
- Reuse Phase 22 A's `buckling_runner` with a new
  `end_condition: 'cantilever'` parameter.
- Add `_write_cantilever_buckle_inp` modeled on the existing pinned-
  pinned composer, removing the tip DOF 2, 3 constraints (tip is
  completely free; only the base is clamped).
- Add `EndCondition` literal `'cantilever'` to the analytical
  helper's k-factor map (k=2.0).
- New geometry `golden_samples/cantilever-buckle-candidate/data/`
  with a single B31 beam clamped at x=0 + unit compressive load at
  x=L.
- Tolerance: 10% (inherited from Phase 22 A; Euler buckling on B31
  is well-conditioned).

**Validated count**: 7 → **8**.
**FEA Dim 2**: 80 → 84 (+4 from 8th case).
**FEA Dim 3** (envelope honesty): +2 from cross-BC k-factor
verification (pinned-pinned k=1.0 + cantilever k=2.0 covers two
points of the k-factor family).

### Slice B — Ballistic candidate section extraction

**Why**: Phase 26 D extracted 5 of 7 sections; Phase 27 B added
Blueprint target as the 6th. Ballistic candidate (~11 items inline)
is the LAST section to extract. Closes the App.tsx Trust Center
view-model decomposition AND continues the LOC trajectory downward.

**Plan**:
- Add `buildBallisticSection(ctx)` to `trustCenterViewModel.ts`.
- Context includes ~6 derived locals: `candidateBallistic`,
  `ballisticInitialVelocitySummary`, `ballisticResidualVelocitySummary`,
  `ballisticPerforationSummary`, `ballisticPerforationTone`,
  `ballisticEnergySummary`, `ballisticEnergyTone`,
  `ballisticAnimationSummary`, `ballisticTimeStepStudySummary`,
  `ballisticTimeStepStudyTone`, `ballisticTier2BlockerSummary`,
  `humanizeStatus`. Wider context than Blueprint, but tractable.
- Pure-function tests for tone derivations and item count.

**Target**: App.tsx 1454 → ~1430 (-24 LOC). Still NOT < 1300, but
trajectory continues DOWN.

### Slice C — Probe-list row EXIT animation + restored-from-session toast

**Why**: Phase 27 C shipped row ENTRANCE animation; exit was
documented as honest scope reduction. Phase 28 C closes it. Phase
27 D ships silent probe-list restoration; users may not notice.
Phase 28 C adds a "Restored 3 pinned probes from your last session"
toast that fades after 4 seconds.

**Plan**:
1. **Row exit animation**: Track a `exitingRowLabel: number | null`
   state in ResultMeshPlaybackPanel. On `onRemove(label)`, set the
   exiting label first; after 150ms (animation duration), call the
   actual `setProbeList(s => removeProbeEntry(s, label))`. The
   exiting row carries a `.fm04a-probe-row-unmount` class that
   triggers a 150ms ease-in fade-out + slide-up. prefers-reduced-
   motion: reduce → instant removal.
2. **Restored toast**: On case load, if `loadProbeList(caseId)`
   returns ≥ 1 entry, show a toast `Restored N pinned probe(s) from
   your last session`. Auto-fades after 4 seconds. Dismissable
   with click. prefers-reduced-motion honored.

**Anti-gaming guard E:-1**: exit-animation timing MUST NOT delay
the actual state update beyond 200ms. Pinned by test asserting
removeProbeEntry called within 200ms of remove button click.

### Slice D — Tour auto-promote sequencing + trust-strip memoization

**Why**: Phase 25 D + 27 D ship the tour but never sequence the
"OK you're done with the tour, now consider switching to Advanced
mode for the full toolkit". Phase 28 D closes this. Trust-strip
memoization is the lowest-effort follow-on to Phase 27 B's view-
model extraction — wraps the context bundles in `useMemo` so
the panel re-renders only when inputs actually change.

**Plan**:
1. **Tour auto-promote**: After the tour completes (or is
   dismissed), if `uiMode === 'basic'` AND the user has never
   seen the "auto-promote" prompt (`fm04a.tour.advanced-prompt.v1.shown`),
   show a brief prompt with two buttons: "Stay in Basic" /
   "Switch to Advanced". Persist the shown flag either way.
2. **Memoization**: Wrap each section's context object in
   `useMemo(...)`. The dependencies are the underlying derived
   locals (~10 per section). React skips the section rebuild when
   identity is preserved.

### Slice E — 3 testing sub-agents + audits + FINAL + retro + STATE

Same discipline as Phase 18-27. R1 only unless real defects.

## Test budget

| Slice | Backend | Frontend | Live ccx |
|---|---|---|---|
| 28 A | ~10 | 0 | yes |
| 28 B | 0 | ~8 | no |
| 28 C | 0 | ~12 | no |
| 28 D | 0 | ~10 | no |
| 28 E | 0 | 0 | no |
| **Total** | **~10** | **~30** | **1** |

Phase 28 total target: **~40 new tests, 0 regressions, 6 commits**.

## Hard constraints (绝对诚实客观 + HF discipline preserved)

- HF1.7a/b/8 + tmp_path-only test writes (except new
  cantilever-buckle-candidate verdict YAML).
- No push, no PR, no Linear/Notion writes unless authorized at
  session end.
- Phase 1-27 chain additive only. Test loosening preserves intent.
- prefers-reduced-motion honored across all NEW motion + audited
  retroactively for Phase 25 D / 27 C affordances.
- LOC measurements reported verbatim — if Slice B does not shrink
  App.tsx, document the result.
- Round 2 only if R1 surfaces real defects (v2.3 cap).

## Phase 29 candidate punchlist (carry-forward from Phase 27)

These items remain open after Phase 28:
1. **Shell element validated case (S4) WITH CalculiX reader plumbing**
   — still Phase 29 priority #1 if Phase 28 ships polish-only.
2. Real WebGL E2E via puppeteer/playwright (8 phases open).
3. Third modal case at intermediate aspect ratio (L/h = 15-20).
4. Iso-surface rendering.
5. Contact-mechanics validated case (Hertz).
6. Transient validated case (`*DYNAMIC`).
7. App.tsx reducer / candidate-spine view-model (full decomposition).
8. CalculiX static viewer σ-tensor path.
9. prefers-reduced-motion retroactive audit across all motion.

Not signed validation; not benchmark agreement.
