"""提及请求模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.constants.enums import SentimentLabel


class MentionReviewRequest(BaseModel):
    final_label: str
    note: str = Field(default="", max_length=400)

    @field_validator("final_label")
    @classmethod
    def check_label(cls, value: str) -> str:
        valid = {item.value for item in SentimentLabel}
        if value not in valid:
            raise ValueError(f"情感标签不合法，可选 {sorted(valid)}")
        return value
