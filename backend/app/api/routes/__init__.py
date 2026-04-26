"""API路由模块.

RFC-001 §6.1 Bucket B: ``knowledge`` route frozen under
``app._frozen.sprint2.route_knowledge`` — unregistered from the live app.
"""
from . import visualization, frd

__all__ = ["visualization", "frd"]
