"""文本归一化：全角转半角、空白压缩、关键词匹配用的小写化。

情感打分与召回试算都依赖这里的同一套归一化，保证「同输入同分」。
"""
from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def normalize(raw: str) -> str:
    """全角→半角（NFKC）、去零宽、压缩连续空白，保留原标点。"""
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", raw)
    text = text.replace("\u200b", "").replace("\ufeff", "")
    return _WS.sub(" ", text).strip()


def fold(raw: str) -> str:
    """匹配用的折叠：归一化 + 小写。位置索引与 normalize 后一致。"""
    return normalize(raw).lower()


def compact(raw: str) -> str:
    """去全部空白，用于跨空格关键词匹配（如「澄 野 咖啡」）。"""
    return re.sub(r"\s+", "", fold(raw))


def snippet(text: str, limit: int = 120) -> str:
    clean = normalize(text)
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"
