"""补采批次请求模型。"""
from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_validator, model_validator

from src.constants.brands import BRAND_KEYS
from src.constants.sources import SOURCE_CODES

# 单次补采最长回溯 30 天，与提及流 days 筛选上限对齐
MAX_WINDOW_DAYS = 30


class CollectBatchCreateRequest(BaseModel):
    brand_key: str
    source_codes: list[str] = Field(min_length=1, max_length=4)
    window_start: datetime
    window_end: datetime

    @field_validator("brand_key")
    @classmethod
    def check_brand(cls, value: str) -> str:
        if value not in BRAND_KEYS:
            raise ValueError(f"品牌不合法，可选 {list(BRAND_KEYS)}")
        return value

    @field_validator("source_codes")
    @classmethod
    def check_sources(cls, value: list[str]) -> list[str]:
        invalid = [code for code in value if code not in SOURCE_CODES]
        if invalid:
            raise ValueError(f"来源不合法：{invalid}，可选 {list(SOURCE_CODES)}")
        # 去重并按来源目录顺序排列，保证批次内来源顺序稳定
        unique = list(dict.fromkeys(value))
        return sorted(unique, key=SOURCE_CODES.index)

    @model_validator(mode="after")
    def check_window(self) -> "CollectBatchCreateRequest":
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("时间窗口必须带时区")
        if self.window_end <= self.window_start:
            raise ValueError("结束时间必须晚于开始时间")
        if self.window_end - self.window_start > timedelta(days=MAX_WINDOW_DAYS):
            raise ValueError(f"单次补采时间跨度不能超过 {MAX_WINDOW_DAYS} 天")
        return self
