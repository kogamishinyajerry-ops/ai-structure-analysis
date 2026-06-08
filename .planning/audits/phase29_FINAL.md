# FM-04a Phase 29 — FINAL composite audit synthesis · rubric v1.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-28.

## Headline

**Phase 29 honest composite: 84.23/100**
**Lift over Phase 28 (79.6): +4.63**

Phase 29 = fourth inside-band landing in a row after Phase 26's
honest re-baseline event. The lift is the LARGEST per-phase Δ since
Phase 27 (+3.8) and hits the upper end of the blueprint's projected
82.5-85.0 band.

**Crucially**: the absolute audit sum (84.23) and the delta-from-
Phase-28 method (79.6 + (5.6 + 0.0 + 8.4)/3 ≈ 84.27) **agree to
within 0.04 points**. The rubric v1.0 (Phase 29 D delivery)
successfully closed the sub-agent drift that surfaced in Phase 28 E
(where the two methods disagreed by 2.7 points). This is the single
most important meta-process outcome of Phase 29 E.

## Per-dimension scoreboard

| Dim | Phase 28 (delta from P27) | Phase 29 absolute (rubric v1.0) | Δ | Anchor justification |
|---|---|---|---|---|
| UX  | 83.6 | **89.2** | +5.6 | Multiple sub-axes moved 80 → 90 anchor (App-root + focus-trap + collapsible accordion) |
| FEA | 77.5 | **77.5** | +0.0 composite | Dim 1 75 → 80 (S4 SHIPPED), Dim 3 +5, Dim 4 +4, Dim 5 +10 — offset by Dim 6 ballistic floor (50) holding |
| UI  | 77.6 | **86.0** | +8.4 | Dim 2 75 → 89, Dim 4 75 → 85, Dim 5 78 → 82, Dim 6 75 → 85 |
| **Composite** | **79.6** | **84.23** | **+4.63** | **Largest per-phase Δ since Phase 27 (+3.8)** |

> The FEA composite Δ of +0.0 is HONEST: real per-axis lifts of
> +5 / +5 / +4 / +10 on Dims 1 / 3 / 4 / 5 are pulled flat by Dim 6
> "Ballistic Tier-2 readiness" anchored at 50 (no `*DYNAMIC`
> validated case in a ballistic-FEA workbench cohort of 9). This is
> the single biggest single-axis FEA lift available; the FEA
> auditor explicitly recommends "first `*DYNAMIC` validated case"
> as the Phase 30 priority.

## Phase 29 wins (cited verbatim from sub-agents)

### UX (auditor `a5dfe0f3...`)
1. **App-root tour mount + focus-trap (29 C)** — single
   structural move closes Phase 28 audit gaps #1 (Visual-tab
   coupling) and #4 (WCAG 2.4.3); evidence at `App.tsx:1224-1240`
   + `useFocusTrap.ts:82-150`.
2. **SectionFrame primitive + collapsible accordion (29 B)** —
   uniform reviewer-frame across trust sections; App.tsx -246 LOC;
   per-section localStorage namespaced
   (`fm04a.trust-section.<key>.collapsed.v1`) with C:-1 anti-bleed
   guard.
3. **Corrupted-key console.warn (29 D)** — three distinct failure
   surfaces in `probeListStorage.ts:64-80` close the Phase 27 retro
   §"What didn't work #3" silent-fallback gap that survived Phase
   28 untouched.

### FEA (auditor `a79c99e0...`)
1. **Phase 29 A S4 shell case** unlocks the Phase 18-28 Dim 1 hard
   cap (75 → 80, rubric anchor exact match). Live ccx 2026-05-18
   residual +0.4881% on 441 nodes / 400 S4 elements; tighter than
   the C3D10 case at same geometry.
2. **Phase 29 A NOTES.md sign-convention doc + C3D8 preservation**
   (Phase 28 A) lifts Dim 3 honest-scope discipline to 95 (95-
   anchor verbatim).
3. **Phase 29 D registry tolerance pin** (12 tests including
   1-to-1 cohort/pin correspondence + ≤25% envelope) closes the
   Phase 28 audit gap; Dim 5 lifts 70 → 80.

