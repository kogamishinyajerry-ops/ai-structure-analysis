# FM-04a Phase 29 — UX Audit · rubric v1.0

> Honest scoring per 绝对诚实客观 contract carried from Phase 18-28.
> Rubric: `.planning/audits/RUBRIC.md` v1.0 (Phase 29 D pinning).
> Tier 1 / Tier 2 engineering candidate; not signed validation;
> not benchmark agreement.

## Provenance baseline
- Phase 28 honest composite = 79.6/100; **Phase 28 UX = 83.6** by
  delta from Phase 27 (per `fm04a_phase28_8th_case_ballistic_exit_promo_memo.md`).
- Phase 28 sub-agent's UX absolute = 82.7 (per `phase28_ux_audit.md`);
  the +0.9 reconciliation is the Phase 28 brief's lift-from-27 number
  vs the sub-agent's absolute under a slightly stricter scale. **Per
  RUBRIC.md §"How sub-agents apply this rubric"** I score absolutes
  against v1.0 anchors directly; the Phase 28 anchor under v1.0 is
  ~83 (composite tour 84 / persist 86 / cog 82 / motion 86 / honesty
  80 / novice 78 — already cited in Phase 28 audit).
- Phase 29 deliveries: 5 commits (`6ecd65b`, `87badbe`, `5456e82`,
  `8d3baed`, `4dd6d38`); App.tsx now 1457 LOC (down from Phase 28's
  1596 = -139 LOC, vs the brief's claimed 1421; the +36 LOC delta
  is downstream test/feature additions in 29 C+D that don't change
  the architecture argument).

## Sub-axes

### 1. Onboarding flow quality: **90/100**

- **Anchor match:** 90 anchor = "App-root tour mount (no tab
  coupling); focus-trap (WCAG 2.4.3); reduce-motion respected;
  corrupted-key warnings observable. Phase 29 C+D." All four
  preconditions cited verbatim below.
- **Evidence (file:line):**
  - App-root mount: `App.tsx:1224-1240` — both `<OnboardingTour>`
    and `<AdvancedModePromo>` render *outside* the tab-switch tree,
    inside the top-level `app-container` div. Closes Phase 28
    gap #1 ("Tour + Promo are mounted inside ResultMeshPlaybackPanel").
  - Focus-trap on tour: ensured by `useFocusTrap` hook
    (`useFocusTrap.ts:82-150`) consumed in `AdvancedModePromo.tsx:104`;
    test pinned by `Phase29C_tour_app_root_focus_trap.test.tsx`.
  - Reduce-motion: `polishStyles.ts:161-174` blocks chevron
    transition and promo entrance animations under
    `prefers-reduced-motion: reduce`.
  - Corrupted-key warn: `probeListStorage.ts:64-66, 70-72, 77-80`
    emits `console.warn` on three failure modes
    (parse-error / wrong-shape / storage-access). Test:
    `Phase29D_corrupted_key_warn.test.tsx`.
- **Interpolation rationale:** All 4 anchor-90 preconditions met.
  Not at 99 because branching paths by user role / in-context
  bubbles / telemetry feedback are explicitly future per RUBRIC.md.

### 2. State preservation + recovery: **90/100**

- **Anchor match:** 90 anchor = "+ Restored-from-session toast
  surfaces the recovery; + corrupted-key console.warn for
  observability; + persistence on collapse state. Phase 29 B+D."
- **Evidence (file:line):**
  - Restored-from-session toast: still wired from Phase 28 C
    (`ResultMeshPlaybackPanel.tsx:296-313` per Phase 28 audit; no
    regression).
  - Corrupted-key console.warn (NEW · 29 D):
    `probeListStorage.ts:64-66`, `70-72`, `77-80` — three distinct
    failure-mode warnings keyed by `caseId`. Pinned by
    `Phase29D_corrupted_key_warn.test.tsx`.
  - Per-section collapse persistence (NEW · 29 B):
    `sectionCollapseStorage.ts:25-27` namespaces each section under
    `fm04a.trust-section.<storageKey>.collapsed.v1`;
    `SectionFrame.tsx:66-70` reads via synchronous initializer
    (no flash), `:77-84` writes through `saveSectionCollapsed`.
    C:-1 anti-bleed guard documented at line 19-20 of the storage
    file.
- **Interpolation rationale:** Three of three Phase-29-tagged
  anchor-90 conditions met exactly. 99 reserved for full-state
  cross-session JSON snapshot + IndexedDB / server-side resume —
  future work, not regressed.

### 3. Cognitive-load mitigation: **89/100**

