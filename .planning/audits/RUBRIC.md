# FM-04a · Audit Scoring Rubric · v1.0 (Phase 29 D)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-28.

## Purpose

Phase 28 E surfaced rubric-strictness drift between sub-agent
instances (FEA sub-agent absolute -6 vs Phase 27 actual despite
net-positive delivery). The honest interpretation was to trust the
relative Δ over the absolute number, but the BETTER fix is to pin
the per-dimension scoring rubric so each new sub-agent works from
the same scale.

**This document is the canonical rubric.** Phase 29 E onward, every
sub-agent prompt cites RUBRIC.md as MUST-READ before scoring. Each
dimension has anchor scores at 60 / 70 / 80 / 90 / 99 with concrete
evidence-bearing examples.

## Versioning

- **v1.0 (Phase 29 D)** — initial pinning.
- Future bumps require explicit retro acknowledgment + a `vN.M`
  bump here; sub-agents read the latest version. Old phase audits
  are NOT re-scored retroactively (additive D:-1 guard).

---

## UX dimensions (6 sub-axes; composite = mean)

### Dim 1 — Onboarding flow quality
What a brand-new reviewer experiences in the first 5 minutes.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Tour exists but covers only a fraction of the surfaces; no auto-promote sequencing; tour copy is stale vs current features. | Phase 25 (no tour) |
| 70 | Tour covers most affordances; surfaces all advanced features once dismissed. | Phase 26 (tour v1, 4 cards) |
| 80 | Tour v2 with 6 cards covering all advanced features + auto-promote prompt sequencing to Advanced mode. | Phase 27 D + Phase 28 D |
| 90 | App-root tour mount (no tab coupling); focus-trap (WCAG 2.4.3); reduce-motion respected; corrupted-key warnings observable. | Phase 29 C+D |
| 99 | Branching onboarding paths by user role; in-context bubbles attached to UI affordances (not modal overlay); telemetry feedback loop. | Future (3+ phases) |

### Dim 2 — State preservation + recovery
How well the workbench survives reloads, case switches, browser quirks.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | State volatile across reloads; no per-case scoping. | Phase 25 |
| 70 | Some persistence (uiMode); no cross-case scoping. | Phase 26 |
| 80 | Per-case persistence (probe list scoped by case_id); corrupted-key fallback to initial state. | Phase 27 D |
| 90 | + Restored-from-session toast surfaces the recovery; + corrupted-key console.warn for observability; + persistence on collapse state. | Phase 29 B+D |
| 99 | + Cross-session full-state snapshot/restore via JSON download; + checkpoint/resume across browsers (IndexedDB or server-side). | Future |

### Dim 3 — Cognitive-load mitigation
Whether the UI lets novice users focus on the task vs being overwhelmed.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | All controls flat; no Basic/Advanced separation; tour did not exist. | Phase 22 |
| 70 | Basic/Advanced toggle exists but defaults to Advanced; tour does not explain it. | Phase 25 C |
| 80 | Default Basic; tour explains Basic vs Advanced; auto-promote sequencing nudges to Advanced. | Phase 28 D |
| 90 | + Collapsible accordion on trust sections (less wall-of-text); + reviewer-frame primitive uniform across panels. | Phase 29 B |
| 99 | + Adaptive UI density based on user role / proficiency telemetry. | Future |

### Dim 4 — Motion / micro-interactions
Whether transitions feel cohesive, intentional, and accessible.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | No animations; instant on/off transitions. | Phase 23 |
| 70 | A few keyframes (tour fade-slide); no reduce-motion respect; inconsistent timing. | Phase 25 D |
| 80 | Single motion vocabulary (200ms ease-out anchor; asymmetric faster-exit); reduce-motion @media disables all of it; entrance + exit animations matched. | Phase 28 C |
| 90 | + Chevron rotation transition; + promo entrance matching tour vocabulary; + all reviewer-touchable affordances covered. | Phase 29 B+C |
| 99 | + Springy / momentum-based gestures for touch users; + haptic feedback hooks. | Future |

### Dim 5 — Error recovery + honesty surfacing
Whether the UI surfaces its honest scope (Tier 1 candidate, not signed validation).

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | "not signed validation" badge buried or absent; failure modes silent. | Phase 21 |
| 70 | Visible "not signed validation" badge; some Tier-2-blocker surfacing. | Phase 26 |
| 80 | Trust strip surfaces claim_tier + claim_boundary on every view; Ballistic Tier-2 blockers row always danger-toned. | Phase 28 B |
| 90 | + Corrupted-key console.warn observable; + per-case tolerance pin visible in artifacts. | Phase 29 D |
| 99 | + Inline "explain this verdict" link on every claim; + dynamic claim_boundary derivation from active evidence set. | Future |

