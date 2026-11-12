"""Celery 入口（backend 只投递任务，消费在 worker 容器）。"""
from __future__ import annotations

from celery import Celery

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
)

# 任务名：backend 投递、worker 实现（跨容器共享同一字符串）
TASK_COLLECT_SWEEP = "newssweep.collect_sweep"
TASK_SENTIMENT_RESCORE = "newssweep.sentiment_rescore"
TASK_BURST_DETECT = "newssweep.burst_detect"
