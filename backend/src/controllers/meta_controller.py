"""元信息控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.middlewares.auth import brand_scope
from src.models.user import User
from src.services import meta_service


def bootstrap(db: Session, user: User) -> dict:
    return meta_service.bootstrap(db, brand_scope(user))


def dictionary() -> dict:
    return meta_service.sentiment_dictionary()
