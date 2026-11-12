"""关键词组请求模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from src.constants.brands import BRAND_KEYS


def _clean_words(value: list[str]) -> list[str]:
    seen: list[str] = []
    for word in value:
        clean = word.strip()
        if clean and clean not in seen:
            seen.append(clean)
    return seen


class GroupCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=2, max_length=120)
    brand_key: str
    keywords: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)
    enabled: bool = True
    priority: int = Field(default=5, ge=0, le=10)
    z_threshold: float = Field(default=3.0, ge=1.0, le=8.0)
    min_count: int = Field(default=5, ge=1, le=50)
    owner_note: str = Field(default="", max_length=400)

    @field_validator("brand_key")
    @classmethod
    def check_brand(cls, value: str) -> str:
        if value not in BRAND_KEYS:
            raise ValueError(f"品牌不合法，可选 {list(BRAND_KEYS)}")
        return value

    @field_validator("keywords", "synonyms", "excludes")
    @classmethod
    def clean_words(cls, value: list[str]) -> list[str]:
        return _clean_words(value)


class GroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    keywords: list[str] | None = None
    synonyms: list[str] | None = None
    excludes: list[str] | None = None
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10)
    z_threshold: float | None = Field(default=None, ge=1.0, le=8.0)
    min_count: int | None = Field(default=None, ge=1, le=50)
    owner_note: str | None = Field(default=None, max_length=400)

    @field_validator("keywords", "synonyms", "excludes")
    @classmethod
    def clean_words(cls, value: list[str] | None) -> list[str] | None:
        return _clean_words(value) if value is not None else None


class GroupTrialRequest(BaseModel):
    code: str = Field(default="draft", max_length=64)
    keywords: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)
    source_code: str | None = None

    @field_validator("keywords", "synonyms", "excludes")
    @classmethod
    def clean_words(cls, value: list[str]) -> list[str]:
        return _clean_words(value)
