"""Per-source ingestion modules for the RAG knowledge base (P1-04b).

See README.md in this directory for the full corpus catalogue.
"""

from backend.app.rag.sources.gs_theory import (
    iter_gs_theory_documents,
    SOURCE_LABEL as GS_THEORY_SOURCE,
)

__all__ = ["iter_gs_theory_documents", "GS_THEORY_SOURCE"]
