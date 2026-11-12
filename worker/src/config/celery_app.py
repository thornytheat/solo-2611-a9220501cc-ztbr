"""Celery 应用：任务名与 backend/src/config/celery_app.py 中的常量逐字一致。"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

celery_app = Celery("newssweep", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=1800,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "worker-heartbeat-every-30s": {
            "task": "newssweep.worker_heartbeat",
            "schedule": 30.0,
        },
        "nightly-collect-sweep": {
            "task": "newssweep.collect_sweep",
            "schedule": crontab(hour=2, minute=10),
        },
        "hourly-burst-detect": {
            "task": "newssweep.burst_detect",
            "schedule": crontab(minute=5),
        },
    },
)
celery_app.autodiscover_tasks(["worker_src.tasks"], force=True)
# 显式导入，确保 `celery -A ... worker` 能注册任务
from worker_src.tasks import burst_task, collect_task, heartbeat_task, sentiment_task  # noqa: E402,F401
