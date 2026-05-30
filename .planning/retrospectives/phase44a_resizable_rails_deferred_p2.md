# Phase 44 A — resizable rails · deferred P2 (Codex round-cap reached)

> Tier 1 engineering candidate; not signed validation. Created at commit of the
> Phase 44 A drag-resizable shell. Documents two Codex R2 P2 findings deferred to
> the retro queue per the round-cap=3 governance (R0 + 2 fix iterations; the 3rd
> round had **no P1**, only P2 → retro, не infinite iteration).

## Codex review arc (cross-file refactor + LOC-pinned App.tsx = risk-tier)

| Round | Findings | Disposition |
|---|---|---|
| R0 | P1 drag clobbered by unrelated re-renders; P2 rails starve stage | **fixed** (useLayoutEffect re-assert; railBudget/clampLayoutToViewport) |
| R1 | P2 below-breakpoint load rewrites saved desktop widths; P3 pointer-capture fallback incomplete | **fixed** (railBudget no-clamp ≤1024; window-level drag listeners) |
| R2 | P2a chat column not in stage reserve; P2b resize persists transient clamp | **DEFERRED → this retro** (round cap reached; both P2) |

The drag-resize CORE (pointer + keyboard + ARIA + persistence + the P1/P3 fixes)
is correct and covered by 26 passing tests. The deferred items are bounded
edge-case refinements of the stage-protection clamp.

## Deferred finding 1 — chat-aware stage reserve (R2 P2a)

`useColumnLayout.ts` `MIN_STAGE_PX = 520` reserves for the whole stage, but when
Copilot/chat is open the stage internally splits `1fr 340px` (`App.tsx:1286`), so
the workbench column = stage − 340. On a ≤1280px window with **both rails widened
toward max AND chat open**, the viewport can drop to ~180px.

- **Not the default flow**: at default rails (210+300) on 1280 with chat open the
  viewport is ~414px (fine). The squeeze requires widened rails + chat + ≤1280.
- **Why deferred**: a correct fix is chat-aware — the hook must know `showChat`
  (App state) to add a 340px reserve only when chat is open. A static bump
  (e.g. 760) over-constrains the common chat-closed case. Threading chat state
  in is an API change touching the LOC-pinned `App.tsx` → its own slice.
- **Proposed fix (follow-up)**: `useColumnLayout({ stageReservePx })` param;
  App passes `showChat ? 340 : 0` added to `MIN_STAGE_PX`.

## Deferred finding 2 — non-destructive resize clamp (R2 P2b)

The window-`resize` handler clamps rail widths to the narrower viewport **and
persists** the clamped values to `fm04a.ui.columns.v1`. Moving a window from a
large external monitor to a laptop and back loses the saved desktop layout (the
transient safety clamp permanently overwrites the preference).

- **Why deferred**: a correct fix separates the persisted *saved* layout from the
  *displayed* (clamped-for-current-viewport) layout — the resize clamp must be
  transient (display only), and widening must re-derive display from the saved
  value. That is a state-model refactor of the hook (saved vs displayed), not a
  one-liner, and would need its own Codex round (exceeding the cap here).
- **Proposed fix (follow-up)**: keep `savedLayout` (persisted, only written by
  user commit) + derive `displayLayout = clampLayoutToViewport(savedLayout, vw)`;
  resize recomputes display from saved without persisting.

## Routing

Both → a follow-up slice (fold into **Phase 44 B collapse** or a dedicated
**44 A-fix**), each a fresh reviewed change. Neither blocks the 44 A core
(drag-resize is a real Dim-3 90-anchor layout system delivered + tested).
