"""4 个采集来源的静态目录（来源不是实体，是共享枚举 + 目录元数据）。"""
from __future__ import annotations

from src.constants.enums import SourceCode

SOURCE_CATALOG: list[dict] = [
    {
        "code": SourceCode.NEWS_WIRE.value,
        "name": "新闻站 · 都市财经频道",
        "channel": "news",
        "base_url": "https://news.fixture.local/search",
        "latency_hint": "索引延迟 8-15 分钟",
        "auth": "公开检索，无登录",
        "daily_quota": 1200,
    },
    {
        "code": SourceCode.MICROBLOG.value,
        "name": "微博式社区 · 热搜与话题",
        "channel": "microblog",
        "base_url": "https://weibo.fixture.local/topic",
        "latency_hint": "实时，限流 30 req/min",
        "auth": "应用 token（演示用固定值）",
        "daily_quota": 4000,
    },
    {
        "code": SourceCode.VERTICAL_FORUM.value,
        "name": "垂直论坛 · 品牌讨论区",
        "channel": "forum",
        "base_url": "https://forum.fixture.local/board",
        "latency_hint": "抓取延迟 1-2 小时",
        "auth": "公开板块",
        "daily_quota": 900,
    },
    {
        "code": SourceCode.VIDEO_AGG.value,
        "name": "短视频标题聚合 · 榜单",
        "channel": "video",
        "base_url": "https://video.fixture.local/hot",
        "latency_hint": "榜单每 30 分钟刷新",
        "auth": "榜单页公开",
        "daily_quota": 700,
    },
]

SOURCE_CODES: tuple[str, ...] = tuple(item["code"] for item in SOURCE_CATALOG)


def source_meta(code: str) -> dict | None:
    for item in SOURCE_CATALOG:
        if item["code"] == code:
            return item
    return None
