# FM-04a Phase 41.4 — Codex review R0 (relocate trust center off the 3D-Scene tab)

> ADR-026 risk-tier: single-file UI placement change (not schema/solver/golden/
> cross-≥3-file). Relay: CRS effort=high. User decision (AskUserQuestion): "Move it
> off the 3D-Scene tab" so the hero stays focused.

## Scope

| File | Change |
|---|---|
| `frontend/src/App.tsx` | `OperatorStatusPanel` ("VALIDATION & TRUST CENTER") was rendered unconditionally below all tab content; now gated `{activeTab !== 'visual' && (...)}` so it lives on the Narrative/Exploration tabs only. JSX compacted (props one-line) → App.tsx 1497 < 1500. |

## Verdict

**CLEAN / APPROVE (0 findings):** "The only tracked code change is a UI placement
tweak, and the added temporary scripts are self-contained. I didn't find a discrete
regression or correctness issue that would reliably break existing behavior."

## Why this is safe

- Tier-honesty signal NOT lost on the 3D-Scene tab: the `ResultMeshPlaybackPanel`
  "not signed validation" badge + the `RightRail` `claimTier`/`allowedClaim` render on
  all tabs regardless of this gate.
- No test renders `<App/>`; the 4 tests referencing `OperatorStatusPanel`
  (Phase21D/22C/29B/39B) render the component directly or reference it statically →
  unaffected by App-level tab gating.

## Verification

- `npx tsc --noEmit` clean; App.tsx 1497 LOC (Phase29B pin < 1500 green).
- vitest **962 passed** (unchanged).
- LIVE (preview): 3D-Scene tab — trust center + Golden-Sample queue ABSENT, 3D hero +
  collapsed "Evidence & Trust" disclosure present; Narrative tab — trust center +
  Golden-Sample queue PRESENT, disclosure correctly absent. Round-trip via tab clicks.
