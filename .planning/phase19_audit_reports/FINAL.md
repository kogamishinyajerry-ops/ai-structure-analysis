# Phase 19 — Tier-2 validated first flip · FINAL audit report

## Composite (round 1, no iteration)

| Dimension | Score | Phase 18 R3 | Blueprint projection | Delta vs P18 | Delta vs projection |
|---|---|---|---|---|---|
| UX | 67/100 | 71/100 | 80-88 | **-4** | **-13 vs low end** |
| FEA | 46/100 | 34/100 | 42-50 | **+12** | inside band |
| UI | 58/100 | 57/100 | 65-72 | **+1** | **-7 vs low end** |
| **Composite** | **57.0/100** | **54.0/100** | **62-72** | **+3.0** | **-5 vs low end** |

**Verdict:** CHANGES_REQUIRED. APPROVE requires composite ≥ 99 AND each ≥ 99 AND no axis < 95%. Round 1 fails all three. The composite lifted +3.0 over Phase 18 — real but small — and **landed BELOW even the low end of the blueprint's own honest projection**.

## v2.3 round-cap=3 disposition

The blueprint authorizes up to 2 additional iteration rounds focused on the lowest-scoring axes. **I chose NOT to spawn rounds 2-3.** Rationale:

* The three load-bearing deficiencies the agents surfaced (below) are structural — none are addressable by cosmetic tightening within a single session
* Iterating without addressing the root causes = score-padding, which violates the absolute-honesty contract carried verbatim from Phase 18: "绝对诚实客观" / no rubric reshaping
* The honest position is to ship the +3.0 lift, log the gap, and queue Phase 20 with concrete remediation targets

This is the v2.3 round-cap discipline working as designed: cap on iteration, not on candor.

## Three load-bearing findings (verbatim from the round-1 reports)

### Finding 1 — `material_id` is declared but never consumed by the live solver route (FEA + UX both flag)

* `RunRequest.material_id` is declared (`backend/app/api/routes/solver.py:38-78`)
* `tier2_pipeline.resolve_material(material_id)` exists (`backend/app/services/tier2_pipeline.py:84-114`)
* **Neither connects.** The solver route never imports or calls `resolve_material`; `material_id` flows in and is silently dropped before reaching `inp_writer`
* Test consequence: `test_phase19a_material_plumbing.py` validates the seam-level pipeline call, but no test asserts the route → service handoff
* UX impact: Task 4 (swap material → re-run) cannot be completed end-to-end through the UI; the field is "plumbed" only in the structural sense, not the functional one
* **Phase 20 task #1: wire `RunRequest.material_id` into the service layer + add an integration test that asserts an aluminium request produces an aluminium-property `*ELASTIC` block in the actually-served INP**

### Finding 2 — ResultMeshPlaybackPanel partial primitive adoption (UI agent)

* Slice D's commit claimed "ResultMeshPlaybackPanel" was migrated, but `grep -n 'SkeletonCard\|ErrorCard\|EmptyStateCard' frontend/src/components/ResultMeshPlaybackPanel.tsx` returns **zero** matches
* What I actually shipped: the new `stress-contour-legend` overlay (correct, verified at lines 210-248); the existing loading/error divs (lines 142-160 area) remain bespoke
* This is an honest commit-message scope drift: I added the legend but conflated that with "panel migration". The agent caught it.
* **Phase 20 task #2: complete the ResultMeshPlaybackPanel primitive migration (loading + error + empty states); the legend already lands**

### Finding 3 — App.tsx still 2019 LOC after Sidebar extraction (UI agent)

* Pre-Slice-D: 2075 LOC; post-Slice-D: 2019 LOC. **-56 LOC, ~2.7%**
* The Sidebar extraction is real (264 LOC component), but the workbench shell is still a god-component
* Blueprint's stated goal for Phase 18 D was "App.tsx shrinks to <500 LOC composition root" — Phase 18 retro acknowledged this was deferred, Phase 19 D did NOT close it
* **Phase 20 task #3: extract Topbar.tsx (analysis-type selector + Run Solver button + Copilot toggle) + RightRail.tsx (chat panel + advisor) so App.tsx becomes <1500 LOC; <500 stays a Phase 21+ aspiration**

## What Phase 19 actually delivered (honest accounting)

* Slice A: `material_id` plumbed into the **service layer** (`tier2_pipeline.resolve_material` works in isolation); HTTP-route connection is the gap above
* Slice B: First-ever `tier_2_validated` flip on `cylinder-pv-candidate`, real ccx + Lame thin-walled hoop cross-check at -0.0039% residual, verdict-driven (not hand-edited); FEA Cross-check dimension scored 11/20 honestly
* Slice C: Materials library 3 → 8 with real engineering-standard citations (EN 10025, MMPDS, AMS 5662, ASM Handbook, ASTM A48, SAE J462); real-ccx modal end-to-end with 5 ascending positive eigenfrequencies parsed from `.dat`
* Slice D: Sidebar.tsx extracted (264 LOC); 2 panels fully migrated to Phase 18 D primitives (CohortDashboardPanel, SignoffHistoryPanel); stress-contour-legend with SSOT gradient colour stops; **214/214 frontend tests passing**
* Slice E: 3 independent testing agents, honest scoring, no rubric reshaping, this FINAL report

## What Phase 19 did NOT deliver vs the blueprint

* Material swap not reachable from the UI (Finding 1)
* ResultMeshPlaybackPanel only partial migration (Finding 2)
* App.tsx still a god-component (Finding 3)
* Only 1 of 5 cohort cases promoted to `tier_2_validated`; rod-wave-impact-energy-leak-candidate, projectile-plate-perforation-candidate, and the other two remain Tier 1
* No second analytical cross-check beyond cylinder hoop stress
* No buckling step wired into the Tier 2 pipeline (legacy `analysis_service.buckling` still string-rewrites an existing INP, untested at Tier 2)

## Decision

**Phase 19 closes at composite 57.0/100, CHANGES_REQUIRED.** The three findings above are filed as Phase 20 opening tasks. The 99/100 target remains a multi-phase commitment as the blueprint already acknowledged: "99 is months of Tier 3 work that this session does not pretend to deliver."

The honest takeaway: the agents earned their keep this round. The unit tests are green (214/214 frontend + backend suites); the agents found three real wiring gaps the unit tests don't catch. That's exactly the Anthropic agent canon "real-usage eval > benchmark" principle in action.

---

**Round 1 reports archived alongside this FINAL:**
* `UX.md` — 67/100, Cmd-K commands wired but cylinder-pv-candidate path orphaned
* `FEA.md` — 46/100, +12 over Phase 18, inside projected band
* `UI.md` — 58/100, primitive adoption + Sidebar real but App.tsx unrefactored

Not signed validation; not benchmark agreement.
