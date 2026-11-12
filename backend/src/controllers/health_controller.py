"""健康检查：db / redis 探活（compose healthcheck 与前端顶栏共用）。"""
from __future__ import annotations

from src.config.database import ping_db
from src.config.settings import settings
from src.utils.redis_client import ping_redis


def health() -> dict:
    database_ok = ping_db()
    redis_ok = ping_redis()
    return {
        "status": "ok" if database_ok and redis_ok else "degraded",
        "brand": settings.brand,
        "database": database_ok,
        "redis": redis_ok,
        "version": "1.0.0",
    }
