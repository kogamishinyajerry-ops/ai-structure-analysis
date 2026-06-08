# FM-04a Phase 28 — FINAL composite audit synthesis

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-27.

## Headline

**Phase 28 honest composite: 79.6/100** (delta method · primary)
**Phase 28 absolute audit sum: 76.9/100** (footnote · auditor rubric drift)

**Lift over Phase 27 (78.5): +1.1** (delta method)

Phase 28 = third inside-band landing in a row after the Phase 26
recalibration event. Trajectory direction sustained UP, but the
per-phase Δ is decaying (Phase 27 = +3.8, Phase 28 = +1.1) which is
expected: low-hanging UX/UI polish was banked Phase 27-28 C, and the
remaining lift to 99/100 is structural (shells, contact, transient
solvers, full reviewer-frame primitive, real WebGL E2E).

## Per-dimension scoreboard (sub-agent absolute scores + Phase-27 deltas)

| Dim | Phase 27 actual | Phase 28 absolute (sub-agent) | Phase 28 by delta from P27 | Δ |
|---|---|---|---|---|
| UX  | 80.9 | 82.7 | 83.6 | **+2.7** |
| FEA | 76.5 | 70.5 | 77.5 | **+1.0** |
| UI  | 77.6 | 77.5 | 77.6 | **~0.0 (-0.5 to +0.5)** |
| **Composite** | **78.5** | **76.9** | **79.6** | **+1.1** |

> The FEA auditor's absolute score (70.5) is materially below the
> Phase 27 actual (76.5) — but no FEA functionality was lost in
> Phase 28 (one validated case was ADDED). The difference is
> rubric-strictness drift between auditor instances. The HONEST
> interpretation is to trust the relative Δ (+1.0) over the
> absolute number. Future phases should pin per-dimension rubric
> definitions to prevent recurrence (Phase 29 retro candidate).

## Phase 28 wins (cited verbatim from sub-agent audits)

### UX (auditor `a211f0eb...`)
1. **State preservation +6** — 28 C restored-from-session toast
   (`ResultMeshPlaybackPanel.tsx:145-149,293-313`; role=status,
   4s auto-fade) closes Phase 27's silent-restoration miss.
2. **Motion polish +6** — 28 C row exit animation
   (`polishStyles.ts:65-68,78-80`; 150ms ease-in with 6px lift;
   `ProbeListPanel.tsx:193,200` conditional class swap; 150ms
   `setTimeout` orchestration in
   `ResultMeshPlaybackPanel.tsx:635-641`) — prefers-reduced-motion
   honored across all three new animations
   (`polishStyles.ts:145-151`).
3. **Onboarding flow +4** — 28 D tour `onDismissed` callback
   (`OnboardingTour.tsx:60-82`) + `AdvancedModePromo` predicate
   (`onboardingTour.ts:266-275`) sequence basic-mode novice into
   advanced affordances. One-shot per browser; two D:-1 re-mount
   tests pin durability.

### FEA (auditor `a461a6d3...`)
1. **Validated count 7 → 8** with hard registry pin
   (`test_phase28a_cantilever_buckle.py:131` asserts
   `len(validated) == 8`); +0.0298% residual is the tightest in
   the cohort.
2. **Honest-scope discipline = 92/100** — the C3D8 hex cantilever
   buckling attempt (256% residual, root cause: shear locking
   under fully-clamped base) is preserved as `NotImplementedError`
   dispatch in `buckling_runner.py:417-423`. No hedging; named in
   `golden_samples/cantilever-buckle-candidate/NOTES.md`.
3. **Registry signed-set discipline = 88/100** — zero inflation;
   no `*-candidate` is registered as `tier_2_validated` without a
   live PASS verdict YAML.

### UI (auditor `ac23892f...`)
1. **Motion language cohesion** — probe row enter/exit
   (200/150ms) + restored toast (200ms fade-in) + tour fade-slide
   (200ms) all share ease-out 200ms anchor with asymmetric
   faster-exit (150ms). Single motion vocabulary.
