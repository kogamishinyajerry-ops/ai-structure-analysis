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

# Registry consumed by `backend.app.rag.cli`. Each entry is
# (source_label, iter_fn(repo_root) -> Iterator[Document]).
ALL_SOURCES: list = [
    (PROJECT_GOVERNANCE_SOURCE, iter_governance_documents),
    (GS_THEORY_SOURCE, iter_gs_theory_documents),
]

__all__ = [
    "ALL_SOURCES",
    "GS_THEORY_SOURCE",
    "PROJECT_GOVERNANCE_SOURCE",
    "iter_governance_documents",
    "iter_gs_theory_documents",
]
