# FM-04a Phase 14 C — TAA Audit Report

**Commit:** `9aba727` (`claude/FM-04a-tier1-ballistic-candidate`)
**Slice:** C — StubAdvisor explicit_dynamics branch (4 themes)
**Auditor:** Test Auditor Agent (independent adversarial review)
**Date:** 2026-05-17
**Blueprint:** `.planning/FM-04A_PHASE14_BLUEPRINT.md` §3.C

---

## Scope under review

* `backend/app/services/reporting/advisor_critique.py` (+79 / -10) — new
  `explicit_dynamics` branch at lines 293-368, mirroring the Phase 12 B
  modal-advisor-branch pattern.
* `tests/test_phase14_advisor_explicit_dynamics_branch.py` (new, 301 LOC,
  12 tests).
* `backend/app/services/reporting/explicit_dynamics_extraction.py` +
  `.planning/methodology/explicit_dynamics_cross_check.md` — slice B
  TAA LOW-1 docstring index correction (`[3]` → `[2]`).
* `.planning/phase14_audit_reports/B.md` — slice B audit archived.

---

## Verification commands

| # | Command | Result |
|---|---------|--------|
| 1 | `pytest tests/test_phase14_advisor_explicit_dynamics_branch.py -v` | **12 passed** |
| 2 | `pytest tests/test_phase11_advisor_critique.py tests/test_phase12_modal_advisor.py -q` | **78 passed**, no regression |
| 3 | `pytest tests/ -q` (full backend sweep) | **2362 passed, 7 skipped** in 24.30s |

Baseline target: ≥2362 (2280 + 38 slice A + 32 slice B + 12 slice C). **Met exactly.**

---

## Adversarial probes

### Probe 1 — 9 forbidden positive-claim tokens in the new branch

Extracted the `elif context.convergence_kind == "explicit_dynamics":` block
(lines 293-368) and scanned all string-literal content:

```
OK: 'validated against' absent
OK: 'perforation completed' absent
OK: 'bullet-through-steel complete' absent
OK: 'validated physics' absent
OK: 'production ready' absent
OK: 'certified' absent
OK: 'approved for service' absent
OK: 'asme compliant' absent
OK: 'signed off' absent
```

All 9 forbidden tokens absent (test 11 also enforces this with a
`not <claim>` carve-out — none triggered).

### Probe 2 — Tier 2 promoting language

Scanned for `tier 2`, `tier-2`, `promote to tier`, `production`,
`release`, `qualified`, `approved` in the new branch — **all absent**.
C cap to ≤10 is NOT triggered.

### Probe 3 — Theme-header pattern + marker uniqueness

After Python string-literal concatenation, the four theme-headers are:

| Theme | Header (case-preserving) | Surface | Marker token (UNIQUE) |
|-------|-------------------------|---------|----------------------|
| 1 | `explicit_dynamics CFL stability:` (×2) | bc_question + failure_mode | `CFL` |
| 2 | `explicit_dynamics energy partition closure:` | mesh_concern | `energy partition` |
| 3 | `explicit_dynamics contact stiffness convergence:` | mesh_concern | `contact stiffness convergence` |
| 4 | `explicit_dynamics wave reflection vs boundary condition:` | bc_question | `wave reflection` |

4 unique theme-headers, exactly as blueprint §3.C requires. Theme 1
appears on TWO surfaces (bc_question + failure_mode) by design — the
slice C test asserts `len(cfl_questions) == 1 AND len(cfl_failures) == 1
AND cfl_questions[0] != cfl_failures[0]` (distinct content, not
boilerplate).

The bare phrase `contact stiffness` appears 3 times (1× theme 3 header,
2× theme 3 body), and `contact stiffness too soft` (split across lines
335-336) appears 1× inside theme 2's body as a cross-reference to
theme 3 — this is acceptable engineering content (energy-partition
failure modes legitimately enumerate contact stiffness too soft as one
cause of energy leakage). The meta-test (`test_contact_stiffness_theme_emitted_distinctly`)
correctly anchors on the **full theme-header phrase**
`contact stiffness convergence`, which appears exactly once. A future
maintainer who tries to satisfy the test by sneaking the bare marker
`contact stiffness` into theme 2's body would NOT satisfy the assertion
unless they use the full theme-header phrase — which would then trip
`test_themes_are_distinct_strings`. Anti-gaming pattern is sound.

### Probe 4 — No marker bleed into Phase 11 ballistic / linear_static_pv contexts

Live invocation of `build_advisor_critique` with `convergence_kind=
"ballistic"` and `convergence_kind="linear_static"`:

```
ballistic context contains cfl: False
ballistic context contains wave reflection: False
ballistic context contains energy partition: False
ballistic context contains contact stiffness convergence: False
linear_static_pv contains cfl: False
linear_static_pv contains wave reflection: False
linear_static_pv contains energy partition: False
```

Zero bleed. The `elif`-chain isolation is correct.

### Probe 5 — Engineering substance (E axis)

