"""时间工具：库里统一存 aware UTC，业务展示按 Asia/Shanghai。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TZ_SHANGHAI = timezone(timedelta(hours=8))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_local(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(TZ_SHANGHAI)


def iso(value: datetime | None) -> str | None:
    """给前端的 ISO 串：统一上海时区，前端直接 new Date() 展示。"""
    if value is None:
        return None
    return to_local(value).isoformat()  # type: ignore[union-attr]


def hour_key(value: datetime) -> str:
    local = to_local(value)
    return local.strftime("%Y-%m-%dT%H")  # type: ignore[union-attr]


def day_key(value: datetime) -> str:
    local = to_local(value)
    return local.strftime("%Y-%m-%d")  # type: ignore[union-attr]


def parse_seed_now(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=TZ_SHANGHAI)
    return parsed
