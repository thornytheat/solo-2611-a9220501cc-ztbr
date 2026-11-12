"""补采批次规划（纯函数、不碰数据库）：候选切片、口径计数、对账。

口径封闭原则：
- 批次候选 = 语料中命中 (品牌, 来源集合, 发布时间段) 的条目；
- 归属停用关键词组的候选计入 skipped（不入库但仍是批次台账的一部分）；
- 台账总数 = inserted + duplicate + failed + skipped + pending，任何时刻成立；
- 全部候选终态后 pending=0，页面四个数字与 collect_batch_items 行数逐一对得上。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.models.collect_batch import (
    ITEM_PENDING,
    SOURCE_PENDING,
)


def select_candidates(
    corpus: list[dict] | tuple[dict, ...],
    *,
    brand_key: str,
    source_codes: tuple[str, ...],
    window_start: datetime,
    window_end: datetime,
    enabled_group_codes: frozenset[str],
) -> list[dict]:
    """按品牌/来源/时间窗口切片，并标注该候选所属关键词组是否停用。"""
    source_set = set(source_codes)
    selected: list[dict] = []
    for item in corpus:
        if item["brand_key"] != brand_key:
            continue
        if item["source_code"] not in source_set:
            continue
        published = item["published_at"]
        if not (window_start <= published < window_end):
            continue
        enriched = dict(item)
        enriched["group_enabled"] = item["group_code"] in enabled_group_codes
        selected.append(enriched)
    # 稳定顺序：来源 → 发布时间 → external_id，保证断点 cursor 可复现
    selected.sort(key=lambda x: (x["source_code"], x["published_at"], x["external_id"]))
    return selected


def split_by_source(candidates: list[dict], source_order: tuple[str, ...]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {code: [] for code in source_order}
    for item in candidates:
        buckets.setdefault(item["source_code"], []).append(item)
    return buckets


def build_source_plan(
    candidates: list[dict], source_codes: tuple[str, ...]
) -> list[dict[str, Any]]:
    """创建批次时的来源 checkpoint 初始口径（全部 pending）。"""
    buckets = split_by_source(candidates, source_codes)
    plan = []
    for position, code in enumerate(source_codes):
        items = buckets.get(code, [])
        plan.append(
            {
                "source_code": code,
                "position": position,
                "status": SOURCE_PENDING,
                "candidates": len(items),
                "cursor": 0,
            }
        )
    return plan


def build_item_ledger(candidates: list[dict]) -> list[dict[str, Any]]:
    """创建批次时写入的逐候选台账行（全部 pending）。"""
    ledger = []
    for position, item in enumerate(candidates):
        ledger.append(
            {
                "source_code": item["source_code"],
                "position": position,
                "external_id": item["external_id"],
                "group_code": item["group_code"],
                "title": item["title"],
                "published_at": item["published_at"],
                "status": ITEM_PENDING,
                "group_enabled": item["group_enabled"],
            }
        )
    return ledger


def reconcile_totals(rows: list[dict]) -> dict[str, int]:
    """从台账行聚合四种终态计数（页面数字的唯一事实源）。"""
    totals = {"inserted": 0, "duplicate": 0, "failed": 0, "skipped": 0, "pending": 0}
    for row in rows:
        status = row["status"]
        if status in totals:
            totals[status] += 1
    return totals


def ledger_is_closed(rows: list[dict]) -> bool:
    """台账封闭：没有待处理条目，且计数之和等于总行数。"""
    totals = reconcile_totals(rows)
    return totals["pending"] == 0 and sum(totals.values()) == len(rows)
