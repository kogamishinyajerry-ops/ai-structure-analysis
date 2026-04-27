# ADR-016: `.frd` → `.vtu` Conversion + Result Visualization

- **Status:** Draft (parallel to ADR-014, ADR-015, ADR-017)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
- **Date:** 2026-04-26
- **Related Phase:** 2.1 — Engineer Entry & Run Submission (viz consumed in 2.2)
- **Branch:** `feature/AI-FEA-ADR-016-frd-vtu-result-viz`
- **Companion ADRs (Draft, parallel):** ADR-014 (WS event bus), ADR-015 (workbench → agent RPC), ADR-017 (RAG facade)

---

## Context

The workbench's last surface to design is **the result-viewer**. The engineer who submitted a SimPlan in Phase 2.1, watched it stream through the agent graph via ADR-014's WS bus, and saw a green `run.finished` now needs to see *what the simulation actually produced* — deformation, stress, mode shapes — without leaving the browser.

CalculiX writes results to a `.frd` file (mixed ASCII/binary, CalculiX-specific). Three options for getting that on screen:

1. **PNG snapshots from the backend.** Cheap. Static. Loses interactivity (can't rotate, can't probe, can't switch between fields).
2. **ParaView Web / Trame.** Full ParaView in the browser. Heavy (Python service + WebGL bridge). Already evaluated in `cfd-ai-workbench` and rejected for similar reasons there (see Notion: 2026-04-11 v1.6.0 migration).
3. **Convert `.frd` → `.vtu` (VTK XML UnstructuredGrid) and render with vtk.js in the browser.** vtk.js takes the `.vtu` blob directly; rendering, picking, color-mapping all run client-side. Backend becomes a static-file server for the `.vtu` artifact.

This ADR commits to **option 3** and pins the contract.

The corresponding constraint is that we already have a mature `backend/app/parsers/frd_parser.py` (CalculiX `.frd` → typed Python dataclasses, multi-increment aware). We do NOT have a `.vtu` writer. ADR-016 specifies the writer's contract; the implementation lands as a Phase 2.2 PR.

---

## Decision

**Pipeline:** `.frd` (CalculiX) → `FRDParseResult` (existing parser) → `.vtu` (new writer, Phase 2.2) → `vtk.js` in browser (new frontend, Phase 2.2).

**Storage path:** every run that produces results writes to `runs/{run_id}/viz/`:
- `mesh.vtu` — geometry + topology (one per run, written once)
- `field_{increment_index}_{field_name}.vtu` — per-increment, per-field result (deformation, von Mises, principal stresses, mode shape)
- `manifest.json` — index of which fields exist, increment metadata (step, type, value), units, and BBox for camera framing

**Format:** ASCII VTK XML (not binary VTU). Reasons:
1. vtk.js's `vtkXMLUnstructuredGridReader` handles ASCII directly; binary requires base64 + zlib, doubles backend complexity.
2. Compressed-on-the-wire by HTTP gzip is ~2× bigger than binary VTU but the browser doesn't care.
3. Diffability: ASCII `.vtu` files diff cleanly in golden-sample regression tests; binary doesn't.
4. The size ceiling that breaks ASCII (>50 MB per increment) corresponds to meshes >500k cells — not Phase 2.x territory. Phase 3 may revisit.

**No streaming, no chunking, no progressive rendering.** vtk.js loads the full `.vtu` and renders. The backend writes the artifact when CalculiX finishes; the frontend fetches when the user opens the viewer. Simple and matches the synchronous Phase 2.1 flow (results are ready before the viewer opens).

**No surface extraction in Phase 2.x.** vtk.js renders the volumetric mesh directly. Surface-only rendering (faster for >100k cells) is a Phase 3 optimization driven by measured performance, not assumed.

**No animations of mode shapes in Phase 2.x.** Mode shapes are scalar magnitude visualizations on a static mesh; the user can scrub through increments via UI, but we do not write per-frame interpolated meshes. Phase 3 add if requested.

---

## Field selection

The `.vtu` files emit a deliberate subset of `FRDParseResult`:

| Source | `.vtu` representation | Phase | Notes |
|--------|----------------------|-------|-------|
| `nodes[i].coords` | `<Points>` | 2.2 | always present |
| `elements[i]` (C3D4, C3D8, C3D10, C3D20, S3, S4, B31, …) | `<Cells>` | 2.2 | initial coverage: tet4/tet10/hex8/hex20/tri3/quad4 (covers all golden samples) |
| `displacements[i]` | `<PointData Name="displacement" type="Float32" NumberOfComponents="3">` | 2.2 | per-increment field; magnitude derived in vtk.js |
| `stresses[i].von_mises` | `<PointData Name="von_mises" type="Float32">` | 2.2 | per-increment field |
| `stresses[i].max_principal` | `<PointData Name="max_principal" type="Float32">` | 2.2 | per-increment field |
| `stresses[i].S11..S23` | (NOT emitted Phase 2.2) | 3 | tensor components rarely useful at the workbench tier; defer |
| `strains` | (NOT emitted Phase 2.2) | 3 | strain field not in FailurePattern signal set; defer |

The "(NOT emitted)" rows are deliberate scope bounds. A Phase 3 ADR can add them when a concrete consumer (reviewer agent, advisor) needs them.

---

## `manifest.json` schema

```json
{
  "schema_version": "v1",
  "run_id": "RUN-2026-04-27-abc123",
  "mesh": {
    "uri": "mesh.vtu",
    "n_nodes": 1234,
    "n_elements": 567,
    "element_types": ["C3D10"],
    "bbox": {"min": [0.0, 0.0, 0.0], "max": [10.0, 1.0, 1.0]},
    "units": {"length": "m"}
  },
  "increments": [
    {
      "index": 0,
      "step": 1,
      "type": "static",
      "value": 1.0,
      "fields": {
        "displacement":  {"kind": "displacement",  "uri": "field_0_displacement.vtu",  "units": "m",  "max_magnitude": 0.0023},
        "von_mises":     {"kind": "von_mises",     "uri": "field_0_von_mises.vtu",     "units": "Pa", "min": 0.0,    "max": 1.4e8},
        "max_principal": {"kind": "max_principal", "uri": "field_0_max_principal.vtu", "units": "Pa", "min": -1.1e8, "max": 9.8e7}
      }
    }
  ],
  "writer": {
    "tool": "app.viz.frd_to_vtu",
    "version": "0.1.0",
    "frd_parser_version": "(from FRDParseResult)",
    "wrote_at": "2026-04-27T12:34:56Z"
  }
}
```

Pydantic v2 frozen + `extra="forbid"` schema lives in `schemas/viz_manifest.py`. The viewer fetches `manifest.json` first to populate the UI (which fields exist, which increment to default to, what color-map range to use); then fetches the specific `.vtu` URI on demand.

The `units` field is **populated from the originating SimPlan**, not inferred from `.frd` (the FRD format does not record units). This requires `run_orchestrator` (ADR-015) to pass the SimPlan's units into the writer.

---

## Authorization

`GET /runs/{run_id}/viz/manifest.json` and `GET /runs/{run_id}/viz/{filename}` are gated by the same `X-Workbench-Token` header from ADR-015. The viewer SPA stores the token in `sessionStorage` (cleared when the tab closes) and adds it to the `X-Workbench-Token` request header on each fetch. **Not** an HTTP-only cookie — JS cannot read those, so the SPA cannot include them as a custom header. The browser-tab-confined storage is acceptable for Phase 2.1's single-trusted-operator-per-server scope (per ADR-014); a multi-operator Phase 3 ADR will revisit.

**No CDN / external storage.** Phase 2.x serves `.vtu` from the workbench backend's local filesystem. Phase 3 may consider object storage if multi-host becomes useful.

---

## Static check — viz contract

A new test, `tests/test_viz_manifest_schema.py`, asserts the `manifest.json` shape. A second test, `tests/test_frd_to_vtu_writer.py` (Phase 2.2 follow-up), asserts:

1. **Round-trip on golden samples:** `.frd` from `golden_samples/GS-001..003/` parses → writes `.vtu` → vtk Python reader re-parses without error → node count, cell count, displacement magnitude match the original `FRDParseResult`.
2. **No Inf / NaN values.** A `.vtu` with `Inf` in `<PointData>` would crash vtk.js silently. Writer must filter or fail loudly.
3. **Cell-type coverage.** Every CalculiX element type in the golden samples has a documented VTK cell-type mapping. New CalculiX types that the FRD parser handles but the writer doesn't are skipped + logged + counted in `manifest.skipped_cells`.
4. **Manifest validates against `schemas.viz_manifest`** (Pydantic v2 frozen, `extra="forbid"`).

Phase 2.2 follow-up PRs implement the writer and tests. This ADR PR adds only the schema stub + the manifest-shape test.

---

## Frontend rendering choice

**vtk.js, no ParaView Web.** Reasons:

1. vtk.js is npm-installable; no Python service required for the viewer.
2. The bundle is large (~5 MB minified) but cached after first load and gzips well.
3. Picking, threshold filtering, and color-map switching all run client-side — no backend round-trip per UI interaction.
4. ParaView Web's Trame stack would force a separate Python service alongside the FastAPI backend, doubling the deploy surface for one feature.

The frontend code lands in `frontend/src/viz/` (Phase 2.2). Outside this ADR's scope.

---

## Considered alternatives

### PNG snapshots from a backend ParaView/PyVista session
Pros: tiny artifacts; trivial to embed in markdown reports.
Cons: no interactivity. Cannot rotate/probe. Forecloses the use case ADR-014 was designed for ("engineer sees stepwise visibility"). **Rejected.**

### ParaView Web (Trame)
Pros: full ParaView feature set in the browser.
Cons: separate Python service; WebGL bridge complexity; deploy doubled. Phase 3 may revisit if Phase 2.2 vtk.js performance is insufficient on real meshes. **Rejected for now.**

### Custom Three.js renderer reading raw `.frd`
Pros: minimal dep set.
Cons: re-implements VTK's 20-year unstructured-grid pipeline. **Rejected.**

### Binary VTU (base64 + zlib `<DataArray>`)
Pros: ~2× smaller files; faster gzip.
Cons: writer complexity; harder to diff in tests; vtk.js handles ASCII just as well. Phase 3 may revisit if file-size ceilings bite. **Rejected for now.**

---

## Implementation plan

| File | Status | Owner | Notes |
|------|--------|-------|-------|
| `docs/adr/ADR-016-frd-vtu-result-viz.md` | this PR | Claude Code | M1 trigger |
| `schemas/viz_manifest.py` | this PR | Claude Code | Pydantic v2 frozen schema (M2) |
| `tests/test_viz_manifest_schema.py` | this PR | Claude Code | shape assertions on `viz_manifest` (M2) |
| `backend/app/viz/__init__.py` | this PR | Claude Code | package marker referencing ADR-016 |
| `backend/app/viz/frd_to_vtu.py` | Phase 2.2 follow-up | Claude Code | the writer |
| `tests/test_frd_to_vtu_writer.py` | Phase 2.2 follow-up | Claude Code | golden-sample round-trip |
| `backend/app/api/viz.py` | Phase 2.2 follow-up | Claude Code | `GET /runs/{id}/viz/{filename}` |
| `frontend/src/viz/*` | Phase 2.2 follow-up | Claude Code | vtk.js viewer SPA |

---

## Codex review expectation

This PR triggers M1 (governance text) and M2 (executable schema + assertions). It does **not** touch HF1 zones. It is **not** an enforcement-coupling PR (the writer reads `FRDParseResult` and writes artifacts; no governance-state mutation).

Self-pass-rate: **30%** — match the BLOCKING ceiling. The schema is the contract every viewer-track PR will be measured against.

---

## Cross-references

- ADR-011 §T2 — M1+M2 trigger compliance basis
- ADR-011 §HF1 — explicit non-touch (only adds new files outside HF1.x)
- ADR-012 R2 (PR #24) — 30% BLOCKING ceiling honored
- ADR-014 (Draft, parallel) — the WS bus emits `artifact.ready` events when `mesh.vtu` / `field_*.vtu` finish writing; the viewer subscribes
- ADR-015 (Draft, parallel) — `run_orchestrator` invokes the writer after CalculiX finishes; passes SimPlan units in
- ADR-017 (Draft, parallel) — independent surface (RAG facade), no overlap

---

## Status notes

**Draft → Final criteria:**

1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
2. The manifest-shape test passes on `main`
3. Phase 2.2 follow-up PR implements `frd_to_vtu` writer + golden-sample round-trip test

Until all three are met, this ADR remains `Draft`.