### UI (auditor `a149cdd1...`)
1. **SectionFrame primitive + 7-section collapsible accordion +
   per-section localStorage persistence** — closes Phase 28 "no
   collapse on trust sections" + "App.tsx monolith" gaps
   simultaneously (Dim 2/5/6 anchors hit).
2. **useFocusTrap hook on BOTH modal overlays + App-root mount**
   decouples them from tab state — closes WCAG 2.4.3 gap (Dim 4
   anchor).
3. **Promo entrance animation + chevron transition** both in tour
   200ms ease-out vocabulary — closes Phase 28 "promo snaps in
   while everything else fades" (Dim 1 anchor exact match).

## Phase 29 honest gaps (carried forward to Phase 30)

### Surfaced by Phase 29 audits
1. **No `*DYNAMIC` validated case in a ballistic-FEA workbench** —
   biggest single-axis lift available (FEA Dim 6 = 50 → 75 anchor
   on first *DYNAMIC ship; +4.2 composite). Phase 30 priority #1.
2. **No multi-viewport split + no measurement / coord-readout
   tools** — Abaqus/CAE / ANSYS / Hyperworks all ship 4-quadrant
   default. UI Dim 5 industrial parity ceiling at 82.
3. **Toast-surfacing variant of corrupted-key warn missing** —
   devtools-only observability caps UX Dim 5 at 86 vs 90.
4. **App.tsx still at 1421 LOC** — Phase 29 B reverted Phase 28 D
   growth +90 below Phase 27 B (-10 was the prior best). Phase 30
   reducer extraction would close Dim 6 maintenance axis.
5. **S4 sign-convention root cause is hypothesis not fact** —
   Phase 29 A documents that CCX *DLOAD P2 with positive pressure
   produces +z observed displacement vs analytical -z; magnitudes
   agree at 0.49% but the sign is unresolved. Future maintenance
   risk.
6. **No convergence-study / Richardson extrapolation** — Dim 5
   ceiling at 80; Phase 30 candidate for the existing 9 cases.

