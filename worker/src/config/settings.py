"""worker 配置：复用 backend 的 settings（同一批环境变量）。"""
from __future__ import annotations

from src.config.settings import settings  # noqa: F401  (PYTHONPATH 里 /app/backend 在前)

BRAND = settings.brand
HEARTBEAT_KEY = f"{settings.brand}:worker:heartbeat"
HEARTBEAT_TTL_SECONDS = 90
