# FM-04a · Phase 29 retro · shell S4 + SectionFrame + App-root tour + tier-2 fixes + RUBRIC.md

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Per 绝对诚实客观 contract carried verbatim
> from Phase 18-28.

## Scope

| Slice | What landed | Commit | Tests |
|---|---|---|---|
| 29 blueprint | 5-slice plan, projection band 82.5-85.0 | `6ecd65b` | — |
| 29 A | 9th tier_2_validated case `plate-ss-shell-candidate` — FIRST S4 shell case; +0.4881% residual; C3D8 cantilever attempt preserved (Phase 28 A); CCX sign-convention oddity documented in NOTES.md | `87badbe` | 25 backend |
| 29 B | SectionFrame primitive + collapsible accordion + useTrustSections hook; App.tsx 1667 → 1421 LOC (-246, reverses Phase 28 D growth) | `5456e82` | 35 frontend |
| 29 C | OnboardingTour + AdvancedModePromo lifted to App-root; useFocusTrap hook (WCAG 2.4.3) on both modals; Promo entrance animation matching tour vocabulary | `8d3baed` | 23 frontend |
| 29 D | Corrupted-key console.warn; per-case registry tolerance pin (12 tests); `.planning/audits/RUBRIC.md` v1.0 | `4dd6d38` | 12 backend + 6 frontend |
| 29 E | 3 sub-agent audits (UX 89.2 / FEA 77.5 / UI 86.0); FINAL synthesis; retro; STATE | (this commit) | — |

**Total: 101 new tests** (37 backend + 64 frontend); **628/628
frontend PASS**; backend Phase 29 A E2E ran live PASS at +0.4881%.

## Composite trajectory (honest)

| Phase | Honest composite | Per-phase Δ |
|---|---|---|
| 22 | ~75 | baseline |
| 23 | ~76 | +1 |
| 24 | ~75 | -1 |
| 25 | ~72.2 | -3 |
| 26 | 74.7 | +2.5 (honest re-baseline) |
| 27 | 78.5 | +3.8 |
| 28 | 79.6 | +1.1 |
| **29** | **84.23** | **+4.63** |

**Phase 29 is the fourth inside-band landing in a row** and the
LARGEST per-phase Δ since Phase 27. The "structural load-bearing
lifts" thesis (shells + reviewer-frame primitive) was correct;
the decaying-Δ pattern of Phase 28 (+1.1) was an exhaustion
signal that Phase 29 reversed by tackling two structural gaps
simultaneously.

## What worked

### Structural lifts beat polish accumulation
- **S4 shell case** unlocked a Dim-1 hard cap that had held since
  Phase 18 (≤75). Just shipping the first non-solid non-beam
  element class moved FEA Dim 1 from 75 → 80 anchor (rubric exact).
- **SectionFrame primitive** simultaneously closed 3 audit gaps:
  no collapse/expand, no uniform primitive, App.tsx monolith.
  Cascading effect across UI Dim 2 / Dim 5 / Dim 6.
- The +4.63 composite Δ reverses Phase 28's decay (+1.1) — proof
  that the right phase scope is "ship TWO structural lifts" not
  "accumulate more polish."

### Reconnaissance before commitment
- Phase 29 A reconnaissance flagged that the "CalculiX shell-
  output reader plumbing" Phase 27 retro feared was actually a
  stress-tensor concern, not a displacement-read gap. Reading
  `backend/app/adapters/calculix/reader.py:377` confirmed S4 was
  already recognized; live ccx ran on the FIRST attempt at +0.49%
  residual. **Two phases of unnecessary deferral closed in one
  reconnaissance pass.**

### useTrustSections custom hook = LOC discipline win
- Phase 28 D inlined granular per-section useMemo (+141 LOC) for
  correctness — right call at the time. Phase 29 B encapsulated
  the orchestration in a hook with IDENTICAL memoization semantics
  but 240 fewer LOC of App.tsx. App.tsx 1667 → 1421, **net 33 LOC
  below the Phase 27 B record (1454)**. Pattern reusable for any
  future hook extraction.

### Rubric v1.0 closed the sub-agent drift
- Phase 28 E saw absolute vs delta methods disagree by 2.7 points
  (76.9 abs vs 79.6 delta). Phase 29 E (rubric v1.0 in effect):
  absolute 84.23 vs delta 84.27 → **0.04 point gap**. The rubric
  is doing its job. This is a load-bearing process improvement.

### Honest C3D8 → B31 pivot pattern reused (Phase 29 A's NOTES.md)
- Phase 28 A's "fail in-tree, document the rejection, regression-
  pin the NotImplementedError" pattern was applied to Phase 29 A's
  CCX S4 sign-convention oddity. The runner reports observed +z
  vs analytical -z; magnitudes agree at 0.49%. NOTES.md documents
  this honestly rather than silently fixing it with abs(). FEA
  Dim 3 (honest-scope discipline) anchored at 95 — second-highest
  axis in the entire audit.

## What didn't work

### Phase 29 A's first edit pass was wrong
- Initial Edit operation on App.tsx commented out the START of the
  Phase 28 D inline block but left the body live (would have caused
  a duplicate-declaration TypeScript error if not caught). Recovery
  used a Python helper script to atomically splice out lines 916-
  1163. Pattern lesson: **for >100-line deletions in TSX, use a
  helper script with explicit line-boundary assertions, not
  multi-Edit-call comment-out attempts.**

