# FM-04a Phase 39 — Dim 4 (AI workflow integration) main-session re-confirmation · PREP

> **Status: PREP, NOT FINALIZED.** This is the main-session re-confirmation of
> Dim 4 (which has no dedicated eval-fleet agent — it is main-session synthesis
> per ADR-026 + RUBRIC_v2.md). It is prepared in the registered-fleet-blocked
> session of 2026-05-24 (see STATE blocker note) so the next session can
> finalize the prospective re-baseline in ONE coherent pass once the registered
> fleet returns Dim 1 / 2 / 3 / 5.
>
> Tier 1 / Tier 2 engineering candidate; 绝对诚实客观. Composite = simple
> arithmetic mean of 6 dims, no weights/transforms. **Phase 38 record (78.33,
> Dim 4 = 76) is UNCHANGED** — any lift here is PROSPECTIVE, applied forward at
> the next composite, never backfilled.

## Re-confirmed Dim 4 = **80** (HELD value was 76 — prospective candidate)

Code @ `67c2b8e` (Phase 39 B head). Advisor code is byte-unchanged across Phase
38–39 (no advisor surface was edited), so this is a *calibration* re-confirmation
against the rubric anchors, not a response to new work — exactly the parallel
situation to Dim 5's held-72.

### 80-anchor — ALL sub-bullets met (file:line verified)

| 80-anchor sub-bullet | Met? | Evidence (file:line) |
|---|---|---|
| Advisor at **3 workflow stages**: case-open / setup(BC) / review(results) | ✅ | (1) case-open: `frontend/src/App.tsx:1341` mounts `<CaseOpenAdvisorCard>`; (2) BC-setup: `App.tsx:1342` mounts `<BCSetupAdvisorCard>` gated by `shouldShowBCSetupAdvisor`; (3) review/results: `frontend/src/components/VisualTabPanel.tsx:185` mounts `<AdvisorPanel>` (the LLM-backed critique) |
| **4-Q gate** (LLM-offline? artifacts? TrustGate? advisory-only?) visible at **each** stage | ✅ | case-open: `CaseOpenAdvisorCard.tsx:96-109` (`data-testid="case-open-advisor-four-question-gate"`, 4 `FOUR_QUESTION_GATE_KEYS`); BC-setup: `BCSetupAdvisorCard.tsx:83-96` (`bc-setup-advisor-four-question-gate`); review: `AdvisorPanel.tsx:187-210` (`advisor-gate-checklist`, per-key ✓/✗/? from `critique.fourQuestionGate`) |

The 4 gate keys are SSOT-pinned (`FOUR_QUESTION_GATE_KEYS` from `advisorCritiqueClient`):
`llm_offline_ok` / `artifacts_user_owned` / `trustgate_explains` / `advisor_only`
— consistent across all 3 surfaces (`CaseOpenAdvisorCard.tsx:48-56`,
`BCSetupAdvisorCard.tsx:47-55`, `AdvisorPanel.tsx:61-66`).

### 90-anchor — NOT met (0 of the two distinctive sub-bullets)

| 90-anchor sub-bullet | Met? | Evidence |
|---|---|---|
| Advisor at **5 stages** (+ mesh-setup advice + solve-monitor narration) | ❌ | Only 3 advisor components exist; `grep MeshAdvisor\|SolveMonitorAdvisor\|mesh-setup-advisor\|solve-monitor` across `components/` + `App.tsx` → none |
| **Calibration-marker prose** ("confidence: high/med/low") on **every** advisor output | ❌ | `grep "confidence: high/med/low"` across all 3 advisor components → none. The cards carry a `stub · offline-first` status badge (`CaseOpenAdvisorCard.tsx:80-82`, `BCSetupAdvisorCard.tsx:67-69`); the panel carries an `advisor_status` badge + `degrade_reason` banner + `claimTier/claimBoundary/claimImpact` footer (`AdvisorPanel.tsx:151-167,170-184,244-256`) — these are **status/provenance** markers, NOT the high/med/low calibration prose the 90-anchor names |

### Score rationale (no interpolation above 80)

Highest fully-met anchor = **80**. Interpolation toward 90 ≈ 0 (both distinctive
90 items absent). Therefore **Dim 4 = 80.00**, flat at the 80-anchor.

- This is **+4 over the HELD 76**. The 76 was Phase 37's deliberate 73→76
  interpolation; Phase 38 D HELD it on byte-unchanged code rather than adopt a
  proxy re-read. On strict file:line re-confirmation the 80-anchor checklist is
  fully satisfied, so the true floor is 80 and 76 was a stale conservative carry.
- **Prospective, not retroactive**: Phase 38's Dim 4 = 76 and composite 78.33
  remain on the record. The 80 applies forward at the next composite, declared
  as a v-baseline correction (parallel to v1.0→v2.0 style basis shifts), NOT a
  backfill.

### Honest counter-checks (anti-generous-drift)

- Did NOT credit the AdvisorPanel's rich provenance footer as 90-anchor
  "calibration prose" — the anchor names a specific high/med/low format the code
  does not emit. Held the line.
- Did NOT count the BC-setup surface's conditional mount (`shouldShowBCSetupAdvisor`)
  against the 3-stage bullet — when a case is open the stage is present; the gate
  just suppresses it for cases where it would be noise. The stage exists.
- The 95-anchor "failed-LLM fallback to StubAdvisor" capability does exist
  (`AdvisorPanel.tsx:56-58,170-184` offline/degrade path) but **carries no score
  here** — you cannot bank 95-anchor credit while the 90-anchor (5 stages +
  calibration prose) is unmet. Recorded only as a forward signal.

## Next-session integration

Combine this Dim 4 = 80 with the registered fleet's authoritative Dim 1 / 2 / 3 / 5
(novice-simulator + functional-tester + industrial-ui-comparator) and a Dim 6
main-session re-confirmation, then compute the prospective re-baseline composite
in one pass. Phase 38 (78.33) and Phase 37 (77.50) records stay frozen.
