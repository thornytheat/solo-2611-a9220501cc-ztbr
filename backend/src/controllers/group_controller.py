"""关键词组控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.middlewares.auth import brand_scope
from src.models.user import User
from src.schemas.group import GroupCreateRequest, GroupTrialRequest, GroupUpdateRequest
from src.services import group_service


def list_groups(db: Session, user: User) -> dict:
    return group_service.list_groups(db, brand_scope(user))


def create(db: Session, payload: GroupCreateRequest, user: User, trace_id: str = "") -> dict:
    return group_service.create_group(db, payload, user, trace_id)


def update(db: Session, group_id: str, payload: GroupUpdateRequest, user: User, trace_id: str = "") -> dict:
    return group_service.update_group(db, group_id, payload, user, trace_id)


def trial(db: Session, payload: GroupTrialRequest, user: User, trace_id: str = "") -> dict:
    return group_service.trial_recall(db, payload, user, brand_scope(user), trace_id)