### Test loosening lag
- Phase 28 D's structural App.tsx scan tests (`it.each(...)`)
  pinned the inline useMemo block patterns. After Phase 29 B moved
  those to the hook, 9 of those tests broke. Fix was straightforward
  (relocate the scan target to the hook source), but the regression
  surfaced AFTER the Phase 29 B commit instead of being pre-
  identified during planning. **Lesson: structural source-scan
  tests should include the file path as a parameter so a phase
  refactor only needs to update one constant.**

### Phase 28 E inline LOC pattern outlived its usefulness
- Phase 28 D's inline `useMemo(() => buildXxx({...}), [deps])`
  was 6-15 lines per section. Phase 29 B extracted to a hook
  saving 240 LOC. The lesson: **when a pattern requires repeated
  20-line stanzas to maintain, that pattern is asking to be
  hooked.** Should have shipped useTrustSections in Phase 28 D
  alongside the memoization; would have saved one phase of LOC
  growth.

### FEA Dim 6 still floors the composite
- Phase 29 A shipped a real structural lift, BUT the FEA composite
  was flat (+0.0) because Dim 6 (Ballistic Tier-2 readiness) is
  anchored at 50 — no `*DYNAMIC` validated case in a ballistic-FEA
  workbench. This is honest: a ballistic-FEA workbench WITHOUT a
  ballistic case has a real ceiling. Phase 30's first `*DYNAMIC`
  case would unlock Dim 6 from 50 → 75.

## v2.3 disposition

- 1 sub-phase = Phase 29 (5 implementation slices + 29 E audit) =
  1 retro at phase-close ✓
- counter += 5 (telemetry only)
- No Codex review triggered (no auth / signing / 安全边界 hit)
- No charter triggered (changes within
  backend/app/services/cross_check/, backend reporting/,
  golden_samples/, backend tests/, frontend src/components/,
  frontend src/state/, frontend test/, .planning/audits/)
- DEC frontmatter 6-field minimum: this retro doubles as the DEC
  for Phase 29 (status=Accepted at commit, parent_dec=Phase 29
  blueprint `6ecd65b`, notion_sync_status=pending session-end
  batch sync)
- Round cap 3: NOT triggered

## Phase 30 opening punchlist (consolidated from 3 audits + carry-over)

### Tier 1 (biggest single-axis lifts)
1. **First `*DYNAMIC` validated case** (1D Hopkinson wave-
   propagation rod, implicit transient) — closes FEA Dim 6
   ballistic-readiness floor (50 → 75); composite lift +4 to +6.
2. **2-quadrant viewport split** (iso + section-cut companion) —
   closes UI Dim 5 industrial-parity (82 → 88).
3. **Toast-surface the corrupted-key warn** (UX Dim 5 86 → 90).

### Tier 2 (smaller but real)
4. Measurement / coord-readout floating tooltip (UI Dim 5 secondary).
5. Convergence-study artifacts for the 9 existing cases (FEA Dim 5 80 → 90).
6. App.tsx reducer extraction (state machine for activeCaseId /
   file / report / loading).

### Tier 3 (multi-phase architectural)
7. Composite-layup S4 case (anisotropic shell, FEA Dim 1 80 → 82).
8. `*HEAT TRANSFER` validated case (thermal coupling, FEA Dim 2 78 → 85).
9. Contact case `*CONTACT PAIR` (paired-surface, FEA Dim 1 80 → 85).
10. Branching onboarding paths (in-context bubbles, UX Dim 1 90 → 99).
11. Real WebGL E2E via playwright (Phase 26-28 carry-over).
12. Iso-surface rendering (Phase 26 carry-over).

### Process improvements
13. Structural source-scan tests should take file-path as a parameter
    (Phase 28 D test relocation lesson).
14. Reconnaissance-before-commit checklist: read the relevant adapter
    BEFORE assuming a plumbing gap exists (Phase 29 A lesson).

## Honest ceiling acknowledgment

Phase 29 FINAL notes: **99/100 may have a structural ceiling at
~95 under the Tier-1-candidate honest contract**. The remaining
14.77 points break down as:
- `*DYNAMIC` ballistic case: +4 to +6
- Multi-viewport + measurement tools: +2 to +3
- Contact + composite + thermal cases: +2 to +3
- App.tsx reducer + real WebGL E2E: +1 to +2
- Polish + branching onboarding + signed-doc workflow: +2 to +3

Achievable under honest contract: ~95. The 95 → 99 gap likely
requires signed external verification or NIST benchmark agreement,
which 绝对诚实客观 explicitly forbids. **Phase 30+ should aim
honestly at 95, not 99; the final 4 points may not be ethically
attainable under the current contract.**

## Decision

Phase 29 closes at honest composite **84.23/100**,
CHANGES_REQUIRED (still below 99 target, but +4.63 over Phase 28
— the largest per-phase Δ since Phase 27). The rubric v1.0
shipped in 29 D delivered its first measurable impact (absolute
vs delta methods converged to 0.04 points vs Phase 28's 2.7-point
gap). Structural lifts (shells + reviewer-frame primitive)
unblocked two hard caps. The 99 target remains a multi-phase
commitment with an honest ceiling of ~95 under the current
contract.

Not signed validation; not benchmark agreement.
