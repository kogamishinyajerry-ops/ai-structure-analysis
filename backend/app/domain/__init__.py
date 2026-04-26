"""Layer 3 — domain logic (RFC-001 §4.2).

Consumes ``ReaderHandle`` (Layer 2) and produces engineering quantities
that Layer 4 (services/report/) renders. Derived-quantity computation
lives here, NOT in Layer-1 adapters (ADR-001).
"""