### Dim 6 — Novice-user gotchas
What a brand-new reviewer can trip over without warning.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Major silent failures (case switch loses unsaved state; field-component mismatch undetected). | Phase 22 |
| 70 | Most state-preservation guarantees in place; some silent fallbacks remain. | Phase 27 D |
| 80 | Silent restoration visible (toast); tour explains all affordances; default-Basic prevents overwhelming first-impression. | Phase 28 C |
| 90 | + Focus-trap (WCAG 2.4.3); + corrupted-key visible warning; + App-root tour mount (no tab coupling). | Phase 29 C+D |
| 99 | + Real WebGL E2E coverage; + measurement/coord tooltips; + multi-viewport split for context. | Future |

---

## FEA dimensions (6 sub-axes; composite = mean)

### Dim 1 — Element-type breadth
What element classes are validated in the cohort.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Only solid tets (C3D10). | Phase 19 |
| 65 | + Solid hex (C3D8). | Phase 20 |
| 70 | + Quadratic tets + beams (B31). | Phase 23 |
| 75 | All solid + beam classes covered; SHELLS still missing. | Phase 28 |
| **80** | **+ Shell elements (S4) validated; first non-solid non-beam element class.** | **Phase 29 A** |
| 85 | + Higher-order shell (S8) + axisymmetric elements. | Future |
| 90 | + Contact pairs + composite-layup shells. | Future (M3) |
| 99 | All major Abaqus element classes (solid / shell / beam / continuum-shell / membrane / contact / gap / cohesive / rigid). | Future (M5) |

### Dim 2 — Solver-kind coverage
What CalculiX `*STEP` kinds the cohort exercises.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Only `*STATIC`. | Phase 19 |
| 70 | + `*BUCKLE` (linear buckling). | Phase 22 |
| 78 | + `*FREQUENCY` (modal eigenvalue). | Phase 26 |
| 85 | + `*DYNAMIC` (transient, implicit). | Future |
| 92 | + `*DYNAMIC, EXPLICIT` (ballistic-scale transient — FIRST ballistic in the ballistic-workbench cohort!). | Future (M4) |
| 99 | + `*HEAT TRANSFER` + `*VISCO` + `*COUPLED TEMPERATURE-DISPLACEMENT`. | Future (M5) |

### Dim 3 — Honest-scope discipline
Whether failed attempts are preserved in-tree with documented rejection vs hidden.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Failed attempts deleted; no record of what was tried. | hypothetical |
| 70 | Retro mentions failures; code is clean of the failed attempt. | Phase 22 |
| 85 | Failed attempt preserved in-tree as documented honest-scope (e.g., NotImplementedError dispatch); regression test pins the rejection. | Phase 28 A C3D8 cantilever |
| 95 | + Honest-scope NOTES.md documents root cause + the lesson learned. | Phase 29 A S4 sign convention |
| 99 | + Failed-attempt corpus indexed (cross-case "what doesn't work" catalog). | Future |

### Dim 4 — Validated-cohort size
How many cases have a live PASS verdict.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | 1-2 cases. | Phase 19 |
| 70 | 3-5 cases. | Phase 22-25 |
| 78 | 6-8 cases. | Phase 26-28 |
| **82** | **9 cases including the first non-solid element type.** | **Phase 29 A** |
| 88 | 12+ cases covering 3+ element classes + 3+ solver kinds. | Future (M3) |
| 99 | 25+ cases spanning all major Abaqus element + solver + BC combinations. | Future (M5) |

### Dim 5 — Residual budget + tolerance discipline
Tightness of the canonical residuals + whether tolerances are pinned per-case.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Residuals 10-20%; no per-case tolerance pin (registry pins verdict only). | Phase 27 |
| 70 | Residuals 5-15%; tolerance is verdict-YAML field but no regression pin. | Phase 28 |
| **80** | **Per-case tolerance pin in registry test (loosening = test trip); residuals ≤ 5% for most cases.** | **Phase 29 D** |
| 90 | + Convergence-study (mesh refinement) documented for each case; + Richardson extrapolation residual. | Future |
| 99 | + Independent third-party verification per case; + uncertainty quantification. | Future |

### Dim 6 — Ballistic Tier-2 readiness
Whether the ballistic candidate section has honest blockers + a path to validation.

| Anchor | What you observe | Examples |
|---|---|---|
| 42 | No ballistic case in cohort; Ballistic section surfaces honest blockers only. | Phase 28 |
| 50 | + Ballistic candidate UI shows tier-2 blocker count + animation manifest pin. | Phase 28 B |
| 75 | + First `*DYNAMIC` validated case (transient, implicit). | Future |
| 90 | + First `*DYNAMIC, EXPLICIT` validated ballistic case. | Future (M4) |
| 99 | + Independent Børvik 2002 benchmark agreement (NOT under current honest contract). | Future (M5+) |

---

## UI dimensions (6 sub-axes; composite = mean)

### Dim 1 — Micro-interaction polish + animation quality
Fluidity, timing, easings.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | No animations; rough state changes. | Phase 23 |
| 70 | Some animations; inconsistent timing; reduce-motion not respected. | Phase 25 |
| 80 | Single motion vocabulary (200ms ease-out anchor); reduce-motion universally honored; entrance + exit matched. | Phase 28 C |
| 90 | + Chevron + accordion + promo entrance all in the same vocabulary. | Phase 29 B+C |
| 99 | + Spring physics / momentum on touch gestures; + haptic feedback hooks; + cohesive across all 7 trust panels. | Future |

