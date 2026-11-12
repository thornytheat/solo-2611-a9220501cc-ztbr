"""定时情感重算（复核结果不会被覆盖）。"""
from __future__ import annotations

import logging

from sqlalchemy import select

from worker_src.config.celery_app import celery_app
from src.config.database import session_scope
from src.models.user import User
from src.services import sentiment_service

logger = logging.getLogger("newssweep.worker.sentiment")


@celery_app.task(name="newssweep.sentiment_rescore")
def sentiment_rescore() -> dict:
    with session_scope() as db:
        actor = db.execute(select(User).where(User.role == "admin")).scalars().first()
        if actor is None:
            return {"status": "skipped", "reason": "no admin user"}
        report = sentiment_service.rescore_all(db, actor, None, trace_id="celery-rescore")
    logger.info("rescore done: %s", report)
    return {"status": "ok", "report": report}
