# ADR-020: Allowable-Stress Lookup — GB 150 / ASME VIII Div 2 (Room Temperature)

- **Status:** Draft (W6b — preparatory; depends on ADR-019 W6a landing)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — pending human-confirmation
- **Date:** 2026-04-27
- **Related Phase:** RFC-001 W6 — engineer-signs-DOCX gap closure
- **Branch:** `refactor/RFC-001-W6b-allowable-stress` (not yet opened)
- **Companion ADRs:** ADR-019 (material data model, W6a), ADR-021 (PASS/FAIL verdict, W6c)
- **Upstream:** RFC-001 §2.2 step 4 ("安全系数" deterministic generator), `docs/RFC-001-W6-roadmap.md` §2 W6b

---

## Context

ADR-019 (W6a) lands material data with `yield_strength` (σ_y) and `ultimate_strength` (σ_u). To go from σ_y/σ_u to a **PASS/FAIL verdict** (W6c), we need an **allowable stress** [σ] — and [σ] is **not** a property of the material alone. It is a function of:

- the material's σ_y and σ_u
- the **design code** (GB 150 / ASME VIII Div 2 / EN 13445)
- the **temperature** (room temp simplified for MVP; high-T deferred)
- the **product form / load category** (general membrane vs. local membrane vs. bending — ASME §5.5 stress classification)

The signing engineer's audit chain is: σ_max (from FE) ≤ [σ] (from code) → SF = [σ] / σ_max → PASS/FAIL. **Without [σ] the chain is broken**; LLM cannot supply [σ] (RFC-001 §2.4 rule 1, "LLM 不接触数字").

This ADR pins **which simplified formulas the wedge uses, where the data lives, and what it explicitly does not cover**, so a future engineer auditing a generated DOCX can trace every number back to a clause.

---

## Decision

### 1. API

```python
# backend/app/services/report/allowable_stress.py

@dataclass(frozen=True)
class AllowableStress:
    sigma_allow: float           # in material.unit_system's stress unit (MPa)
    code_standard: str           # "GB" | "ASME"
    code_clause: str             # "GB 150-2011 §4.1.5 Table 4" or similar
    formula_used: str            # human-readable, e.g. "min(σ_y / 1.5, σ_u / 3.0)"
    inputs: dict[str, float]     # {"sigma_y": 345, "sigma_u": 470, "temperature_C": 20}
    is_simplified: bool          # True iff using the room-temp simplified path

def compute_allowable_stress(
    material: Material,
    code: Literal["GB", "ASME"],
    temperature_C: float = 20.0,
) -> AllowableStress: ...
```

The function:
- raises `ValueError` if `material.code_standard` mismatches `code` AND there's no cross-reference (e.g. requesting "GB" allowable for a `SA-516-70` material — refuses, not auto-converts)
- raises `NotImplementedError` for `temperature_C > 50` in MVP — the simplified path is **room-temperature only**; high-T is deferred
- returns an `AllowableStress` with full provenance (`code_clause`, `formula_used`, `inputs`) so the DOCX can render it verbatim

### 2. Simplified formulas (MVP)

#### GB 150-2011 §4.1.5 (room temp ≤ 50 °C)

```
[σ] = min(σ_y / 1.5, σ_u / 3.0)         for carbon and low-alloy steel
[σ] = min(σ_y / 1.5, σ_u / 3.0)         identical formula for room temp; high-T diverges
```

`formula_used = "min(σ_y / 1.5, σ_u / 3.0)"`.
`code_clause = "GB 150-2011 §4.1.5 Table 4 (room temperature)"`.
`is_simplified = True`.

The 1.5 / 3.0 factors are **safety factors built into the code**, not the engineer's design margin. The engineer's margin is then SF = [σ] / σ_max ≥ 1.0 (W6c).

#### ASME VIII Div 2 §5.5 / Table 5A (room temp ≤ 100 °F ≈ 38 °C)

```
[σ] = min(σ_y / 1.5, σ_u / 2.4)         general primary membrane (Pm)
```

`formula_used = "min(σ_y / 1.5, σ_u / 2.4)"`.
`code_clause = "ASME VIII Div 2 §5.5.1 / Table 5A (Pm category, room temperature)"`.
`is_simplified = True`.

Local-membrane (PL) and bending (Pb) categories use **2× and 3×** [σ] respectively per §5.5.6 — but those are **stress classification** decisions that belong to the engineer, not the code calculator. The wedge returns the **base [σ]** and the engineer / template decides whether to multiply by 1.5 (PL+Pb) or 1.0 (Pm) based on the load category. This avoids the wedge silently applying a multiplier the engineer didn't authorize.

### 3. Why these formulas, and why simplified

