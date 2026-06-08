// FM-04a Phase 2 C — Workbench candidate-case picker registry.
//
// Tier 1 engineering candidate; not signed validation; not benchmark agreement.
//
// Typed contract for the `/api/v1/candidate-cases` endpoint plus a
// static fallback list that matches the on-disk
// `golden_samples/*-candidate/` directories. The static list is used
// when the backend is unreachable so the Workbench still surfaces the
// picker as a Tier 1 boundary-preserving stub.

export type CandidateCaseId =
  | 'GS-102-candidate'
  | 'GS-102-refined-candidate'
  | 'GS-102-hifi-candidate'
  | string

export interface CandidateCaseRecord {
  caseId: CandidateCaseId
  claimTier: string
  starterDeckRelpath: string | null
  engineDeckRelpath: string | null
  generatorScriptRelpath: string | null
  notesExcerpt: string | null
  claimBoundary: string
  // FM-04a Phase 18 E (round 3) — optional human display label for
  // the picker dropdown + Cmd-K palette. When absent the picker
  // falls back to ``caseId``. Adopted incrementally so this stays
  // back-compat with payloads from the live route (which doesn't
  // emit this field yet).
  displayLabel?: string
  // FM-04a Phase 36 C — closes Phase 35 R3 friction point (f).
  // `true`  → the case has a live ccx runner + verdict YAML
  //           (cohort-12 cases as of Phase 34 C)
  // `false` → demo deck only (GS-* OpenRadioss decks + rod-wave
  //           cases without a cross-check runner yet)
  // undefined / absent → unknown / live-route payload not yet
  //           emitting this field; UI should not surface a badge.
  runnerAvailable?: boolean
  // FM-04a Phase 37 A — solver kind for CaseBrowser tree grouping.
  // Mirrors the backend verdict YAML `solver_kind:` enum
  // (Phase 35 B 6 values: linear_static / modal / buckling /
  // dynamic / heat_transfer_steady_state / contact_pair_static).
  // Optional so the live-route payload stays back-compat.
  solverKind?:
    | 'linear_static'
    | 'modal'
    | 'buckling'
    | 'dynamic'
    | 'heat_transfer_steady_state'
    | 'contact_pair_static'
  // FM-04a Phase 38 D — whether this case has boundary conditions assigned
  // yet. Absent / false → not assigned (every cohort case as of Phase 38 D;
  // BC authoring is future scope) → BCSetupAdvisorCard shows + BCSetupPillList
  // labels pills "Expected". true → advisor hides + pills "Assigned".
  // Optional so the live-route payload stays back-compat.
  bcAssigned?: boolean
}

export interface CandidateCaseRegistryPayload {
  claimTier: string
  claimBoundary: string
  claimImpact: string
  count: number
  cases: CandidateCaseRecord[]
}

