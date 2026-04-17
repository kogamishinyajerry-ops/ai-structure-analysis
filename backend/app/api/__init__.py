"""API路由模块"""
from .result import router as result_router
from .nl import router as nl_router

__all__ = ["result_router", "nl_router"]