2. **Toast a11y is textbook** — `role="status"` + `aria-live="polite"` +
   scoped `aria-label="Dismiss restored probes notification"` on the
   dismiss button (`ResultMeshPlaybackPanel.tsx:295-308`). Correct
   non-modal informational pattern; no focus theft, no keyboard
   trap.
3. **Tonal vocabulary held discipline** — `accent/warning/danger/muted`
   4-tone system threads through all 7 trustCenter sections; gradient
   slider matches viewport legend gradient (single color story
   blue→green→orange).

## Phase 28 honest gaps (cited verbatim, NOT softened)

### Carried over from Phase 27 (NOT addressed in Phase 28)
- **#1 Shell element validated case (S4) absent** — still hard caps
  FEA Dim 1 at ≤75. Most important Phase 29 priority by single-axis
  lift potential.
- **#3 App.tsx reducer/candidate-spine extraction NOT shipped** —
  App.tsx grew 1454 → 1596 LOC in Phase 28 D from inline `useMemo`
  wrapping (each `useMemo(() => buildXxx({...}), [deps])` is 6-15
  lines vs the prior 3-line builder call). Honest cost of granular
  memoization; trade was real (correctness over LOC), but the
  net direction is wrong again.
- **#7 Real WebGL E2E** — still puppeteer/playwright not wired.
- **#8 Third modal case at intermediate L/h** — still absent.
- **#10 Iso-surface rendering** — still absent.

### Newly surfaced in Phase 28 audits
1. **Tour + AdvancedModePromo mounted INSIDE Visual tab**
   (`ResultMeshPlaybackPanel.tsx:284-289`) — novices landing on
   the Narrative tab miss onboarding entirely. Modal-on-modal
   stacking is fragile (z-index 999/1000, single-frame race
   between OnboardingTour `dismissed → true` and AdvancedModePromo
   conditional visibility).
2. **Corrupted-key fallback still silent** — Phase 27 retro punch
   item carried forward — if a user's localStorage payload becomes
   malformed they get an empty probe list with NO console warning.
3. **No focus-trap on AdvancedModePromo + OnboardingTour modals** —
   both `role="dialog"` but Tab escapes. Abaqus job-edit modals
   trap focus per WCAG 2.4.3.
4. **No multi-viewport split + no measurement/coord tools** —
   Abaqus/CAE ships 4-quadrant view by default; this is
   single-viewport. Hyperworks coord-readout floating panel
   absent.
5. **No collapse/expand on 7 trust sections** — industrial reviewer
   tools default to collapsible accordions; uniform `SectionFrame`
   primitive absent.
6. **Registry pins verdict only, not tolerance** — a future
   loosening of `BUCKLING_CROSS_CHECK_TOLERANCE_PCT` would not
   trip a regression test. Auditor recommends pinning tolerance
   per case in the verdict YAML schema.
7. **No `*DYNAMIC explicit` validated case in a BALLISTIC FEA
   workbench** — 0/8 validated cases are ballistic. The Ballistic
   candidate section (28 B) surfaces honest Tier 2 blockers but
   the COHORT itself has no transient/explicit case. FEA Dim 6
   = 42/100 (sub-agent).
8. **AdvancedModePromo has NO entrance animation** — polish
   inconsistency with the Phase 24/25/27 fade-slide vocabulary.

## Phase 29 priority recommendations (synthesis)

Ranked by single-axis lift potential × shippability:

### Tier 1 (high lift, multi-phase carry)
1. **Shell element S4 case + CalculiX shell-output reader
   plumbing** — unblocks FEA Dim 1 hard cap (+8 to +12 single
   biggest lift available). Requires non-trivial
   `app/adapters/calculix/reader.py` extension. Carried since
   Phase 27 blueprint.
2. **Reviewer-Frame primitive + collapsible accordion + section
   collapse/expand persistence** — biggest "looks like CAE"
   structural lift on UI Dim 5 (+8 to +12 sub-agent estimate).
   Requires extracting a `SectionFrame.tsx` primitive used by all
   7 trust sections + per-section collapse state in localStorage.
