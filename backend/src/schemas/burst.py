"""爆发事件请求模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.constants.enums import BurstStatus


class BurstDisposeRequest(BaseModel):
    status: str = Field(default=BurstStatus.HANDLED.value)
    note: str = Field(default="", max_length=400)

    @field_validator("status")
    @classmethod
    def check_status(cls, value: str) -> str:
        if value not in (BurstStatus.HANDLED.value, BurstStatus.DISMISSED.value):
            raise ValueError("处置状态只能是 handled 或 dismissed")
        return value