| Theme | Physical mechanism cited | Concrete sweep / cross-check |
|-------|-------------------------|------------------------------|
| 1 | CFL conditional stability of explicit time integration (`dt ≤ Δx_min / c_wave`); mass scaling >2-5% as Phase 11 token-back-compat anchor | dt sweep "converged within 5% on metric of interest"; element-by-element wave-speed audit |
| 2 | Per-frame K+I energy MUST sum to external work | `energy_partition_audit drift_fraction` 1% default; enumeration of injection sources (contact too soft / hourglass leakage / mass-scaling cutoff) |
| 3 | Hourglass control coefficient + contact stiffness scale factor coupling | "0.1x / 1x / 10x" stiffness sweep + hourglass coefficient within solver-recommended bounds |
| 4 | Free vs clamped sign-flip on reflected stress wave | cites `bar_wave_first_reflection_s` from slice-B `explicit_dynamics_extraction` — direct cross-module integration |

All four themes name a real physical mechanism + a concrete check.
No boilerplate "review this concern". The slice-B cross-reference
(theme 4 → `bar_wave_first_reflection_s`) is a strong inter-slice
integration signal.

### Probe 6 — 4Q gate + Tier 1 disclaimer trio

`test_four_question_gate_fires_on_explicit_dynamics_branch` asserts every
key in `FOUR_QUESTION_GATE_KEYS` is present and `True`.
`test_tier1_disclaimer_trio_preserved_on_explicit_dynamics_envelope`
asserts `claim_tier="Tier 1 engineering candidate"`,
`claim_boundary` carries `not_signed_validation` + `not_benchmark_agreement`,
`claim_impact` carries the lower-case prose form. Both pass.

---

## Scoring (per blueprint §3.C sub-rubric)

| Axis | Score | Floor | Justification |
|------|-------|-------|---------------|
| **M (Methodology)** | **12 / 12** | 10 | All 4 themes named in code with the `explicit_dynamics <theme>:` theme-header pattern. No silent consolidation. Comments at lines 304/329/342/355 explicitly call out theme N + the marker token. Cap M ≤ 10 NOT triggered. |
| **T (Testing)** | **15 / 15** | 10 | 12 tests delivered (≥10 required). Each of the 4 themes asserted distinctly (tests 2/3/4/5). Phase 11 + Phase 12 branches asserted unchanged (tests 7/8). 4Q gate fires (test 9). Tier 1 trio preserved (test 10). Legacy `mass scaling` / `dt` Phase 11 token guard (test 12). 9 forbidden tokens absent (test 11). Themes-are-distinct anti-boilerplate guard (test 6). |
| **C (Coverage)** | **12 / 12** | 10 | All 9 forbidden positive-claim tokens absent. No Tier 2 promoting language anywhere. Cap C ≤ 10 NOT triggered. |
| **A (Anti-gaming)** | **8 / 8** | 6 | Each theme carries a UNIQUE marker token (`CFL` / `energy partition` / `contact stiffness convergence` / `wave reflection`). Meta-tests grep by the FULL theme-header phrase (`contact stiffness convergence`, not bare `contact stiffness`) — a future maintainer inserting the marker into a different theme's body trips either the count-1 assertion or the `test_themes_are_distinct_strings` assertion. |
| **E (Evidence)** | **8 / 8** | 7 | Every theme cites a real physical mechanism + a concrete sweep / cross-check (probe 5 table). Theme 4 cross-references the slice-B `bar_wave_first_reflection_s` function — direct inter-slice integration. No boilerplate. |
| **V (Verification)** | **8 / 8** | 7 | Full sweep at exactly 2362 passed (target hit; +12 from baseline 2350). Phase 11/12 regression suites 78/78 green. No regression. Cap V ≤ 7 NOT triggered. |
| **Total** | **63 / 63** | — | — |

---

## Findings

### None at any severity.

The slice C implementation closes its own scope cleanly and additionally
closes the **slice B TAA LOW-1** docstring-drift carry-forward
(`ANALYSIS_TYPE_TUPLE[3]` → `[2]` in `explicit_dynamics_extraction.py`
and `methodology/explicit_dynamics_cross_check.md`). The slice B audit
report is correctly archived to `.planning/phase14_audit_reports/B.md`.

The theme-header pattern is robust against the canonical anti-gaming
attack vector (sneaking a marker token into a different theme's body
to satisfy a grep-based test) — the meta-tests anchor on the full
theme-header phrase (`contact stiffness convergence`, not bare
`contact stiffness`), and the `test_themes_are_distinct_strings`
catches set/list-cardinality regressions.

---

## Verdict

**APPROVE** — 63 / 63, zero HIGH / MEDIUM / LOW findings, every axis at
ceiling, full backend sweep at exactly the targeted 2362 passing tests,
no Phase 11 / Phase 12 regression, slice-B LOW-1 closed as a bonus.

Slice C is cleared for arc continuation to slice D (real-runnable
explicit dynamics candidate case fixture under
`golden_samples/rod-wave-impact-candidate/`).
