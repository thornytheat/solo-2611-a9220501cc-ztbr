"""worker 心跳：写 Redis 时间戳，供容器 healthcheck 判定。"""
from __future__ import annotations

import time

import redis

from src.config.settings import settings

HEARTBEAT_KEY = f"{settings.brand}:worker:heartbeat"


def beat() -> float:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    now = time.time()
    client.set(HEARTBEAT_KEY, f"{now:.3f}", ex=300)
    return now


def last_beat() -> float | None:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    value = client.get(HEARTBEAT_KEY)
    return float(value) if value else None
