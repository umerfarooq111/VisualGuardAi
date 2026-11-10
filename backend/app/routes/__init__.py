"""
API routes package for VisualGuard AI.
"""

from app.routes.processing import router as processing_router
from app.routes.system import router as system_router
from app.routes.videos import router as videos_router

__all__ = ["system_router", "videos_router", "processing_router"]
