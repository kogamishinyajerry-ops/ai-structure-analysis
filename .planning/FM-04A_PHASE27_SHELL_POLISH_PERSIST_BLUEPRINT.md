# FM-04a Phase 27 — Shell Element + Apple Polish + Probe Persistence + LOC Honest Reduction · BLUEPRINT

> Authorized by user 2026-05-17. Targets top-tier full-flow AI FEA;
> testing sub-agents pin every load-bearing claim; 绝对诚实客观 contract
> carried verbatim from Phase 18-26.

## Phase 26 → Phase 27 lift target

| Dimension | Phase 26 R1 (honest) | Phase 27 R1 projection |
|---|---|---|
| UX | 76.8/100 | 78.5-80.0 (+2-3) |
| FEA | 75.0/100 | 78.5-80.5 (+3.5-5.5) — **shell elements lift Dim 1** |
| UI | 72.3/100 | 75.5-77.5 (+3-5) |
| **Composite** | **74.7/100** | **77.5-79.5 (+3-5)** |

The 99 target remains multi-phase. Phase 27's honest target is a
**+3-5 composite lift on the honest baseline**.

## Slice plan (5 implementation slices + audit slice)

### Slice A — 7th validated case · S4 shell element clamped plate

**Why**: FEA Dim 1 (element library breadth) has been stuck at
65/100 since Phase 18 (B31 beam introduction). Shell elements are
the single biggest unlock for Dim 1 — commercial-CAE parity (Abaqus
/ ANSYS / CalculiX) all support shells. Phase 27 A introduces the
**first shell-element validated case** to the cohort.

**Plan**:
- Geometry: 1.0m × 1.0m × 0.020m steel square plate (a/t = 50, deep
  Kirchhoff regime); generated via gmsh as **2D surface mesh** (not
  3D solid).
- Element: **S4 (linear shell, 4 nodes)** with `*SHELL SECTION` for
  thickness; CalculiX's standard shell formulation.
- Boundary: 4-edge clamped (u_x = u_y = u_z = rotation = 0).
- Load: uniform pressure (top-face equivalent nodal load).
- Analytical: **Roark Table 11.4 case 1b** —
  `w_center = α·q·a⁴/D` with α = 0.00138 for clamped square ν = 0.3
  (Timoshenko & Woinowsky-Krieger §31; distinct from the Phase 25 A
  α = 0.00406 simply-supported case).
- Tolerance: 12% (shell discretization is tighter than C3D10 solid).
- Runner: self-contained pattern (Phase 25 A + 26 A established);
  hand-rolled INP composing S4 elements + `*SHELL SECTION` +
  4-edge clamp + pressure-equivalent load.
- Validity envelope: a/t ≥ 20 (thin-shell Kirchhoff regime).
- Anti-gaming guard A:-1 — shell normal direction pinned at predicate
  level (S4 element node-ordering convention; reverse order flips
  the +z normal → catastrophic stiffness sign error).

**Validated count**: 6 → **7**.
**FEA Dim 1**: 65 → **75** (shell elements enter cohort).
**FEA Dim 4**: 72 → 74 (S4 shell-bending solver kind distinct from
prior solid `*STATIC` linear elastic).

### Slice B — Blueprint target section extraction · honest LOC reduction

**Why**: Phase 26 D's view-model extraction GREW App.tsx (1446 →
1464). Phase 27 B revisits the extraction with **measure-twice
discipline**: choose a section whose context interface is small
enough that the extraction genuinely shrinks the file.

**Plan**:
- Pick the **Blueprint target section** (lines 924-931 in App.tsx;
  8 items + 12 lines of frame = 20 lines inline).
- Context: only `blueprintSummary` (one already-typed bundle).
- Build `buildBlueprintTargetSection(ctx)` in
  `trustCenterViewModel.ts`.
- App.tsx replaces the inline section literal with a one-line
  builder call: `buildBlueprintTargetSection({icon, blueprintSummary})`.
- **Honest LOC measurement**: before vs after, named in commit
  message AND retro. If LOC grows or stays flat, that's the honest
  result — no rubric reshape.

**Target**: App.tsx 1464 → ~1450 (-14 LOC). NOT <1300 — that's a
multi-phase commitment.

### Slice C — Apple-tier polish breadth pass

**Why**: Phase 25 D shipped tour fade-slide + CSV; Phase 26
shipped baseline tag + Unicode minus but no new motion. Apple-tier
polish breadth has stalled for 2 phases.

**Plan**:
1. **Probe-list row add/remove easing**: 200ms ease-out fade-in on
   row mount; 150ms ease-in fade-out on row unmount. Driven by CSS
   transitions on a wrapper element (no library dependency).
   `prefers-reduced-motion` media-query bypass.
