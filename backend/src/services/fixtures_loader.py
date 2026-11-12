"""把确定性语料包装成服务层可用的形状（不碰数据库）。"""
from __future__ import annotations

from functools import lru_cache

from scripts import fixtures


@lru_cache(maxsize=1)
def inbox_corpus() -> tuple[dict, ...]:
    """采集窗口原始候选（92 条）。"""
    return tuple(fixtures.inbox_items())


def group_specs() -> list[dict]:
    return fixtures.GROUP_SPECS


def seed_mentions() -> list[dict]:
    return fixtures.seed_mentions()
