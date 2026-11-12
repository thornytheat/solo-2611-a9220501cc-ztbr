"""通用响应模型。"""
from __future__ import annotations

from pydantic import BaseModel


class ErrorPayload(BaseModel):
    code: str
    message: str
    detail: str = ""
    trace_id: str | None = None


class HealthPayload(BaseModel):
    status: str
    brand: str
    database: bool
    redis: bool
    version: str = "1.0.0"