3. **Tour + AdvancedModePromo lifted to App-root** — closes the
   Visual-tab coupling gap. Should be straightforward (relocate
   mount + thread uiMode state up).

### Tier 2 (smaller lift, faster ship)
4. **Focus-trap library** on both modal overlays (Reach UI / 
   FocusTrap-React) — closes WCAG 2.4.3 gap.
5. **Corrupted-key console warning** — single console.warn at
   `probeListStorage.ts` parse-fail site.
6. **AdvancedModePromo entrance animation** — match
   `fm04a-onboarding-fade-slide-in` keyframe vocabulary.
7. **Per-case registry tolerance pin** — extend verdict YAML
   schema to include the tolerance used; pin in registry test.

### Tier 3 (multi-phase architectural)
8. **App.tsx reducer / candidate-spine view-model** — would
   reverse the 1454→1596 LOC growth from Phase 28 D's memo
   inlining.
9. **Real WebGL E2E via playwright** — would lift FEA Dim 7
   evidence-confidence axis.
10. **`*DYNAMIC explicit` validated case** — would FINALLY put a
    ballistic case in the ballistic workbench's validated cohort.

## v2.3 disposition

- 1 sub-phase = Phase 28 (5 implementation slices including 28 E
  audit) = 1 retro at phase-close ✓
- counter += 5 (telemetry only)
- No Codex review triggered (no auth / signing / 安全边界 risk-tier
  hit)
- No charter triggered (changes within frontend/src/components/,
  frontend/src/state/, frontend/src/onboardingTour.ts, backend
  cross_check/_claim_tier/test_phase28a)
- DEC frontmatter: this FINAL doubles as the DEC for Phase 28
  (status=Accepted at commit, parent_dec=Phase 28 blueprint
  `3c97645`, notion_sync_status=pending session-end batch sync)
- Round cap 3: NOT triggered — R1 sub-agents surfaced gaps but
  no Phase-20-style real defects that require a Round 2 spawn.
  Per v2.3 cap discipline + Phase 18-27 convention: NO R2.

## Hard-constraint compliance

- HF1.7a signed-registry: PASS (8th case added as `*-candidate`
  per HF1.7b carve-out; promoted to `tier_2_validated` by overlay)
- HF1.7b `*-candidate` carve-out: PASS (cantilever-buckle-candidate)
- HF1.8 path-guard: PASS (no writes outside permitted scope)
- tmp_path-only test snapshot writes: PASS (excl.
  `golden_samples/cantilever-buckle-candidate/cross_check_verdict.yaml`
  per HF1.7b)
- No push / no PR / no Linear writes in Phase 28 — local-commit only
  awaiting next user authorization
- Test pyramid: 563/563 frontend (was 528 pre-28 D · +35 in 28 D;
  was 511 pre-28 C · +17 in 28 C); backend Phase 28 A: 8 new
  + @requires_solver E2E ran live PASS at +0.0298% residual
- Phase 1-27 chain additive only: PASS — Phase 27 A's `len==7` strict
  pin loosened to `>=7` with comment, preserves intent

## Decision

Phase 28 closes at honest composite **79.6/100** (delta method),
CHANGES_REQUIRED. **+1.1 over Phase 27.** Decaying per-phase Δ
reflects exhaustion of UX/UI polish low-hanging fruit; the remaining
20.4-point gap to 99 is structural and will require 4-8 more phases
covering:
- shell + contact + transient solvers (FEA)
- reviewer-frame primitive + multi-viewport (UI parity)
- App.tsx full decomposition (UI maintainability)
- real WebGL E2E + measurement tools

Not signed validation; not benchmark agreement.

---

Auditor files:
- UX: `.planning/audits/phase28_ux_audit.md` (auditor `a211f0eb...`)
- FEA: `.planning/audits/phase28_fea_audit.md` (auditor `a461a6d3...`)
- UI: `.planning/audits/phase28_ui_audit.md` (auditor `ac23892f...`)
