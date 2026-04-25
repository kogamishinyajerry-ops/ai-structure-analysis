"""Per-source ingestion modules for the RAG knowledge base (P1-04b).

See README.md in this directory for the full corpus catalogue.
"""

from backend.app.rag.sources.gs_theory import (
    SOURCE_LABEL as GS_THEORY_SOURCE,
    iter_gs_theory_documents,
)
from backend.app.rag.sources.project_governance import (
    SOURCE_LABEL as PROJECT_GOVERNANCE_SOURCE,
    iter_governance_documents,
)

__all__ = [
    "GS_THEORY_SOURCE",
    "PROJECT_GOVERNANCE_SOURCE",
    "iter_governance_documents",
    "iter_gs_theory_documents",
]
