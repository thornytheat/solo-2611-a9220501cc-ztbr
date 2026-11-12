"""定时采集：复用 backend 的 collect_service（同一套去重与打分）。"""
from __future__ import annotations

import logging

from sqlalchemy import select

from worker_src.config.celery_app import celery_app
from src.config.database import session_scope
from src.models.user import User
from src.services import collect_service

logger = logging.getLogger("newssweep.worker.collect")


@celery_app.task(name="newssweep.collect_sweep", bind=True, max_retries=2)
def collect_sweep(self) -> dict:
    try:
        with session_scope() as db:
            actor = db.execute(select(User).where(User.role == "admin")).scalars().first()
            if actor is None:
                return {"status": "skipped", "reason": "no admin user"}
            report = collect_service.run_collection(db, actor, trace_id=f"celery-{self.request.id}")
        logger.info("collect sweep done: %s", report)
        return {"status": "ok", "report": report}
    except Exception as exc:  # noqa: BLE001
        logger.warning("collect sweep failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)