// Static fallback list — read at build time so the Workbench can
// render the picker even when /api/v1/candidate-cases is unreachable.
// Mirrors the on-disk directory contents committed in
// `golden_samples/*-candidate/` and the matching `scripts/gen_*` files.
// Phase 18 E (round 3) — gained human displayLabel + leak case entry.
export const FALLBACK_CANDIDATE_CASES: CandidateCaseRecord[] = [
  {
    caseId: 'GS-102-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 · Single-hex demo (Tier 1)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: 'golden_samples/GS-102-candidate/data/model_00_0000.rad',
    engineDeckRelpath: 'golden_samples/GS-102-candidate/data/model_00_0001.rad',
    generatorScriptRelpath: null,
    notesExcerpt:
      'GS-102-candidate · 1-hex starter+engine demo deck for FM-04a P3 ' +
      'registration. Tier 1 engineering candidate; not signed validation; ' +
      'not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'GS-102-refined-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 refined · 4×3×3 plate + 2×2×2 projectile (Tier 1)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath:
      'golden_samples/GS-102-refined-candidate/data/model_00_0000.rad',
    engineDeckRelpath:
      'golden_samples/GS-102-refined-candidate/data/model_00_0001.rad',
    generatorScriptRelpath: 'scripts/gen_gs102_refined_deck.py',
    notesExcerpt:
      'GS-102-refined-candidate · 4x3x3 plate hex + 2x2x2 projectile hex ' +
      'refinement of GS-102-candidate. Tier 1 only; not signed validation; ' +
      'not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'GS-102-hifi-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'GS-102 hi-fi · 7.62×51 AP vs Weldox 460E @ V0=600 m/s (Tier 1)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0000.rad',
    engineDeckRelpath: 'golden_samples/GS-102-hifi-candidate/data/model_00_0001.rad',
    generatorScriptRelpath: 'scripts/gen_gs102_hifi_deck.py',
    notesExcerpt:
      'GS-102-hifi-candidate · 7.62x51 AP-class projectile vs 100x100x8 mm ' +
      'Weldox 460E plate at V0 = 600 m/s. Tier 1 only; not signed validation; ' +
      'not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    // Phase 18 E (round 3) — leak case promoted into the fallback so
    // novice reviewers can find it without the live backend route.
    // UX agent round-2 finding: case was invisible in the fallback
    // path until now.
    caseId: 'rod-wave-impact-energy-leak-candidate',
    runnerAvailable: false,
    solverKind: 'dynamic',
    displayLabel: 'Rod-wave impact · ENERGY LEAK case (Tier 1)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt:
      'rod-wave-impact-energy-leak-candidate · the canonical "what does ' +
      'a broken case look like?" fixture. Hidden energy leak appears in ' +
      'the .frd; the cohort drift surface flags it. Tier 1 only; not ' +
      'signed validation; not benchmark agreement.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    // Phase 19 B / Phase 20 — first tier_2_validated case (per the
    // verdict-file-driven overlay in
    // `backend/app/services/reporting/_claim_tier.py`). Surfaced in
    // the fallback so the Phase 20 D Sidebar candidate roster shows
    // it even when the live backend route is unreachable. Phase 20 E
    // round-1 UX finding: omission of these three new candidates was
    // a real defect; this commit closes it.
    caseId: 'cylinder-pv-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Cylinder pressure vessel · Tier 2 validated',
    claimTier: 'Tier 2 validated (analytical hoop-stress cross-check)',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: 'scripts/cross_check_cylinder_pv.py',
    notesExcerpt:
      'cylinder-pv-candidate · first tier_2_validated case in the harness. ' +
      'Lame thin-walled hoop stress σ=p·r/t cross-checked vs real ccx ' +
      'wall coupon at -0.0039% residual (PASS). Verdict file at ' +
      'golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml.',
    claimBoundary:
      'tier2_real_solver_validated; not_signed_validation; ' +
      'cross_check_against_analytical',
  },
  {
    caseId: 'plate-with-hole-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Plate with hole · 100×50×5 mm, meshed pipeline',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath:
      'golden_samples/plate-with-hole-candidate/data/plate_with_hole.geo',
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt:
      'plate-with-hole-candidate · Phase 20 C demonstration of the ' +
      'meshed Tier 2 pipeline. Real gmsh → C3D4 tet mesh → real ccx → ' +
      'non-zero u_x field under tensile load. Kirsch σ_max = 3·σ_∞ ' +
      'cross-check runner is Phase 21+ scope.',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  {
    caseId: 'cantilever-beam-candidate',
    runnerAvailable: true,
    solverKind: 'linear_static',
    displayLabel: 'Cantilever beam · Euler-Bernoulli δ=PL³/(3EI)',
    claimTier: 'Tier 1 engineering candidate',
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt:
      'cantilever-beam-candidate · second analytical cross-check ' +
      'companion. Phase 20 B shipped the analytical formula + validity ' +
      'envelope; ccx-running runner is Phase 21+ scope (single-hex ' +
      'coupons cannot capture bending; multi-element Gmsh path lands ' +
      'this case at tier_2_validated).',
    claimBoundary:
      'tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement',
  },
  // FM-04a Phase 38 H — the 17 entries below close eval finding #3 (only
  // 7/24 on-disk *-candidate cohort dirs were reachable when the backend is
  // unreachable). Generated from golden_samples/ disk truth by
  // scripts/gen_fallback_candidate_registry.py (provenance / regeneration):
  // claimTier + claimBoundary come from the _claim_tier SSOT (a PASS
  // cross_check_verdict.yaml on a REGISTERED case promotes to Tier 2 — e.g.
  // nafems-le10 is now Tier 2 (V2-1/ADR-027: registered + PASS
  // cross_check_verdict.yaml, real ccx LE10 benchmark agreement)); solverKind + runnerAvailable from the verdict YAML;
  // notesExcerpt is the same 12-line / 1200-char rule the backend route emits
  // (online<->offline parity). Double-quoted to preserve embedded apostrophes
  // (Hooke's / Euler's / Young's). displayLabel intentionally omitted (the
  // picker falls back to caseId) rather than fabricating a label. Drift guard:
  // frontend/test/Phase38H_fallback_cohort_coverage.test.tsx fails if a new
  // *-candidate dir lands without a fallback entry — re-run the script then.
  {
    caseId: "cantilever-beam-modal-candidate",
    runnerAvailable: true,
    solverKind: "modal",
    displayLabel: "Cantilever Beam Modal · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# cantilever-beam-modal-candidate · NOTES\n\n> **Phase 26 A** — 6th tier_2_validated case. Closes Phase 25 retro\n> punchlist item #3 (FEA Dim 4 solver-kind coverage held flat at 68\n> since Phase 23 A). Introduces the `*FREQUENCY` modal-eigenvalue\n> solver kind to the validated cohort.\n\n## Geometry\n\n- `data/cantilever_modal.geo` — 0.500 m × 0.020 m × 0.020 m steel beam.\n- L / max(h, w) = 25 (well inside Euler-Bernoulli slender-beam\n  envelope ≥ 10).",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "cantilever-beam-modal-l50-candidate",
    runnerAvailable: true,
    solverKind: "modal",
    displayLabel: "Cantilever Beam Modal L50 · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# cantilever-beam-modal-l50-candidate · NOTES\n\n> **Phase 27 A** — 7th tier_2_validated case. Second modal case at\n> the slenderness extreme (L/h = 50, 4× more slender than Phase 26 A's\n> L/h = 25). Validates the Euler-Bernoulli envelope across 4× the\n> slenderness range.\n\n## Geometry\n\n- `data/cantilever_modal_l50.geo` — 1.000 m × 0.020 m × 0.020 m steel beam.\n- L / max(h, w) = 50 (well inside Euler-Bernoulli slender-beam\n  envelope ≥ 10; 5× the validity threshold).",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "cantilever-buckle-candidate",
    runnerAvailable: true,
    solverKind: "buckling",
    displayLabel: "Cantilever Buckle · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# cantilever-buckle-candidate · NOTES\n\n> **Phase 28 A** — 8th tier_2_validated case. Second buckling case\n> at the **fixed-free (cantilever) end condition** (k = 2.0), distinct\n> from Phase 22 A's pinned-pinned (k = 1.0). Validates Euler's\n> effective-length-factor discipline across the k-factor family.\n\n## Geometry\n\n- 1.000 m × 0.020 m × 0.020 m steel column, single-axis buckling.\n- L / r = L / (h/√12) = 1.0 / 0.005774 = 173 (deep slender regime).\n- Boundary: x=0 face fully clamped; x=L tip COMPLETELY FREE (no",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "cantilever-dynamic-candidate",
    runnerAvailable: true,
    solverKind: "dynamic",
    displayLabel: "Cantilever Dynamic · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# cantilever-dynamic-candidate — FM-04a Phase 30 A\n\n> Tier 1 / Tier 2 engineering candidate; not signed validation; not\n> benchmark agreement.\n\n## What this case validates\n\n**The first `*DYNAMIC` (transient implicit time integration)\nvalidated case in the cohort.** Closes the FEA Dim 6 ballistic-\nreadiness floor that has been anchored at 50/100 for 11 phases\n(Phase 18-29). Prior 9 cases used `*STATIC` / `*BUCKLE` /\n`*FREQUENCY` only.",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "cylinder-pv-collapsed-candidate",
    runnerAvailable: false,
    displayLabel: "Cylinder PV Collapsed · Tier 1 candidate",
    claimTier: "Tier 1 engineering candidate",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: null,
    claimBoundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  },
  {
    caseId: "cylinder-pv-extended-candidate",
    runnerAvailable: false,
    displayLabel: "Cylinder PV Extended · Tier 1 candidate",
    claimTier: "Tier 1 engineering candidate",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: "scripts/gen_cylinder_pv_extended_deck.py",
    notesExcerpt: null,
    claimBoundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  },
  {
    caseId: "euler-column-candidate",
    runnerAvailable: true,
    solverKind: "buckling",
    displayLabel: "Euler Column · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# euler-column-candidate — Phase 22 A (infrastructure) + Phase 23 A (promotion)\n\n**Tier:** `tier_2_validated` (promoted Phase 23 A · 2026-05-17). Verdict\nfile `cross_check_verdict.yaml` carries a PASS verdict from\n`run_buckling_b31_cross_check` (B31 Timoshenko beam-element runner).\n\n**Promotion path:**\n* Phase 22 A: built `run_buckling_cross_check` (C3D8 solid-element)\n  + analytical helper. Solid-element verdict landed ~10× off Euler\n  analytical (37,360 N vs 1,727 N) — honest scope reduction recorded\n  FAIL verdict, case stayed tier_1_candidate.\n* Phase 23 A: shipped `run_buckling_b31_cross_check` using ccx B31",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "heat-transfer-1d-candidate",
    runnerAvailable: true,
    solverKind: "heat_transfer_steady_state",
    displayLabel: "Heat Transfer 1D · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# heat-transfer-1d-candidate — FM-04a Phase 31 A\n\n> Tier 1 / Tier 2 engineering candidate; not signed validation; not\n> benchmark agreement.\n\n## Documented pivot from Phase 31 blueprint Slice A\n\nThe Phase 31 blueprint (`acce14c`) scoped this slice as a `*CONTACT\nPAIR` Hertz contact case. During reconnaissance the contact setup\nproved structurally complex:\n\n* CCX `*SURFACE, TYPE=...` does not support analytical sphere /",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "hertz-contact-candidate",
    runnerAvailable: true,
    solverKind: "contact_pair_static",
    displayLabel: "Hertz Contact · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# `hertz-contact-candidate` · scope notes (Phase 33 D infra → Phase 34 C validated)\n\n> Tier 2 real-solver validated (Phase 34 C); not signed validation; not\n> benchmark agreement. The *CONTACT PAIR solver machinery is ccx-validated via\n> a stacked-cube uniaxial proxy — NOT Hertz curvature contact (future work).\n\n## Status\n\n**Phase 34 C outcome: tier_2_validated** (supersedes the Phase 33 D\nINFRASTRUCTURE_ONLY status below). Live ccx 2.23 *CONTACT PAIR cross-check\nPASS — 1D-exact δ=F·H/(E·A), residual −6.82% within the 20% envelope; cohort\n11 → 12. Honest scope: validates the contact-pair SOLVER mechanism, NOT Hertz",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "modal-cantilever-candidate",
    runnerAvailable: false,
    displayLabel: "Modal Cantilever · Tier 1 candidate",
    claimTier: "Tier 1 engineering candidate",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: "scripts/gen_modal_cantilever_deck.py",
    notesExcerpt: null,
    claimBoundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  },
  {
    caseId: "modal-cantilever-stiff-candidate",
    runnerAvailable: false,
    displayLabel: "Modal Cantilever Stiff · Tier 1 candidate",
    claimTier: "Tier 1 engineering candidate",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: "scripts/gen_modal_cantilever_stiff_deck.py",
    notesExcerpt: null,
    claimBoundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  },
  {
    caseId: "nafems-le10-thick-plate-candidate",
    runnerAvailable: true,
    solverKind: "linear_static",
    displayLabel: "NAFEMS LE10 Thick Plate · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# NAFEMS LE10 — Thick Plate Pressure (real ccx benchmark agreement)\n\n> **Tier 2 real-solver validated · PUBLIC-BENCHMARK AGREEMENT (NAFEMS LE10).**\n> NOT signed validation (no independent reviewer signoff per ADR-023 Tier-2-signed\n> / ADR-027 G-2). Real ccx 2.23 solve; sign normalized to the solver convention.\n\n## What this case is (V2-1 / ADR-027, 2026-06-03)\n\nThis is the project's **first genuine public-benchmark agreement** — every other\n`tier_2_validated` case is a real-ccx cross-check against an *analytical closed\nform*; this one compares a real ccx solve against the **published NAFEMS LE10\nreference value** σ_yy(D) = −5.38 MPa.",
    // V2-1 / ADR-027 (Codex R1 P1): LE10's tier_2 substantiation is a
    // public-benchmark agreement, NOT an analytical cross-check — mirrors the
    // backend CLAIM_BOUNDARY_OVERRIDES entry in _claim_tier.py.
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; public_benchmark_agreement_nafems_le10; sign_normalized_to_solver_convention",
  },
  {
    caseId: "plate-simply-supported-candidate",
    runnerAvailable: true,
    solverKind: "linear_static",
    displayLabel: "Plate Simply Supported · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# plate-simply-supported-candidate · NOTES\n\n> **Phase 25 A** — 5th tier_2_validated case. Closes Phase 24 retro\n> FEA Dim 2 \"validated count held flat at 4\". Promotion driven by\n> `cross_check_verdict.yaml` overlay in\n> `backend/app/services/reporting/_claim_tier.py:_apply_verdict_overlay`.\n\n## Geometry\n\n- `data/plate_ss.geo` — 1.0 m × 1.0 m × 0.020 m square steel plate.\n- a / t = 50 (well inside Kirchhoff thin-plate envelope a/t ≥ 20).\n- Origin at one corner; thickness extruded along +z.",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "plate-ss-shell-candidate",
    runnerAvailable: true,
    solverKind: "linear_static",
    displayLabel: "Plate SS Shell · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# plate-ss-shell-candidate — FM-04a Phase 29 A\n\n> Tier 1 / Tier 2 engineering candidate; not signed validation; not\n> benchmark agreement.\n\n## What this case validates\n\n**The first S4 (4-node quadrilateral shell) element case in the\nvalidated cohort.** Closes the FEA Dim 1 hard cap that has been\nload-bearing since Phase 18 (≤75/100). Prior 8 cases used\nC3D4 / C3D8 / C3D10 / B31 only.\n",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "rod-wave-impact-candidate",
    runnerAvailable: false,
    displayLabel: "Rod Wave Impact · Tier 1 candidate",
    claimTier: "Tier 1 engineering candidate",
    starterDeckRelpath: "golden_samples/rod-wave-impact-candidate/data/model_00_0000.rad",
    engineDeckRelpath: "golden_samples/rod-wave-impact-candidate/data/model_00_0001.rad",
    generatorScriptRelpath: "scripts/gen_rod_wave_impact_deck.py",
    notesExcerpt: "# rod-wave-impact-candidate — fixture notes\n\nTier 1 engineering candidate; not signed validation; not benchmark agreement.\n\n## Geometry\n\n* Rod length L = 1.0 m\n* Cross-section area A = 0.0001 m^2 (10 mm x 10 mm).\n* Material: SA-516 Gr.70 carbon steel (E = 2.000e+11 Pa, rho = 7850.0 kg/m^3).\n\n## Loading\n",
    claimBoundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  },
  {
    caseId: "rod-wave-impact-stiff-candidate",
    runnerAvailable: false,
    displayLabel: "Rod Wave Impact Stiff · Tier 1 candidate",
    claimTier: "Tier 1 engineering candidate",
    starterDeckRelpath: "golden_samples/rod-wave-impact-stiff-candidate/data/model_00_0000.rad",
    engineDeckRelpath: "golden_samples/rod-wave-impact-stiff-candidate/data/model_00_0001.rad",
    generatorScriptRelpath: "scripts/gen_rod_wave_impact_stiff_deck.py",
    notesExcerpt: "# rod-wave-impact-stiff-candidate — fixture notes\n\nTier 1 engineering candidate; not signed validation; not benchmark agreement.\n\nSibling of `rod-wave-impact-candidate` (Phase 14 D). The STIFF variant changes ONLY Young's modulus (200 GPa -> 210 GPa) so the analytical 1D-bar wave-propagation cross-check shifts to a faster wave and earlier reflection.\n\n## Geometry (unchanged from canonical)\n\n* Rod length L = 1.0 m\n* Cross-section area A = 0.0001 m^2 (10 mm x 10 mm)\n* Impact velocity v = 10.0 m/s at x = 0; far end at x = L is FREE\n",
    claimBoundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  },
  {
    caseId: "wedge-c3d6-candidate",
    runnerAvailable: true,
    solverKind: "linear_static",
    displayLabel: "Wedge C3D6 · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# C3D6 wedge — uniaxial Hooke's law (6th element class)\n\n> **Tier 2 real-solver validated** · genuine cross-check (real ccx + analytical).\n> Not signed validation; not benchmark agreement.\n\n## What this case is\n\nPhase 38 B adds the **6th element class** to the FM-04a validated cohort.\nPrior 5: C3D4 / C3D8 / C3D10 / S4 / B31. This case exhibits **C3D6** — the\n6-node linear pentahedral wedge — via a real ccx solve of a single wedge held\nin pure uniaxial stress, cross-checked against the closed-form Hooke's law.\n",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical",
  },
  {
    caseId: "nafems-le11-solid-cyl-temperature-candidate",
    runnerAvailable: true,
    solverKind: "linear_static",
    displayLabel: "NAFEMS Le11 Solid Cyl Temperature · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# NAFEMS LE11 — Solid Cylinder/Taper/Sphere, Temperature (candidate notes)\n\n**Second independent public-benchmark agreement** for this repo (after LE10). Real\nccx 2.23 thermo-elastic solve; σ_zz at point A = **−105.398 MPa** vs the published\n**−105 MPa** → **+0.38%**, PASS (tol 3%). Tier-1 engineering candidate /\npublic-benchmark agreement — **NOT signed validation** (no independent reviewer\nsignoff per ADR-023 / ADR-027 G-2).\n\n## Why LE11 (not LE1)\n\nLE1 (elliptic membrane) reuses LE10's *exact elliptical planform* + pure-elasticity\n+ `*DLOAD` family — a near-duplicate. LE11 is independent on **every** axis:",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; public_benchmark_agreement_nafems_le11; thermoelastic_imposed_temperature_field; sign_normalized_to_solver_convention",
  },
  {
    caseId: "nafems-le3-hemisphere-shell-candidate",
    runnerAvailable: false,
    displayLabel: "NAFEMS Le3 Hemisphere Shell · Tier 1 candidate",
    claimTier: "Tier 1 engineering candidate",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# NAFEMS LE3 — Hemispherical shell with point loads (CalculiX solver-limit study)\n\n> **This is NOT a benchmark agreement.** It is an honest record of a CalculiX\n> capability boundary. ccx converges to **ux@A = 0.2004 m**, **+8.3%** above the\n> NAFEMS thin-shell reference of **0.185 m**. Claim tier: **Tier-0 software-path +\n> documented limitation** — deliberately excluded from the tier_2 validated cohort.\n\n## What this case is\n\nThe repo's first attempt at a *shell / curved-geometry / bending* public benchmark,\nafter two solid benchmarks (LE10 thick-plate stress, LE11 solid thermo-elastic).\nNAFEMS LE3 is the canonical thin-shell point-load test: a hemisphere (R = 10 m,",
    claimBoundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  },
  {
    caseId: "rotating-disk-centrifugal-candidate",
    runnerAvailable: true,
    solverKind: "linear_static",
    displayLabel: "Rotating Disk Centrifugal · Tier 2 validated",
    claimTier: "Tier 2 real-solver validated",
    starterDeckRelpath: null,
    engineDeckRelpath: null,
    generatorScriptRelpath: null,
    notesExcerpt: "# Rotating annular disk, centrifugal load — CalculiX public-benchmark agreement\n\n> **Tier-2 real-solver validated public-benchmark agreement** (NOT signed validation).\n> The project's **third** public-benchmark agreement and its **first centrifugal /\n> rotational-body-force** load. ccx 2.23 reproduces the classical Timoshenko plane-stress\n> rotating-disk hoop stress at the bore: **observed 65.353 MPa vs analytic 65.312 MPa,\n> +0.063%** (canonical mesh), with the σ_θ(r)/σ_r(r) profile **along the +x radial line**\n> matching to ±0.1%.\n\n## What this case is\n\nA thin steel annular disk (inner radius a = 0.2 m, outer radius b = 1.0 m) spinning at",
    claimBoundary: "tier2_real_solver_validated; not_signed_validation; public_benchmark_agreement_rotating_disk_timoshenko; centrifugal_body_force_load; plane_stress_3d_elasticity_reference",
  },
]

// Server payload key → camelCase mapping for the React layer.
interface RawCandidateCaseRecord {
  case_id: string
  claim_tier: string
  starter_deck_relpath: string | null
  engine_deck_relpath: string | null
  generator_script_relpath: string | null
  notes_excerpt: string | null
  claim_boundary: string
}

interface RawCandidateCasePayload {
  claim_tier: string
  claim_boundary: string
  claim_impact: string
  count: number
  cases: RawCandidateCaseRecord[]
}

export function parseCandidateCasesPayload(
  raw: RawCandidateCasePayload | null | undefined,
): CandidateCaseRegistryPayload | null {
  if (!raw || typeof raw !== 'object' || !Array.isArray(raw.cases)) {
    return null
  }
  return {
    claimTier: raw.claim_tier,
    claimBoundary: raw.claim_boundary,
    claimImpact: raw.claim_impact,
    count: raw.count ?? raw.cases.length,
    cases: raw.cases.map((r) => ({
      caseId: r.case_id,
      claimTier: r.claim_tier,
      starterDeckRelpath: r.starter_deck_relpath,
      engineDeckRelpath: r.engine_deck_relpath,
      generatorScriptRelpath: r.generator_script_relpath,
      notesExcerpt: r.notes_excerpt,
      claimBoundary: r.claim_boundary,
    })),
  }
}

export interface CandidateCaseFetchResult {
  cases: CandidateCaseRecord[]
  source: 'live' | 'fallback'
  claimImpact: string
  error?: string
}

export async function fetchCandidateCases(
  apiBase: string,
  signal?: AbortSignal,
): Promise<CandidateCaseFetchResult> {
  const url = `${apiBase.replace(/\/$/, '')}/candidate-cases`
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) {
      throw new Error(`candidate-cases endpoint returned ${res.status}`)
    }
    const raw = (await res.json()) as RawCandidateCasePayload
    const parsed = parseCandidateCasesPayload(raw)
    if (!parsed) {
      throw new Error('candidate-cases payload missing cases array')
    }
    return {
      cases: parsed.cases,
      source: 'live',
      claimImpact: parsed.claimImpact,
    }
  } catch (err) {
    return {
      cases: FALLBACK_CANDIDATE_CASES,
      source: 'fallback',
      claimImpact:
        'Tier 1 candidate-case picker fallback (backend unreachable); not ' +
        'signed validation; not benchmark agreement',
      error: err instanceof Error ? err.message : String(err),
    }
  }
}

export function findCandidateCase(
  cases: CandidateCaseRecord[],
  caseId: string | null | undefined,
): CandidateCaseRecord | null {
  if (!caseId) return null
  return cases.find((c) => c.caseId === caseId) ?? null
}