**GB 150.3-2011 §4.1.5 Table 4** lists [σ] directly per grade per temperature. The simplified `min(σ_y/1.5, σ_u/3.0)` formula is **bounded above by Table 4** by construction (Table 4's footnote allows `σ_u/2.7` for low-alloy pressure-vessel grades, which is structurally larger than the simplified `σ_u/3.0`). Concretely:

| Material | σ_y | σ_u | Simplified `min(σ_y/1.5, σ_u/3.0)` | Table 4 (room T, approx.) | Gap |
|---|---|---|---|---|---|
| Q345B | 345 | 470 | `min(230.0, 156.7) = 156.7 MPa` | ~170 MPa | ~8% lower |
| Q345R | 345 | 510 | `min(230.0, 170.0) = 170.0 MPa` | ~170 MPa | none (yields drives) |
| 16MnR | 345 | 510 | `min(230.0, 170.0) = 170.0 MPa` | ~170 MPa | none (legacy = Q345R) |
| 20# | 245 | 410 | `min(163.3, 136.7) = 136.7 MPa` | ~140 MPa | small |

The gap shows up only when the **σ_u/3.0 leg dominates**, i.e. when Table 4 is using the more permissive `σ_u/2.7`. For grades where the σ_y/1.5 leg dominates (Q345R / 16MnR — high σ_u relative to σ_y), the simplified formula and Table 4 happen to coincide. The simplified path is **safe (conservative or equal)** — it never returns an [σ] higher than Table 4 — but it is **not** uniformly conservative-with-margin across every grade.

(Earlier revisions of this ADR cited "Q345R simplified = 156.7 MPa" — that calculation mixed Q345R's σ_y with Q345B's σ_u; the correct Q345R simplified value is 170.0 MPa as shown above. Codex R1 on PR #99 (W6c) caught a follow-up error: 16MnR has σ_u=510 in `materials.json` (legacy designation for Q345R, same chemistry), so 16MnR also produces 170.0 MPa — not a separate gap example. The table above reflects the actual seed data.)

We compute (and accept the conservative gap) rather than table-look-up because:

- a tabulated [σ] hides the formula; the auditor wants to see `σ_y / 1.5 = 230` not just "230 from Table 4"
- temperature interpolation (M4) is a different formula; bolting tabulated values into the API now means re-architecting later
- a conservative-or-equal bound is **the right wedge default**: the simplified formula never returns higher than Table 4 by construction (Table 4's `σ_u/2.7` ≥ simplified's `σ_u/3.0`), so the engineer can always trust the simplified value as a lower bound. Where the σ_u-leg dominates (e.g. Q345B: 156.7 vs Table 4 ~170), the simplified value is materially below Table 4; where the σ_y-leg dominates (e.g. Q345R: 170.0, same as Table 4), there is no gap. Engineers can override with a manual Table 4 lookup at the DOCX edit stage in any case.
- a regression test pins the value (`Q345R room-T simplified must be in [150, 170] MPa` — actual = 170.0 MPa, hits inclusive upper bound; the band catches future drift in either direction) so future changes can't silently move it

The DOCX renderer **must** flag `is_simplified=True` and explicitly state "本算式为简化算式（`σ_u/3.0`）；Table 4 对部分等级允许 `σ_u/2.7`，可能高 ~8%。如需精确值请查 Table 4"。

**ASME VIII Div 2 §5.5.1**: same reasoning. Table 5A has tabulated values; we compute and cite the formula to make the calculation traceable.

**Why not Eurocode (EN 13445) in W6b**: seed users (RFC-001 §3.2: 化工 / 电力 design institutes) overwhelmingly use GB 150 and ASME. Eurocode adds a third standards-citation surface for negligible seed-user benefit. M4+.

### 4. Data files

```
backend/app/data/allowable_stress_gb.yaml      # GB 150 §4.1.5 simplified factors
backend/app/data/allowable_stress_asme.yaml    # ASME VIII Div 2 §5.5 simplified factors
```

Each YAML file carries the **safety factors used**, **temperature range of validity**, and the **clause citation**. The Python module loads them at import time and exposes them as immutable dicts.

The factors themselves are short — both fit in <30 lines of YAML — but having them in YAML rather than a Python literal lets the engineering reviewer of the PR audit the numbers without reading Python.

### 5. DOCX rendering contract (W6b)

A new section `§ 许用应力 / Allowable Stress` between `§ 材料属性` and `§ 关键结果`:

```
§ 许用应力
设计依据：GB 150-2011 §4.1.5 Table 4 (常温 ≤ 50°C)
公式：[σ] = min(σ_y / 1.5, σ_u / 3.0) = min(345 / 1.5, 470 / 3.0)
                                       = min(230.0, 156.7)
                                       = 156.7 MPa

[若 temperature_C > 50] ⚠ 本计算限于常温；高温下 [σ] 须查 Table 4。
[若 is_simplified=True] 注：此为简化算式（`σ_u/3.0`）；Table 4 对部分等级允许 `σ_u/2.7`。本算式从不高于 Table 4，但在 σ_u-leg 主导时可能偏低 ~8%（参 §3 表）。如需精确值请查 Table 4。
```

Heading style level 1, formula rendering through a fixed template (no LLM), citation rendered as a hyperlink-styled paragraph.

### 6. Test surface

Four unit-test buckets:
- `test_allowable_stress_gb.py` — every GB material in `materials.json` produces a sensible [σ], all 4 fields populated, room-T only.
- `test_allowable_stress_asme.py` — same for ASME materials.
- `test_allowable_stress_cross_standard_refuses.py` — `compute_allowable_stress(Q345B, "ASME", ...)` raises `ValueError` (no auto cross-reference).
- `test_allowable_stress_high_T_refuses.py` — `temperature_C > 50` raises `NotImplementedError` with a clear "M4+ feature" message.

Plus one regression test pinning the **value** of Q345R simplified vs GB 150.3-2011 Table 4: Q345R room-T simplified [σ] must land in `[150, 170] MPa` (actual = 170.0 MPa, hits inclusive upper bound; the [150, 170] band catches drift in either direction — a yield-strength regression toward 220 MPa or an ultimate-strength regression toward 450 MPa would both trip). Test name: `test_simplified_vs_table4_conservative_gap_is_pinned`. Future changes that drift outside this band must be ADR-updated, not silently merged.

---

## Why this shape

1. **Compute > look-up** for traceability. The auditor wants to see the formula, not a magic number from a table.
2. **YAML > Python literal** for the factors so engineers can read the data without learning Python.
3. **Refuse cross-standard requests** rather than auto-cross-reference (e.g. "Q345B = SA-516-70 close enough"). The closest cross-references are documented in industry but **the wedge does not encode them** — wrong cross-reference is a sign-blocker. The engineer must explicitly choose the standard for their material.
4. **Refuse high-T silently** rather than extrapolating room-T factors. Extrapolation produces wrong numbers with no flag.
5. **Return base [σ], not load-category-multiplied** so the wedge doesn't silently apply Pm/PL/Pb logic the engineer didn't authorize. The template / W6c verdict step decides the category.
6. **`is_simplified` as a first-class field** so the DOCX can flag it. A future M4 PR can add tabulated lookups for high-T and flip `is_simplified=False`.

---

## What this does NOT decide

- **High-T allowable stress (T > 50 °C / 100 °F).** Deferred to M4. The simplified factors at high T diverge from tabulated values; need full Table 4 / 5A.
- **Stress classification (Pm vs. PL vs. Pb).** ASME §5.5 categories are engineer-driven decisions about load category, not material lookups. W6c may surface a category dropdown; ADR-021 will decide.
- **Welded-joint efficiency factor (E_j ≤ 1.0).** GB 150 / ASME apply E_j to [σ] for components with welds. This is a structure-level decision, not a material-level one. Deferred to W6c verdict computation; ADR-021 to specify.
- **Non-Pm load categories** — see point 5 above.
- **Eurocode EN 13445 / JIS B 8265 / GOST.** Out of MVP scope. The data-file structure (`allowable_stress_<code>.yaml`) is open to extension when needed.
- **Bolting allowables (different SF).** GB 150 Appendix / ASME II Part D Table 4 list special factors for bolts. Deferred — W6 wedge cases are pressure-vessel walls and equipment foundations, not bolted joints.
- **Aluminum / titanium / nickel / cast iron.** Out of scope per ADR-019 (W6a).

---

## Open questions deferred to user

- **GB 150-2011 vs GB 150.3-2011**: GB 150-2011 was superseded by GB 150.1-2011 / 150.3-2011 in 2012. Current Chinese pressure-vessel work uses GB 150.3 in practice; the wedge cites which one? (Default per ADR-020: cite GB 150.3-2011 §4.1.5 — matches actual current usage.)
- **Citation language**: section headings / DOCX text in Chinese only, English only, or bilingual? (Default per ADR-020: bilingual heading "§ 许用应力 / Allowable Stress", citations in original language only.)
- **Floor under [σ]**: some institutes apply a global lower bound of 80 MPa even when the formula gives lower (esp. for thin sections at high T). Should the wedge ever floor? (Default per ADR-020: never. The formula stands. Engineer can manually override in DOCX edit.)

---

## Revision history

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-04-27 | Initial draft prepared during Codex outage window. Awaits user buy-in on GB 150 vs 150.3 citation + bilingual policy. |
| 0.2 | 2026-04-27 | Self-correction after spot-check: simplified formula is **bounded above by Table 4 by construction** (σ_u/3.0 ≤ σ_u/2.7), not "within ±2 MPa". The gap is non-uniform: it appears only when the σ_u-leg governs (Q345B 156.7 vs Table 4 ~170, ~8% lower), and disappears when the σ_y-leg governs (Q345R / 16MnR 170.0, equal to Table 4). Pinned the value via regression test, added DOCX disclaimer. See §3 truth table for per-grade values. |
| 0.3 | 2026-04-28 | W6c PR #99 cleanup (Codex R1 / R2 / R3): corrected the Q345R "156.7" calculation typo (actual = 170.0); fixed 16MnR claim (also 170.0, not the gap example); rewrote uniform "~8%" claims at §3.1 / §5 / revision-history / `allowable_stress_gb.yaml` docx_disclaimers to reflect the §3 truth table — the gap is conditional on which leg governs. |
