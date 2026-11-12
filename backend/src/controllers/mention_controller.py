"""提及控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.middlewares.auth import brand_scope
from src.models.user import User
from src.schemas.mention import MentionReviewRequest
from src.services import mention_service


def list_mentions(db: Session, user: User, **filters) -> dict:
    return mention_service.list_mentions(db, brand_scope=brand_scope(user), **filters)


def detail(db: Session, mention_id: str, user: User) -> dict:
    return mention_service.get_mention(db, mention_id, brand_scope(user))


def review(db: Session, mention_id: str, payload: MentionReviewRequest, user: User, trace_id: str = "") -> dict:
    return mention_service.review(
        db, mention_id, payload.final_label, payload.note, user, brand_scope(user), trace_id
    )


def review_queue(db: Session, user: User, limit: int = 20) -> dict:
    return mention_service.review_queue(db, brand_scope(user), limit)
