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

# Registry of (source_label, iter_fn) pairs. The CLI runner walks this list
# to ingest every available source. Add new sources here as they land.
ALL_SOURCES = [
    (PROJECT_GOVERNANCE_SOURCE, iter_governance_documents),
    (GS_THEORY_SOURCE, iter_gs_theory_documents),
]

__all__ = [
    "iter_gs_theory_documents",
    "GS_THEORY_SOURCE",
    "iter_governance_documents",
    "PROJECT_GOVERNANCE_SOURCE",
    "ALL_SOURCES",
]
