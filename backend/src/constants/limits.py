"""限流桶与分页上限（值可被环境变量覆盖）。"""
from __future__ import annotations

from src.config.settings import settings

RATE_LIMIT_COLLECT_PER_MINUTE = settings.rate_limit_collect_per_minute
RATE_LIMIT_DETECT_PER_MINUTE = settings.rate_limit_detect_per_minute
RATE_LIMIT_DEFAULT_PER_MINUTE = settings.rate_limit_default_per_minute

MENTION_PAGE_MAX = 100
MENTION_PAGE_DEFAULT = 30
BURST_PAGE_MAX = 100
EXPORT_TOP_NEGATIVE = 5
TRIAL_PREVIEW_LIMIT = 8
