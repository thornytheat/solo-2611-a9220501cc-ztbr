"""认证：Bearer → request.state.user（挂 FastAPI 依赖）。"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants import error_codes as codes
from src.constants.enums import UserRole
from src.models.user import User
from src.utils.errors import AppError
from src.utils.jwt import decode_token


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_bearer(request)
    if not token:
        raise AppError(codes.AUTH_REQUIRED, "请先登录", "missing Authorization header")
    payload = decode_token(token)
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise AppError(codes.AUTH_INVALID, "登录状态无效，请重新登录", "user missing/inactive")
    request.state.user = user
    request.state.brand_key = user.brand_key
    return user


def brand_scope(user: User) -> str | None:
    """client 账号只能看自己品牌；员工看全量（返回 None）。"""
    if user.role == UserRole.CLIENT.value:
        return user.brand_key or "__none__"
    return None


def ensure_brand_access(user: User, brand_key: str | None) -> None:
    scope = brand_scope(user)
    if scope and brand_key and brand_key != scope:
        raise AppError(
            codes.BRAND_SCOPE_DENIED,
            "该数据不属于你负责的品牌",
            f"scope={scope} target={brand_key}",
        )


def serialize_actor(user: User) -> dict[str, Any]:
    from src.services.auth_service import serialize

    return serialize(user)
