"""心跳任务（beat 每 30s）。"""
from __future__ import annotations

from worker_src.config.celery_app import celery_app
from worker_src.core.heartbeat import beat


@celery_app.task(name="newssweep.worker_heartbeat")
def worker_heartbeat() -> dict:
    timestamp = beat()
    return {"brand": "newssweep", "beat_at": timestamp}
