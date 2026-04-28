# ADR-019: Material Properties Data Model — Built-in Library + Free Input

- **Status:** Draft (W6a — preparatory; lands when PR #90 W5f merges + Codex restored)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — pending human-confirmation
- **Date:** 2026-04-27
- **Related Phase:** RFC-001 W6 — engineer-signs-DOCX gap closure
- **Branch:** `refactor/RFC-001-W6a-material-properties` (not yet opened)
- **Companion ADRs:** ADR-020 (allowable-stress lookup, W6b), ADR-021 (PASS/FAIL verdict, W6c)
- **Upstream:** RFC-001 §2.2 step 4 ("材料属性表" deterministic generator), `docs/RFC-001-W6-roadmap.md` §2 W6a

---

## Context

`backend/app/core/types/domain.py:46-58` already exposes a `Material` dataclass — but the wedge has nowhere to **source** material data:

- The `.frd` file (CalculiX result) does not carry material info.
- The `.inp` file (CalculiX input) carries `*MATERIAL` blocks, but the wedge does not parse them today.
- The Electron shell has no material input UI.
- `Material` itself only carries `name / youngs_modulus / poissons_ratio / density` — **no `yield_strength`, no `ultimate_strength`, no code reference.** Without σ_y and σ_u, the safety-factor / PASS-FAIL chain (W6b/W6c) is structurally impossible.

The signing engineer's first audit of any DOCX is "what material did the analysis use, and what's the source?". A blank or wrong material is a sign-blocker; an unverified LLM-supplied number is worse.

This ADR pins **how material data enters the system** and **how it is shown in the DOCX**, before any UI or DOCX work begins.

---

## Decision

### 1. Extend `Material` schema

```python
@dataclass(frozen=True)
class Material:
    name: str                             # e.g. "Q345B" or "SA-516-70"
    youngs_modulus: float                 # in unit_system's stress unit
    poissons_ratio: float
    density: float | None
    yield_strength: float                 # σ_y, in stress unit (NEW)
    ultimate_strength: float              # σ_u, in stress unit (NEW)
    code_standard: str                    # "GB" | "ASME" | "EN" (NEW)
    code_grade: str                       # canonical grade per the standard (NEW)
    source_citation: str                  # e.g. "GB/T 1591-2018 Table 7" (NEW)
    unit_system: UnitSystem
    is_user_supplied: bool = False        # True iff free-input, triggers [需工程师确认] flag (NEW)
```

`is_user_supplied=True` materials are rendered with a `[需工程师确认]` flag in the DOCX (RFC-001 §2.4 rule 4).

### 2. Built-in material library: `backend/app/data/materials.json`

A read-only JSON file with **10–15 entries** scoped to **carbon steel + low-alloy steel** common in Chinese chemical / power design institutes (matching RFC-001 §3.2 seed-user demographics). Every entry carries the full Material schema + a `source_citation` to a specific clause of the originating standard.

Why a JSON file (not a Python module):
- Easier to audit by non-Python engineers (the seed users themselves).
- Trivially diffable across versions of the standards.
- Loadable without import-time side effects.

Why **only carbon + low-alloy steel** in W6a:
- 90% of seed-user (chemical / power) reports use these.
- Stainless / aluminum / cast iron deferred to M4 — adding them to the JSON is mechanical, but the testing surface and standards-citation work multiplies.

The library schema is frozen by this ADR; new materials can be added without ADR (data-only PR), but field renames / removals require an ADR-019 update.

### 3. Free-input fallback

When the engineer's material isn't in the built-in library, the Electron form must allow **free-form numeric input**. Free-input materials:

- get `is_user_supplied=True`
- get `source_citation = "工程师自录入"` (or whatever the user typed)
- DOCX renders the row with a `[需工程师确认]` flag
- DOCX appendix lists the user-supplied values verbatim with a "工程师须复核" caveat

**LLM never edits a Material**. The material card flows from Electron → Layer-2 ReaderHandle → Layer-3 → Layer-4 DOCX renderer as-is. This is a hard rule per RFC-001 §2.4 rule 1 ("LLM 不接触数字").

### 4. Where material data joins the pipeline

```
Electron form (W6a UI)
      ↓ IPC: req.material = "Q345B" | { custom: {...} }
report-cli (W6a CLI flag: --material Q345B  OR  --material-json path)
      ↓
ReaderHandle.materials  (Layer-2 protocol, already exists)
      ↓
Layer-4 DOCX renderer: §"材料属性" section (W6a)
      ↓ same Material object referenced by W6b allowable-stress lookup
```

`--material-json` accepts a path to a JSON file matching the Material schema, for the case where engineers maintain their own institute-specific library.

### 5. DOCX rendering contract (W6a)

A new section `§ 材料属性 / Material Properties` between `§ 模型概况` and `§ 边界条件`:

```
§ 材料属性
| 牌号    | 弹性模量 E   | 泊松比 ν | 屈服强度 σ_y | 抗拉强度 σ_u | 标准引用       |
| ------ | ---------- | ------- | ----------- | ----------- | ------------ |
| Q345B  | 2.06×10⁵   | 0.30    | 345 MPa     | 470 MPa     | GB/T 1591    |

[若 is_user_supplied=True] ⚠ 数值由工程师自录入，须复核。
```

Heading style matches existing template (level 1). Numeric formatting goes through the existing `format_number` helper to keep precision discipline.

### 6. Test surface

Three unit-test buckets:
- `test_material_library_load.py` — every JSON entry parses, fields complete, units consistent within unit-system.
- `test_material_dropdown_flow.py` — Electron form picks built-in → CLI receives `--material Q345B` → DOCX renders correct row.
- `test_material_user_supplied_flow.py` — free-input → flag appears in DOCX, JSON sidecar records `is_user_supplied=True`.

E2E: the GS-001 demo button must be updated to default to a real built-in material (Q345B suggested) so the demo DOCX has a non-blank materials section out of the box.

---

## Why this shape

1. **JSON > Python module** for the library because the eventual maintainers are mechanical engineers (RFC-001 §3 seed users), not Python programmers. A JSON file with field names in English + Chinese standard citations is auditable by them.
2. **Frozen schema, open data** — adding a new steel grade is a data-only PR with no schema migration. Removing a field is an ADR-019 update.
3. **`is_user_supplied` as a first-class field** rather than a string convention — the DOCX renderer checks this boolean to decide whether to inject the `[需工程师确认]` flag, no string-matching ambiguity.
4. **Numeric input never leaves the Electron form unsanitised** — preload.cts validates floats, rejects NaN / negative E / negative σ_y, and refuses to forward bad input to the CLI. CLI also re-validates (defense in depth, per the RETRO-V61-053 executable-smoke-test risk_flag).
5. **Carbon + low-alloy first** is a deliberate scope cut — see RFC-001 §3.2 seed demographics.

---

## What this does NOT decide

- **Allowable-stress σ_allow lookup** — ADR-020 (W6b) handles `compute_allowable_stress(material, code, T)`. ADR-019 only pins how σ_y / σ_u get into the system; turning them into an allowable is W6b's job.
- **Temperature dependence** — W6a is room-temperature only. The schema does **not** carry temperature-dependent E / σ_y curves; M4 will extend with a `temperature_curves: dict[float, MaterialAtTemp]` field if seed-user demand confirms.
- **Plasticity / damage / creep** — out of scope (RFC-001 §2.3 wedge limits to linear-elastic static).
- **Material auto-detection from `.inp`** — possible later, but UI-driven entry is primary because seed users may run analyses set up by colleagues with hand-edited materials they want to override.
- **Sharing user-supplied material entries across projects** — out of scope (Desktop-first, single-user, no cloud).

---

## Initial library content (frozen by this ADR)

The following 12 grades go into `materials.json` v1. Source citations point to the **2018 / 2011 / current** revision of each standard; later revisions require a JSON data-only PR with a citation update.

| # | code_grade | code_standard | E (MPa) | ν | σ_y (MPa) | σ_u (MPa) | source_citation |
|---|---|---|---|---|---|---|---|
| 1 | Q235B | GB | 200000 | 0.30 | 235 | 370 | GB/T 700-2006 §5.1 Table 3 |
| 2 | Q345B | GB | 206000 | 0.30 | 345 | 470 | GB/T 1591-2018 §6.2 Table 7 |
| 3 | Q345R | GB | 206000 | 0.30 | 345 | 510 | GB 713-2014 §5.2 Table 5 |
| 4 | Q370R | GB | 206000 | 0.30 | 370 | 530 | GB 713-2014 §5.2 Table 5 |
| 5 | 16MnR | GB | 206000 | 0.30 | 345 | 510 | GB 713-2008 §5.2 (legacy designation, kept for older project files) |
| 6 | 15CrMoR | GB | 206000 | 0.30 | 295 | 450 | GB 713-2014 §5.2 Table 6 |
| 7 | 14Cr1MoR | GB | 206000 | 0.30 | 310 | 520 | GB 713-2014 §5.2 Table 6 |
| 8 | 20# | GB | 206000 | 0.30 | 245 | 410 | GB/T 699-2015 §5.1 Table 4 |
| 9 | SA-516-70 | ASME | 200000 | 0.30 | 260 | 485 | ASME II Part A SA-516/SA-516M Table 2 |
| 10 | SA-105 | ASME | 200000 | 0.30 | 250 | 485 | ASME II Part A SA-105/SA-105M Table 2 |
| 11 | SA-106-B | ASME | 200000 | 0.30 | 240 | 415 | ASME II Part A SA-106/SA-106M Table 2 |
| 12 | SA-387-Gr11-Cl2 | ASME | 200000 | 0.30 | 310 | 515 | ASME II Part A SA-387/SA-387M Table 2 |

Unit system: **si-mm** for all entries (MPa = N/mm² aligns with the wedge's default unit_system per RFC-001 §4.6). Entries in **SI base** (Pa) are out of scope; conversion happens at the boundary if a different `unit_system` is requested.

ν=0.30 is the standard textbook value for structural steel; deviations are not represented at this revision.

---

## Migration / backwards-compat

- The `Material` dataclass is `frozen=True`; adding fields with defaults (`is_user_supplied: bool = False`) is non-breaking for existing callers.
- The new required fields (`yield_strength`, `ultimate_strength`, `code_standard`, `code_grade`, `source_citation`) **are** breaking — every existing call site that constructs a `Material` (currently: zero in production code, two in tests) must be updated.
- `ReaderHandle.materials` returns `dict[str, Material]`; existing consumers index by `name`, no API change there.

---

## Open questions deferred to user

- **Library coverage edge case**: should we include 304 / 316L (austenitic stainless) in v1, given some pressure-vessel work uses them? (Default per ADR-019: no — defer to M4. User can override.)
- **Free-input flag wording**: `[需工程师确认]` vs `[USER-SUPPLIED]` vs both bilingual? (Default per ADR-019: Chinese flag in DOCX, English log line in CLI for parser-friendliness.)
- **Default material for GS-001 demo**: Q345B (low-alloy, common) vs Q235B (basic, ubiquitous)? (Default per ADR-019: Q345B — matches the typical "设备基础" wedge case.)

---

## Revision history

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-04-27 | Initial draft prepared during Codex outage window (2026-04-27 → 04-29). Awaits user buy-in on library scope + free-input wording before implementation. |
