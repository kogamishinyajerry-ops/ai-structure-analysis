"""Layer 4 — report generation services (RFC-001 §6.1 Bucket D).

Template engine + draft generator + DOCX exporter for the MVP
static-strength report Copilot. Consumes Layer-3 domain outputs and
writes a DOCX that an engineer can sign within 30 minutes of opening
the app (RFC §3 success criterion).

ADR-012: every claim in the rendered draft must be backed by an
``EvidenceItem.evidence_id``; the exporter MUST refuse to emit
DOCX for a draft whose evidence-bundle has unresolved IDs.
"""
