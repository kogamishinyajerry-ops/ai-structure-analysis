"""Per-source ingestion modules for the RAG knowledge base (P1-04b).

See README.md in this directory for the full corpus catalogue.
"""

from backend.app.rag.sources.project_governance import (
    iter_governance_documents,
    SOURCE_LABEL as PROJECT_GOVERNANCE_SOURCE,
)

__all__ = [
    "iter_governance_documents",
    "PROJECT_GOVERNANCE_SOURCE",
]
