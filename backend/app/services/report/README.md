# services/report/ — placeholder

**Lands:** Weeks 4-6 (RFC-001 §6.4).

**Modules planned:**
  * `templates.py`     — load + validate the 3 MVP `.docx` templates
                         (equipment foundation static / lifting lug /
                         pressure-vessel local stress).
  * `draft.py`         — fill `ReportSpec.sections` from Layer-3 data
                         + `EvidenceBundle`; stream tokens for the
                         WebSocket draft endpoint (§6.3).
  * `exporter.py`      — `python-docx` wrapper that materialises a
                         signed-ready DOCX from a finalised draft.

**ADR-012 enforcement:** `exporter.py` MUST verify every inline claim
ID resolves into the linked `EvidenceBundle`. Unresolved IDs are a
hard refusal, not a warning.

**Trap reminders:** the templates' content is non-trivial copy
(ASME / GB-50017 boilerplate); the W1-4 parallel non-technical track
(§6.6) drafts these in `.docx` form before the Python wiring lands.
