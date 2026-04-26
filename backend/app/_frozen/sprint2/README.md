# Sprint 2 frozen services — RFC-001 §6.1 Bucket B

This directory holds Sprint 2 work that **is not part of the MVP wedge**
defined in `docs/RFC-001-strategic-pivot-and-mvp.md` §3 (chemical / power
design-institute static-strength report Copilot).

The code is **frozen, not deleted**: live consumers may continue to import
it (with `app._frozen.sprint2.X` paths) until each file's expiration date
fires. New features must NOT be added here. Only mechanical edits
(import-path adjustments, syntax-only fixes to keep the freeze compiling)
are allowed.

## Files

### `knowledge_base.py`
- **Source path before freeze:** `backend/app/services/knowledge_base.py`
- **Why frozen:** ChromaDB-backed FEA knowledge retrieval was Sprint 1/2
  scope. The MVP report Copilot does *not* require RAG-style knowledge
  injection in W1-W6; standards / handbook citation will be wired in via
  the new `services/report/` package once Layer-3 lands.
- **Live consumers (post-freeze):**
  - `services/report_generator.py` (lazy/guarded import — see import patch)
  - `tests/test_compliance.py::test_knowledge_base_linkage` — marked
    `@pytest.mark.legacy`
- **Expiration:**
  - **Re-enable trigger:** M5 (post-MVP), if standards-citation use case
    upgrades from "deterministic lookup" to "semantic retrieval".
  - **Delete trigger:** M6, if M5 rebuild starts from a clean facade
    (RFC-001 ADR-002 closed-set discipline applies — no re-importing the
    open-vocabulary embedding store).

### `visualization.py`
- **Source path before freeze:** `backend/app/services/visualization.py`
- **Why frozen:** PyVista-based 3D HTML scene exports, deformation
  animation, and delta visualization are out of MVP scope. Per RFC-001
  §6.1 the **PNG-output minimum** has been re-exposed via
  `services/plots/` for the static-strength report use case.
- **Live consumers (post-freeze):**
  - `services/plots/__init__.py` (thin shim — MVP-relevant PNG only)
  - `api/routes/visualization.py` (HTML-scene endpoints — slated for
    rebuild on Layer-2 ReaderHandle in W2-W3)
- **Expiration:**
  - **Re-enable trigger:** M4 — only if the MVP report Copilot needs
    embedded interactive 3D scenes (currently NOT planned).
  - **Delete trigger:** M6 if HTML-scene endpoints are rebuilt on the
    Layer-2 adapter contract instead of revived from this code.

### `route_knowledge.py`
- **Source path before freeze:** `backend/app/api/routes/knowledge.py`
- **Why frozen:** the `/api/v1/knowledge/*` endpoints (vector query, RAG
  Q&A, document upsert, clear-all) require the frozen
  `services/knowledge_base.py`. They are **not registered** on the live
  FastAPI app anymore — the route is dropped from `app/main.py` and
  `app/api/routes/__init__.py`.
- **Live consumers (post-freeze):** none.
- **Expiration:**
  - **Re-enable trigger:** never — the MVP report Copilot does not expose
    a knowledge-base HTTP surface. If post-MVP RAG is rebuilt, the new
    endpoints must live under a fresh module name and be reviewed
    against RFC-001 ADR-002 closed-set discipline.
  - **Delete trigger:** M6.
