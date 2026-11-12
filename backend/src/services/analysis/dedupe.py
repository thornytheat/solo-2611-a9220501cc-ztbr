"""去重指纹：内容归一化 + SHA-256；并给出「同源同 id」「同内容」两级判定。"""
from __future__ import annotations

import hashlib
from datetime import datetime

from src.utils.textutils import normalize


def content_hash(title: str, body: str) -> str:
    payload = normalize(title) + "\u0001" + normalize(body)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def external_id(source_code: str, native_id: str) -> str:
    return f"{source_code}:{native_id}"


def dedupe_key(source_code: str, native_id: str, title: str, body: str) -> tuple[str, str]:
    return external_id(source_code, native_id), content_hash(title, body)


def hash_key(digest: str, source_code: str, published_at: datetime) -> tuple[str, str, datetime]:
    """同内容去重键：内容哈希 + 来源 + 发布小时（跨来源的模板化转载不算重复）。"""
    return (digest, source_code, published_at.replace(minute=0, second=0, microsecond=0))


def is_duplicate(
    existing_ids: set[str],
    existing_hashes: set[tuple[str, str, datetime]],
    ext_id: str,
    key: tuple[str, str, datetime],
) -> str | None:
    if ext_id in existing_ids:
        return "external_id"
    if key in existing_hashes:
        return "content_hash"
    return None


def partition(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """批次内去重：同一批里重复的条目归入 duplicates（保留第一条）。"""
    seen_ids: set[str] = set()
    seen_hash: set[str] = set()
    fresh: list[dict] = []
    dup: list[dict] = []
    for item in items:
        ext_id = item["external_id"]
        digest = item["content_hash"]
        if ext_id in seen_ids or digest in seen_hash:
            dup.append(item)
            continue
        seen_ids.add(ext_id)
        seen_hash.add(digest)
        fresh.append(item)
    return fresh, dup


def hour_of(value: datetime) -> datetime:
    return value.replace(minute=0, second=0, microsecond=0)
