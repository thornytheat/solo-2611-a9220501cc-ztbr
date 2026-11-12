"""不变量 / 性质 + 异常输入：同一份输入必须得到同一份输出，且口径是封闭的。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from src.services.analysis.burst_detector import MentionPoint, build_hourly, detect, level_for_z, trend_series
from src.services.analysis.sentiment_analyzer import analyze, analyze_keyword_recall, label_for_score
from src.utils.timeutil import TZ_SHANGHAI

EVAL_DAY = date(2026, 11, 12)
SEED_SERIES = [0, 1, 3, 4, 8, 9, 9]

SEED_TEXTS = [
    "澄野挂耳咖啡开袋就香气很足，回甘明显，已经回购三次了。",
    "芽初婴儿米粉比上次还顺滑，家里人一致好评。",
    "岩行冲锋衣性价比很划算，一箱到手 39.9，超值。",
    "毛球冻干主粮的用料扎实，包装严实，物流也及时，好评。",
    "净川洗衣凝珠拆开就有刺鼻异味，袋底还有异物，太失望了！",
    "脆岛薯片这批明显发霉，霉点一片，已经投诉了。",
    "关于净川除菌喷雾的检测报告编号 A2026-1187，可在官网查询。",
    "客服回复：脆岛海苔脆的发货仓在苏州，三天内出库。",
    "难道这也叫好喝",
    "不好喝，后来香浓",
]


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ_SHANGHAI)


def _points(series: list[int] | None = None, eval_count: int = 31, hour: int = 14) -> list[MentionPoint]:
    series = SEED_SERIES if series is None else series
    points: list[MentionPoint] = []
    for idx, count in enumerate(series):
        day = EVAL_DAY - timedelta(days=7 - idx)
        for n in range(count):
            points.append(MentionPoint("coffee-foreign", "coffee", _at(day, hour, n), f"b{idx}-{n}", n))
    for n in range(eval_count):
        points.append(MentionPoint("coffee-foreign", "coffee", _at(EVAL_DAY, hour, n), f"e-{n}", n))
    return points


# ---------------------------------------------------------------- 不变量 ----


def test_score_stays_inside_open_unit_interval_and_label_is_consistent() -> None:
    for text in SEED_TEXTS:
        result = analyze(text)
        assert -1.0 < result.score < 1.0, text
        assert 0.0 <= result.confidence <= 1.0, text
        assert result.label == label_for_score(result.score), text


def test_analyze_is_deterministic() -> None:
    for text in SEED_TEXTS:
        assert analyze(text).to_dict() == analyze(text).to_dict(), text


def test_detect_is_deterministic_for_same_input_order() -> None:
    points = _points()

    first = detect(points)
    second = detect(points)

    assert [event.to_dict() for event in first["events"]] == [event.to_dict() for event in second["events"]]
    assert first["unknown_windows"] == second["unknown_windows"]
    assert first["scanned_hours"] == second["scanned_hours"]


def test_detect_is_order_independent_on_metrics() -> None:
    points = _points()

    forward = detect(points)
    backward = detect(list(reversed(points)))

    assert len(forward["events"]) == len(backward["events"]) == 1
    left, right = forward["events"][0].to_dict(), backward["events"][0].to_dict()
    for field in ("window_start", "window_end", "count", "baseline_mean", "baseline_std", "z_score", "level"):
        assert left[field] == right[field], field


def test_counts_are_conserved_between_points_buckets_and_trend() -> None:
    points = _points()

    buckets = build_hourly(points)
    total_in_buckets = sum(stat.count for stat in buckets.values())
    trend = trend_series(points, "coffee-foreign", EVAL_DAY)

    assert total_in_buckets == len(points)
    assert sum(row["count"] for row in trend) == sum(1 for point in points if point.published_at.date() == EVAL_DAY)


def test_level_is_monotone_in_z() -> None:
    rank = {"watch": 0, "alert": 1, "critical": 2}
    zs = [3.0001, 3.9, 4.0, 4.1, 5.99, 6.0, 6.01, 9.5]

    levels = [level_for_z(z) for z in zs]

    assert [rank[level] for level in levels] == sorted(rank[level] for level in levels)
    assert levels == ["watch", "watch", "watch", "alert", "alert", "alert", "critical", "critical"]


def test_more_rhetoric_markers_never_raise_the_score() -> None:
    plain = analyze("好喝").score
    one_marker = analyze("这也叫好喝").score
    two_markers = analyze("难道这也叫好喝").score

    assert plain == pytest.approx(0.3934)
    assert one_marker == pytest.approx(0.3223)
    assert two_markers == pytest.approx(0.2324)
    assert plain > one_marker > two_markers


# ------------------------------------------------------------- 异常 / 降级 ----


def test_analyze_rejects_none_instead_of_returning_dirty_value() -> None:
    """非 str 输入必须炸（不能静默给出一个「中性」分）。"""
    with pytest.raises(AttributeError):
        analyze(None)  # type: ignore[arg-type]


def test_keyword_recall_degrades_on_none_text() -> None:
    """空/None 文本在召回试算里是明确的「未命中」，不是异常也不是脏命中。"""
    result = analyze_keyword_recall(None, ["异物"], ["澄野异物"], ["咖啡渣"])  # type: ignore[arg-type]

    assert result == {
        "matched": False,
        "kept": False,
        "hit_keywords": [],
        "hit_synonyms": [],
        "hit_excludes": [],
    }


def test_score_distribution_ignores_unknown_labels_but_keeps_total() -> None:
    from src.services.analysis.sentiment_analyzer import score_distribution

    dist = score_distribution(["pos", "unknown", "neg"])

    assert dist == {"pos": 1, "neu": 0, "neg": 1, "total": 3}


def test_explicit_day_outside_corpus_yields_empty_not_stale_numbers() -> None:
    result = detect(_points(), explicit_day=date(2026, 10, 1))

    assert result["events"] == []
    assert result["eval_day"] == date(2026, 10, 1)
    assert result["scanned_hours"] == 24