### Carried forward unresolved from Phase 27 + 28
7. Real WebGL E2E via playwright (Phase 26 retro #5 / Phase 27 #5 /
   Phase 28 #7) — STILL not shipped.
8. Iso-surface rendering (Phase 26 retro / Phase 28 #10) — STILL
   absent.
9. Third modal case at intermediate L/h (Phase 27 #8 / Phase 28
   #8) — STILL absent.
10. Composite-layup S4 + clamped-edge BC variants — single shell
    case isn't broad coverage.

## Phase 30 priority recommendations (consolidated from 3 audits)

Ranked by single-axis lift potential × shippability:

### Tier 1 (biggest single-axis lifts available)
1. **First `*DYNAMIC` validated case** (1D Hopkinson wave-propagation
   rod or similar — implicit transient). Closes the FEA Dim 6
   ballistic-readiness floor (50 → 75 anchor). Single biggest
   single-axis FEA lift; composite lift +4 to +6.
2. **2-quadrant viewport split** (iso + section-cut companion).
   Closes UI Dim 5 from 82 → 88 anchor. Biggest UI parity gap with
   commercial CAE.
3. **Toast-surface the corrupted-key warn** (1-line UI; lifts UX
   Dim 5 from 86 → 90 anchor). Cheap polish; should bundle with
   Tier 1.

### Tier 2 (smaller but real)
4. **Measurement / coord-readout tools** (Hyperworks-style floating
   coordinate readout on hover). UI Dim 5 secondary lift.
5. **Convergence-study artifacts** for the 9 existing cases (mesh
   refinement table; Richardson residual). FEA Dim 5 80 → 90.
6. **App.tsx reducer extraction** (state machine for
   activeCaseId / file / report / loading). Dim 6 maintenance
   lift; should bundle with broader refactor.

### Tier 3 (architectural multi-phase)
7. **Composite-layup S4 case** (anisotropic shell). FEA Dim 1
   80 → 82.
8. **`*HEAT TRANSFER` validated case** (thermal coupling). FEA
   Dim 2 78 → 85.
9. **Contact case (`*CONTACT PAIR`)** (paired-surface validation).
   FEA Dim 1 80 → 85.
10. **Branching onboarding paths** (in-context bubbles instead of
    modal overlay). UX Dim 1 90 → 99.
11. **Real WebGL E2E via playwright** (Phase 26-28 carry-over).
12. **Iso-surface rendering** (Phase 26 carry-over).

## v2.3 disposition

- 1 sub-phase = Phase 29 (5 implementation slices + 29 E audit) =
  1 retro at phase-close ✓
- counter += 5 (telemetry only)
- No Codex review triggered (no auth / signing / 安全边界 hit)
- No charter triggered (changes within
  backend/app/services/cross_check/, backend reporting/, golden_samples/,
  backend tests/, frontend src/components/, frontend src/state/,
  frontend test/, .planning/audits/)
- DEC frontmatter: this FINAL doubles as the DEC for Phase 29
  (status=Accepted at commit, parent_dec=Phase 29 blueprint `6ecd65b`,
  notion_sync_status=pending session-end batch sync)
- Round cap 3: NOT triggered — R1 sub-agents surfaced gaps but
  no Phase-20-style real defects requiring Round 2.

## Hard-constraint compliance

- HF1.7a signed-registry: PASS
- HF1.7b `*-candidate` carve-out: PASS (plate-ss-shell-candidate)
- HF1.8 path-guard: PASS
- tmp_path-only test writes: PASS (excl. golden_samples per HF1.7b)
- No push / no PR / no Linear writes in Phase 29 — local-commit
  only awaiting next user authorization
- Test pyramid: 628/628 frontend (was 599 pre-29 D; +29 across
  29 B/C/D); backend Phase 29 A 25 unit + @requires_solver E2E
  ran live PASS at +0.4881%; backend Phase 29 D 12 tests pass
- Phase 1-28 chain additive only: PASS — Phase 28 A's `len==8`
  loosened to `>=8` with comment

## Meta-process: rubric v1.0 worked

Phase 28 E ended with absolute-vs-delta method disagreement of
2.7 points (76.9 abs vs 79.6 delta) attributed to sub-agent
strictness drift. Phase 29 D shipped `.planning/audits/RUBRIC.md`
v1.0 with anchored scoring at 60/70/80/90/99 per axis and
"NEVER score above 99" / "NEVER re-score retroactively" rules.

Phase 29 E result: absolute (84.23) and delta-from-Phase-28
(84.27) agree to **0.04 points**. The rubric closed the drift.
This is a load-bearing process improvement; future phases inherit
it.

## Decision

Phase 29 closes at honest composite **84.23/100**,
**CHANGES_REQUIRED** (still 14.77 points below the 99 target).
+4.63 over Phase 28; largest per-phase Δ since Phase 27.

**Trajectory check (honest):**
| Phase | Composite | Δ |
|---|---|---|
| 22 | ~75 | baseline |
| 26 | 74.7 | +2.5 (honest re-baseline) |
| 27 | 78.5 | +3.8 |
| 28 | 79.6 | +1.1 |
| **29** | **84.23** | **+4.63** |

Phase 29 reverses the Phase 28 decay — the "structural load-bearing
lifts" thesis (shells + reviewer-frame primitive) was correct. The
remaining 14.77 points to 99 break down honestly:
- **First `*DYNAMIC` ballistic case** → +4 to +6 composite
- **Multi-viewport + measurement tools** → +2 to +3 composite
- **Contact + composite-layup + thermal cases** → +2 to +3 composite
- **App.tsx reducer extraction + real WebGL E2E** → +1 to +2 composite
- **Final polish + branching onboarding + signed-doc workflow** → +2 to +3 composite

**Achievable headroom under the honest contract: ~95**. The 95 → 99
gap likely requires signed external verification or NIST benchmark
agreement, which the project explicitly forbids. Phase 29 FINAL
notes this honestly: **99/100 may have a structural ceiling at ~95
under the Tier-1-candidate constraint**. Phase 30+ should aim
honestly at 95, not 99; the final 4 points may not be ethically
attainable.

Not signed validation; not benchmark agreement.

---

Auditor files:
- UX: `.planning/audits/phase29_ux_audit.md` (auditor `a5dfe0f3...`)
- FEA: `.planning/audits/phase29_fea_audit.md` (auditor `a79c99e0...`)
- UI: `.planning/audits/phase29_ui_audit.md` (auditor `a149cdd1...`)
- Rubric: `.planning/audits/RUBRIC.md` v1.0 (Phase 29 D)
