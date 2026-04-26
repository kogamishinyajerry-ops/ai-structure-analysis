"""Layer 1 — concrete solver adapters (RFC-001 §4.2).

Each subpackage ships a single concrete class implementing the
``app.core.types.ReaderHandle`` Protocol over one solver's native
result format. ADR-001/003/004 forbid derived-quantity computation,
heuristic completion, and hidden caching at this layer.
"""
