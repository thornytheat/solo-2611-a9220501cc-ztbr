"""情感控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.middlewares.auth import brand_scope
from src.models.user import User
from src.services import sentiment_service


def rescore(db: Session, user: User, trace_id: str = "") -> dict:
    return sentiment_service.rescore_all(db, user, brand_scope(user), trace_id)


def summary(db: Session, user: User) -> dict:
    scope = brand_scope(user)
    payload = sentiment_service.summary(db, scope)
    payload["evidence_words"] = sentiment_service.top_evidence_words(db, scope, limit=12)
    return payload
