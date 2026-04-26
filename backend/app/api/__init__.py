"""API routes module.

RFC-001 §6.1 Bucket C: result_router removed along with parsers/result_parser.py.
Replacement endpoint POST /api/v1/projects/{id}/results lands in W4+ per RFC §6.3.
"""
from .nl import router as nl_router

__all__ = ["nl_router"]
