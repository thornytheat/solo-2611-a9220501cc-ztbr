"""整点爆发检测：写入/更新 BurstAlert（按 group_id + window_start 幂等）。"""
from __future__ import annotations

import logging

from sqlalchemy import select

from worker_src.config.celery_app import celery_app
from src.config.database import session_scope
from src.models.user import User
from src.services import burst_service

logger = logging.getLogger("newssweep.worker.burst")


@celery_app.task(name="newssweep.burst_detect")
def burst_detect() -> dict:
    with session_scope() as db:
        actor = db.execute(select(User).where(User.role == "admin")).scalars().first()
        if actor is None:
            return {"status": "skipped", "reason": "no admin user"}
        report = burst_service.run_detection(db, actor, None, trace_id="celery-burst")
    logger.info("burst detect done: events=%s", len(report["events"]))
    return {"status": "ok", "events": len(report["events"]), "eval_day": report["eval_day"]}
