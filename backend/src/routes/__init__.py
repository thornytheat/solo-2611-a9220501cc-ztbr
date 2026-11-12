"""路由总装配。"""
from fastapi import APIRouter

from src.routes import audit, auth, burst, collect, export, group, health, mention, meta, sentiment

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(group.router)
api_router.include_router(mention.router)
api_router.include_router(collect.router)
api_router.include_router(sentiment.router)
api_router.include_router(burst.router)
api_router.include_router(export.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