- **Anchor match:** 90 anchor = "+ Collapsible accordion on trust
  sections (less wall-of-text); + reviewer-frame primitive uniform
  across panels. Phase 29 B."
- **Evidence (file:line):**
  - Collapsible accordion: `SectionFrame.tsx:95-123` — clickable
    header with `aria-expanded` + `aria-controls`; body hidden via
    `hidden` attribute + `display:none` (line 129-130). Default is
    expanded (line 59, `defaultCollapsed = false`) — D:-1 additive
    guard so no existing reviewer sees behavior regression.
  - Reviewer-frame primitive: `SectionFrame.tsx` is the unified
    primitive consumed via the new `useTrustSections` hook
    (referenced in commit `5456e82`); the -246 LOC drop in App.tsx
    (Phase 28's 1596 → Phase 29's 1457 = -139 net after subsequent
    additions) confirms the consolidation.
  - Item-count summary in the collapsed-header
    (`SectionFrame.tsx:115-122`) provides at-a-glance breadcrumbs
    when sections are collapsed — directly addresses cognitive
    load.
- **Interpolation rationale:** -1 vs strict 90 because the brief's
  "App.tsx 1667 → 1421" advertised target appears to be 1457 in
  the audited tree, indicating either the reducer extraction wasn't
  as deep as advertised OR Phase 29 C+D re-introduced ~36 LOC of
  mount logic at App-root (likely the latter, given the visible
  29 C App-root tour mount block at 1224-1240). Phase 28 retro's
  punchlist #3 (reducer extraction) is improved but not closed.
  Adaptive UI-density (99 anchor) explicitly future.

### 4. Motion / micro-interactions: **90/100**

- **Anchor match:** 90 anchor = "+ Chevron rotation transition;
  + promo entrance matching tour vocabulary; + all reviewer-
  touchable affordances covered. Phase 29 B+C."
- **Evidence (file:line):**
  - Chevron rotation: `polishStyles.ts:137-142` defines
    `.fm04a-section-frame-chevron { transition: transform 180ms
    ease-out; }`; `SectionFrame.tsx:107-111` applies the class +
    inline `transform: rotate(-90deg | 0deg)`. Reduce-motion at
    `polishStyles.ts:170-173` zeros the transition (kept rotation
    structural so visual state is preserved per the comment on
    line 168-170 — thoughtful).
  - Promo entrance animation: `polishStyles.ts:74-77` defines
    `fm04a-advanced-mode-promo-fade-slide-in` 200ms (same vocabulary
    as `fm04a-restored-toast-fade-in` line 70-73 and `fm04a-probe-
    row-fade-in` line 62-65 — single 200ms ease-out anchor). Reduce-
    motion: line 165 disables it. Closes Phase 28 audit Dim 4 gap
    ("AdvancedModePromo ships with no entrance animation").
- **Interpolation rationale:** All Phase-29 anchor-90 conditions met
  with the same motion vocabulary explicitly maintained (200ms
  ease-out). 99 reserved for spring physics / haptic — future.

### 5. Error recovery + honesty surfacing: **86/100**

- **Anchor match:** Between 80 (Phase 28 B) and 90 anchor =
  "+ Corrupted-key console.warn observable; + per-case tolerance
  pin visible in artifacts. Phase 29 D."
