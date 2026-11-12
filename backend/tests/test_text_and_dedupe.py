"""解析 / 归一工具：文本归一化、时间戳族、去重指纹（算法前的确定性预处理）。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.services.analysis.dedupe import (
    content_hash,
    dedupe_key,
    external_id,
    hash_key,
    is_duplicate,
    partition,
)
from src.utils.textutils import compact, fold, normalize, snippet
from src.utils.timeutil import TZ_SHANGHAI, day_key, hour_key, iso, parse_seed_now, to_local

# --------------------------------------------------------------- 文本归一 ----


def test_normalize_fullwidth_to_halfwidth() -> None:
    """NFKC：全角字母/数字/表意空格 → 半角，连续空白压成一个。"""
    assert normalize("ＡＢＣ　１２３") == "ABC 123"


def test_normalize_strips_zero_width_and_collapses_whitespace() -> None:
    assert normalize("  a\u200b  b\t\n c  ") == "a b c"
    assert normalize("\ufeff标题") == "标题"


def test_normalize_empty_and_none_degrade_to_empty_string() -> None:
    assert normalize("") == ""
    assert normalize(None) == ""  # type: ignore[arg-type]


def test_fold_lowercases_after_normalize() -> None:
    assert fold("Hello　WORLD") == "hello world"
    assert fold("iPhone 15") == "iphone 15"


def test_compact_removes_all_whitespace() -> None:
    assert compact(" 澄 野 咖啡 ") == "澄野咖啡"
    assert compact("ＡＢ　Ｃ") == "abc"


def test_snippet_truncates_to_limit_with_ellipsis() -> None:
    text = "字" * 200

    cut = snippet(text, limit=120)

    assert len(cut) == 120
    assert cut == "字" * 119 + "…"
    assert snippet("很短", limit=120) == "很短"


# --------------------------------------------------------------- 时间戳族 ----


def test_to_local_converts_utc_to_shanghai() -> None:
    utc = datetime(2026, 11, 12, 10, 30, tzinfo=timezone.utc)
    local = to_local(utc)

    assert local == datetime(2026, 11, 12, 18, 30, tzinfo=TZ_SHANGHAI)
    assert local.utcoffset().total_seconds() == 8 * 3600
    assert iso(utc) == "2026-11-12T18:30:00+08:00"
    assert hour_key(utc) == "2026-11-12T18"
    assert day_key(utc) == "2026-11-12"


def test_naive_datetime_is_treated_as_utc() -> None:
    naive = datetime(2026, 11, 12, 10, 30)

    assert to_local(naive) == datetime(2026, 11, 12, 18, 30, tzinfo=TZ_SHANGHAI)
    assert iso(naive) == "2026-11-12T18:30:00+08:00"


def test_local_day_rolls_over_at_shanghai_midnight() -> None:
    """UTC 16:30 = 上海次日 00:30 → day_key 必须按上海日期切。"""
    utc = datetime(2026, 11, 12, 16, 30, tzinfo=timezone.utc)

    assert day_key(utc) == "2026-11-13"
    assert hour_key(utc) == "2026-11-13T00"


def test_none_passthrough_for_time_helpers() -> None:
    assert to_local(None) is None
    assert iso(None) is None


def test_parse_seed_now_marks_naive_as_shanghai() -> None:
    parsed = parse_seed_now("2026-11-12T18:00:00")

    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 8 * 3600
    assert parsed == datetime(2026, 11, 12, 18, 0, tzinfo=TZ_SHANGHAI)


def test_parse_seed_now_keeps_explicit_offset() -> None:
    as_utc = parse_seed_now("2026-11-12T10:00:00+00:00")

    assert as_utc == datetime(2026, 11, 12, 18, 0, tzinfo=TZ_SHANGHAI)


# --------------------------------------------------------------- 去重指纹 ----


def test_content_hash_is_deterministic_and_normalized() -> None:
    first = content_hash("  标题  ", "正文\t内容")
    second = content_hash("标题", "正文 内容")
    other = content_hash("标题", "正文内容")

    assert first == second
    assert first != other
    assert len(first) == 64
    assert all(char in "0123456789abcdef" for char in first)


def test_external_id_and_dedupe_key_shape() -> None:
    assert external_id("news_wire", "N-001") == "news_wire:N-001"

    key = dedupe_key("news_wire", "N-001", "标题", "正文")

    assert key == ("news_wire:N-001", content_hash("标题", "正文"))


def test_hash_key_truncates_to_publish_hour() -> None:
    key = hash_key("abc123", "microblog", datetime(2026, 11, 12, 14, 59, 59, 999999))

    assert key == ("abc123", "microblog", datetime(2026, 11, 12, 14, 0, 0))
    assert hash_key("abc123", "microblog", datetime(2026, 11, 12, 14, 0, 0)) == key


def test_is_duplicate_priority_external_id_then_content_hash() -> None:
    key = ("digest", "news_wire", datetime(2026, 11, 12, 14, 0))

    assert is_duplicate({"a:1"}, {key}, "a:1", key) == "external_id"
    assert is_duplicate(set(), {key}, "a:2", key) == "content_hash"
    assert is_duplicate({"a:1"}, {key}, "a:2", ("other", "news_wire", datetime(2026, 11, 12, 15, 0))) is None


def test_partition_keeps_first_occurrence_only() -> None:
    items = [
        {"external_id": "a:1", "content_hash": "h1"},
        {"external_id": "a:1", "content_hash": "h2"},  # 同 external_id
        {"external_id": "a:2", "content_hash": "h1"},  # 同 content_hash
        {"external_id": "a:3", "content_hash": "h3"},
    ]

    fresh, duplicates = partition(items)

    assert [item["external_id"] for item in fresh] == ["a:1", "a:3"]
    assert [item["external_id"] for item in duplicates] == ["a:1", "a:2"]
    assert len(fresh) + len(duplicates) == len(items)


def test_partition_empty_batch() -> None:
    assert partition([]) == ([], [])


# ------------------------------------------------------------------ 异常 ----


def test_parse_seed_now_rejects_invalid_calendar_values() -> None:
    with pytest.raises(ValueError):
        parse_seed_now("2026-13-45T00:00:00")


def test_content_hash_rejects_non_string_body() -> None:
    """不可静默返回脏值：真值非字符串输入必须显式抛错（None 走「空值→空串」降级）。"""
    with pytest.raises(TypeError):
        content_hash(123, "正文")  # type: ignore[arg-type]
    assert content_hash("标题", None) == content_hash("标题", "")  # type: ignore[arg-type]