### Dim 2 — Visual hierarchy + typography
Heading sizes, label-vs-value disambiguation, claim badges.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Flat font sizing; labels and values look the same; no visual prioritization. | Phase 21 |
| 70 | Some hierarchy; tone-colored values; trust strip + sections visually distinct. | Phase 26 |
| 80 | Full 4-tone palette (accent/warning/danger/muted) consistent across all 7 sections; gradient slider matches legend; claim badges visible. | Phase 28 C |
| 90 | + Uniform SectionFrame primitive; + collapse summary in header. | Phase 29 B |
| 99 | + Custom typography pairs (sans + mono) for data vs prose; + responsive density breakpoints. | Future |

### Dim 3 — Color system + tonal discipline
Whether the tone vocabulary is consistent + matches conventions.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Ad-hoc color usage; no token system. | Phase 21 |
| 75 | `accent/warning/danger/muted` tokens but inconsistently applied. | Phase 25 |
| 85 | All 7 trust sections + golden samples + claim badges thread the 4-tone system; gradient slider matches viewport legend. | Phase 28 |
| 90 | + No regression in Phase 29 ship. | Phase 29 (held) |
| 99 | + Dark/light theme toggle with token re-mapping. | Future |

### Dim 4 — Accessibility (a11y)
WCAG 2.x coverage on dialog, role, aria, focus.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | role/aria largely absent; no focus management. | Phase 22 |
| 75 | role="dialog" + aria-label on overlays; role="status" + aria-live on toasts. | Phase 28 C |
| 85 | + Focus-trap on all modal overlays (WCAG 2.4.3). | Phase 29 C |
| 92 | + Keyboard-only navigation tested + documented; + screen-reader fixtures. | Future |
| 99 | + Full WCAG 2.2 AA conformance certified. | Future |

### Dim 5 — Industrial-software parity
Does the UI stand next to Abaqus/CAE, ANSYS Mechanical, Hyperworks?

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Looks like a Bootstrap admin template. | Phase 19 |
| 70 | Top-bar / sidebar / glass-panel modern; viewport area dominant. | Phase 25 |
| 78 | + 3D viewport with webGL + threshold filter + section cut + probe HUD. | Phase 27 |
| 82 | + Collapsible accordion on trust sections; uniform SectionFrame primitive. | Phase 29 B |
| 88 | + Multi-viewport split (4-quadrant default); + measurement/coord tools; + collapsible left/right rails. | Future (M5) |
| 99 | + Direct CAD picking on imported geometry; + ribbon menus; + customizable panel layouts. | Future (M6) |

### Dim 6 — Density + reviewer ergonomics
Whether the UI breathes vs crams.

| Anchor | What you observe | Examples |
|---|---|---|
| 60 | Cramped table cells; no whitespace discipline. | Phase 22 |
| 75 | Probe list + trust sections breathe; gradient sliders precision-friendly. | Phase 27 C |
| 85 | + Per-section collapse lets reviewer focus on one panel at a time. | Phase 29 B |
| 92 | + Drag-to-resize panels; + density toggle (compact / comfortable). | Future |
| 99 | + Full customizable workspace layout (Abaqus-style). | Future |

---

## How sub-agents apply this rubric

1. **Read this file first.** Cite version (v1.0) in the audit output header.
2. For each axis, find the anchor closest to current state. Use the
   **examples column** as concrete evidence anchors — if you can name
   files/lines/tests matching a 80-anchor example, you're at ~80, not
   85.
3. Score INTERPOLATING between anchors (e.g., "between 80 and 90 →
   ~83") when the evidence partially matches a higher anchor.
4. **NEVER score above 99.** 99 is "exceptional under the honest
   Tier-1-candidate contract"; 100 would require crossing into signed
   validation territory which the project explicitly forbids.
5. **NEVER score below 60.** 60 is "the baseline functionality
   exists in some form"; below that would imply the project is
   actively broken, which is a build/test issue not a quality issue.
6. **Composite = simple arithmetic mean** of the 6 sub-axes. Do not
   weight or apply transforms.
7. **Cite EVIDENCE for every score.** Format: `<axis>: <score>/100
   — <one-sentence justification with file:line or test name>`.

## What sub-agents must NOT do

- Re-score Phase 28 retroactively using this rubric (additive D:-1).
- Apply weights/transforms to the composite (must be simple mean).
- Score above 99 or below 60.
- Hide honest gaps in averaged scores. If FEA Dim 1 is hard-capped
  by missing shells, say so explicitly even when it pulls FEA
  composite down.
- Drift the rubric mid-phase. If you find an axis genuinely lacks
  a useful anchor at your score, **flag it for a v1.1 bump** in the
  retro; do not silently invent a new anchor.

---

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement. 绝对诚实客观 across 12 consecutive Tier-2 phases.