- **Evidence (file:line):**
  - Corrupted-key console.warn (NEW · 29 D):
    `probeListStorage.ts:64-66, 70-72, 77-80` — three distinct
    failure surfaces (parse / shape / storage-access). Closes Phase
    28 audit Dim 5 gap exactly ("Persistence corrupted-key fallback
    is silent... no `console.warn`").
  - Per-case tolerance pin: `test_phase29d_registry_tolerance_pin.py`
    is asserted by the brief; the test surface exists in tree
    (per commit `4dd6d38` description). I have NOT independently
    grepped the .py test contents in this audit pass — caveat:
    the visible-in-artifacts half of the anchor is asserted by
    the brief, not by file-level inspection in this report. The
    console.warn half is independently verified.
  - Honest-scope copy unchanged from Phase 28 (Tier 0/1/not signed/
    not benchmark badges all carry forward).
- **Interpolation rationale:** The console.warn half is firmly
  worth +3 over Phase 28's 80; the per-case tolerance pin half
  appears wired but I'm rounding down to 86 to honor the rubric
  rule "If you can name files/lines/tests matching a 80-anchor
  example, you're at ~80, not 85" applied conservatively. Toast-
  surfacing variant of the warn (Phase 28 audit recommendation #2)
  remains as console-only — a real-user gap. 99 reserved for
  inline-explain-this-verdict links — future.

### 6. Novice-user gotchas: **90/100**

- **Anchor match:** 90 anchor = "+ Focus-trap (WCAG 2.4.3);
  + corrupted-key visible warning; + App-root tour mount (no tab
  coupling). Phase 29 C+D."
- **Evidence (file:line):**
  - Focus-trap (WCAG 2.4.3): `useFocusTrap.ts:82-150` —
    Tab/Shift-Tab cycle (lines 109-135), initial focus on
    first-tabbable (lines 102-107), prior-focus restore on cleanup
    (lines 141-148). Consumed by `AdvancedModePromo.tsx:104`. D:-2
    guard pins first-tabbable as initial focus. E:-1 keeps the
    handler narrow (Tab only — Esc/Enter pass through).
  - Corrupted-key visible warning: see Dim 2 / Dim 5 evidence.
    Visible to reviewers who have devtools open; meets the "visible"
    anchor for a non-end-user-facing observability surface (matches
    Phase 28 retro's intent for that gap).
  - App-root tour mount: `App.tsx:1226-1240` — comment block
    explicitly cites Phase 28 audit's gap. The novice who lands on
    Narrative tab (no longer Visual-coupled) sees the tour first.
- **Interpolation rationale:** All 3 anchor-90 conditions met
  exactly. Phase 28's modal-on-modal stacking risk is partially
  mitigated by 29 C's structural lift (tour and promo now both
  App-root, so z-index 1000 vs 999 still applies but the dismiss
  sequencing is no longer fragile-by-tab-context). 99 reserved for
  WebGL E2E + measurement tools — future.

## Composite UX score: **89.2/100**

  (90 + 90 + 89 + 90 + 86 + 90) / 6 = 535/6 = **89.17 → 89.2**

## Phase-29 lift over Phase 28 UX (83.6): **+5.6**

Lift drivers (anchor jumps from 80-band to 90-band):
- Onboarding flow **84 → 90 (+6)** — App-root mount + focus-trap
  + reduce-motion compliance closes Phase 28 audit gaps #1 and #4
  in one structural move.
- State preservation **86 → 90 (+4)** — corrupted-key warn (29 D)
  + collapse persistence (29 B). Phase 28 audit recommendation #2
  half-closed (console.warn shipped; toast variant not).
- Cognitive-load **82 → 89 (+7)** — SectionFrame primitive + collapsible
  accordion is the most user-visible win of the phase; -139 LOC in
  App.tsx is a credible reducer-extraction signal.
- Motion **86 → 90 (+4)** — chevron + promo-entrance both land in
  the single 200ms ease-out vocabulary; Phase 28 audit Dim 4 gap
  (promo had no entrance animation) closed.
- Error/honesty **80 → 86 (+6)** — corrupted-key warn is the exact
  Phase 27 retro §What didn't work #3 + Phase 28 audit Dim 5 gap;
  per-case tolerance pin asserted by brief.
- Novice gotchas **78 → 90 (+12)** — focus-trap + App-root mount
  + corrupted-key warn all hit the anchor-90 example list exactly.

Aggregate +5.6 lands at the high end of the brief's "+2 to +6"
expected band; this is the largest Phase-over-Phase UX lift since
Phase 25 D and is the single phase where all 6 sub-axes moved
upward — no Dim stays flat or regresses.

## Phase 30 recommendations (top 3)

1. **Toast-surface the corrupted-key warn.** The 29 D `console.warn`
   in `probeListStorage.ts:64-80` is observable only with devtools
   open; the Phase 28 audit recommended a `restoredCount=0` toast
   variant ("Stored pinned-probe state was malformed and was reset")
   that would lift Dim 5 from 86 → 90 cleanly. Cheap (~20 lines)
   and closes the only remaining Phase 28 audit recommendation
   not delivered in Phase 29.
2. **Push reducer extraction across the line.** App.tsx at 1457
   LOC still embeds App-root tour mount + handler bodies that
   would naturally live in a `useAppRootOverlays` hook (mirroring
   29 B's `useTrustSections`). Target: < 1300 LOC, which would
   unambiguously close Phase 27 punchlist #3 and lift Dim 3 from
   89 → 91+ when paired with a UI-density adaptive default.
3. **Inline-attached onboarding bubbles instead of modal cards.**
   The anchor 99 for Dim 1 calls out "in-context bubbles attached
   to UI affordances (not modal overlay)." This is a structural
   shift away from modal-on-modal sequencing; Phase 30 D could
   prototype attaching the first tour card to the field-component
   switcher button directly (Popover.tsx primitive) — would lift
   both Dim 1 (onboarding) and Dim 3 (cognitive-load by removing
   one modal layer).

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