2. **Threshold-filter slider gradient track**: replace the default
   `<input type="range">` gray track with a custom `::-webkit-
   slider-runnable-track` + `::-moz-range-track` showing the
   legend's blue→green→orange gradient so the min/max handles
   visually sit ON the colored value spectrum.
3. **Section-cut position hover preview**: a small numeric readout
   floats above the section-cut slider as the user drags, showing
   the cut position in meters (e.g., "x = 0.25 m"). Disappears on
   release.

**Anti-gaming guard B:-1**: `prefers-reduced-motion` honored — all
3 affordances become instant in reduce mode. Pinned at component
test level (mock the media query, assert classes/styles change).

### Slice D — Probe save/restore + tour copy refresh

**Why**: Phase 25 D CSV is one-way (export only); reviewers can
copy-out but can't reload a session's probe list. Tour copy was
written for Phase 24 B and doesn't mention Phase 25 C Basic mode
or Phase 26 C Δ column.

**Plan**:
1. **Probe save**: localStorage persistence keyed by case_id; on
   `addProbeEntry` / `removeProbeEntry` / `clearAllProbes`, persist
   the new state under `fm04a.probe-list.v1.<case-id>`. Corrupted-
   key fallback to empty list (same pattern as Phase 25 C
   `fm04a.ui.mode.v1`).
2. **Probe restore**: on `ResultMeshPlaybackPanel` mount, load
   `fm04a.probe-list.v1.<case-id>` if present and seed
   `setProbeList`. Skip when the key is malformed.
3. **Tour copy refresh**: replace the Phase 24 B 4-card sequence
   with a 5-card sequence that includes a "Basic vs Advanced
   mode" card AND a "Δ column" card. Bump the dismissed-key from
   `fm04a.onboarding.v1.dismissed` to `fm04a.onboarding.v2.dismissed`
   so existing dismissals don't suppress the new tour.

**Anti-gaming guard C:-1**: probe-list persistence is scoped BY
case_id. Switching cases must load DIFFERENT lists, not bleed
state across. Pinned at predicate level (storage key includes the
case_id verbatim).

**Anti-gaming guard D:-1**: tour-version bump is ADDITIVE — Phase
27 D does NOT clear the Phase 24 B dismissed key; if a user has
already dismissed `v1` they will SEE `v2` once, then dismiss it,
then both are dismissed. (Some users might find this annoying but
hiding a refreshed tour from existing users defeats the purpose.)

### Slice E — 3 testing sub-agents + audits + FINAL + retro + STATE

**Why**: Per Phase 18-26 discipline, every phase closes with 3
honest dimension audits (UX/FEA/UI) + synthesis + retro + STATE
refresh. No round 2 unless R1 surfaces real defects (v2.3 cap).

## Test budget

| Slice | Backend tests | Frontend tests | Live ccx run |
|---|---|---|---|
| 27 A | ~15 (analytical + envelope + A:-1 guard + verdict + E2E pin) | 0 | yes (S4 shell live run) |
| 27 B | 0 | ~5 (builder contract + LOC measurement smoke) | no |
| 27 C | 0 | ~10 (3 affordances × 3 tests; reduce-motion guard) | no |
| 27 D | 0 | ~12 (save/restore + key-namespacing + tour v2 sequencing) | no |
| 27 E | 0 | 0 (audits only) | no |
| **Total** | **~15** | **~27** | **1** |

Phase 27 total target: **~42 new tests, 0 regressions, 6
sequential commits**.

## Hard constraints (绝对诚实客观 + HF discipline preserved)

- HF1.7a (signed-registry hard-stop), HF1.7b (`*-candidate` carve-
  out), HF1.8 (path-guard) — unchanged.
- tmp_path-only test snapshot writes — except the new
  shell-clamped-plate-candidate verdict YAML in
  `golden_samples/shell-clamped-plate-candidate/`.
- No push, no PR, no Linear/Notion writes unless explicitly
  authorized at session end.
- Phase 1-26 chain additive only. Any test loosening must preserve
  original guard intent (Phase 25 A → 26 A pattern).
- Apple-tier polish must honor `prefers-reduced-motion`.
- Probe-list persistence MUST be case_id-scoped (no global key).
- LOC measurements MUST be reported verbatim — if Slice B doesn't
  shrink App.tsx, that's the honest result.
- Round 2 only if R1 surfaces "real defects unit tests missed";
  otherwise R1 closes the phase.
- v2.3 round-cap = 3 applies.

## Phase 28 candidate punchlist (carry-forward from Phase 26)

These items remain open for Phase 28+:
1. Real WebGL E2E via puppeteer/playwright (7 phases open).
2. Trust-strip / sections memoization.
3. Iso-surface rendering.
4. Second modal case (different aspect ratio).
5. CalculiX static viewer σ-tensor path.
6. Contact-mechanics validated case (Hertz).
7. Transient validated case (`*DYNAMIC`).
8. Tour auto-promote sequencing.

Not signed validation; not benchmark agreement.
