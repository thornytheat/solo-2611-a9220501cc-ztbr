"""算法 2：小时桶爆发检测（7 天同小时基线 μ/σ → z → 等级 → 相邻小时合并）。

期望值全部手算：
    σ_eff   = max(σ_population, 1.0)              # sigma_floor
    z       = (x − μ) / σ_eff
    trigger = z > 3.0 and x ≥ max(min_count=5, 2μ)
    level   = watch(z≤4) / alert(4<z≤6) / critical(z>6)
    unknown = 非零基线天数 < 3（历史不足，不告警）
评估日 = 语料里最新一条提及所在的自然日（与时区无关地固定，不依赖 now）。
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import pytest

from src.services.analysis.burst_detector import (
    DETECTION_VERSION,
    MentionPoint,
    build_hourly,
    detect,
    evaluation_day,
    floor_hour,
    level_for_z,
    trend_series,
)
from src.utils.timeutil import TZ_SHANGHAI

EVAL_DAY = date(2026, 11, 12)
# seed 里 coffee-foreign@14:00 的基线：过去 7 天同小时计数（由远到近）
SEED_SERIES = [0, 1, 3, 4, 8, 9, 9]
SEED_MEAN = 34 / 7  # 4.857142857
SEED_STD = math.sqrt(608) / 7  # 3.522522287
SEED_Z = 183 / math.sqrt(608)  # 7.421630017


def _at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ_SHANGHAI)


def make_points(
    group_id: str = "coffee-foreign",
    brand_key: str = "coffee",
    hour: int = 14,
    series: list[int] | None = None,
    eval_count: int = 0,
    eval_day: date = EVAL_DAY,
) -> list[MentionPoint]:
    """按 (series=过去 7 天同小时计数, eval_count=评估日该小时计数) 造提及。"""
    series = SEED_SERIES if series is None else series
    points: list[MentionPoint] = []
    for idx, count in enumerate(series):
        day = eval_day - timedelta(days=7 - idx)  # idx 0 → −7 天，idx 6 → −1 天
        for n in range(count):
            points.append(
                MentionPoint(
                    group_id=group_id,
                    brand_key=brand_key,
                    published_at=_at(day, hour, minute=n),
                    title=f"{group_id}-base{idx}-{n}",
                    engagement=n,
                )
            )
    for n in range(eval_count):
        points.append(
            MentionPoint(
                group_id=group_id,
                brand_key=brand_key,
                published_at=_at(eval_day, hour, minute=n),
                title=f"{group_id}-eval-{n}",
                engagement=n,
            )
        )
    return points


# --------------------------------------------------------------- 正常路径 ----


def test_seed_critical_window_matches_documented_values() -> None:
    """seed 真实基线 (0,1,3,4,8,9,9) + 14:00 量 31 → μ=4.8571 σ=3.5225 z=7.4216 critical。"""
    result = detect(make_points(eval_count=31))

    assert result["eval_day"] == EVAL_DAY
    assert result["version"] == DETECTION_VERSION
    assert result["scanned_hours"] == 24  # 单组 24 个小时桶，x=0 的桶被跳过
    assert result["unknown_windows"] == []
    assert len(result["events"]) == 1

    event = result["events"][0].to_dict()
    assert event["group_id"] == "coffee-foreign"
    assert event["brand_key"] == "coffee"
    assert event["window_start"] == "2026-11-12T14:00:00+08:00"
    assert event["window_end"] == "2026-11-12T15:00:00+08:00"
    assert event["merged_windows"] == ["2026-11-12T14:00"]
    assert event["count"] == 31
    assert event["baseline_mean"] == pytest.approx(round(SEED_MEAN, 4))
    assert event["baseline_std"] == pytest.approx(round(SEED_STD, 4))
    assert event["z_score"] == pytest.approx(round(SEED_Z, 4))
    assert event["level"] == "critical"
    # 算法逐日回看 1..7 天，所以回传序列是「近→远」；fixtures 里存的是「远→近」。
    # μ/σ 与顺序无关（总体均值/标准差），因此 z 不受该顺序影响。
    assert event["baseline_series"] == list(reversed(SEED_SERIES)) == [9, 9, 8, 4, 3, 1, 0]
    assert event["sample_titles"] == ["coffee-foreign-eval-0", "coffee-foreign-eval-1", "coffee-foreign-eval-2"]


def test_adjacent_triggered_hours_merge_into_one_event() -> None:
    """14:00 量 31、15:00 量 25 同时触发 → 合并为 1 个事件，count 累加 56，z 取最大。"""
    points = make_points(hour=14, eval_count=31) + make_points(hour=15, eval_count=25)
    result = detect(points)

    assert len(result["events"]) == 1
    event = result["events"][0].to_dict()
    assert event["count"] == 56
    assert event["merged_windows"] == ["2026-11-12T14:00", "2026-11-12T15:00"]
    assert event["window_start"] == "2026-11-12T14:00:00+08:00"
    assert event["window_end"] == "2026-11-12T16:00:00+08:00"
    assert event["z_score"] == pytest.approx(7.4216)  # max(7.4216, 5.7183)
    assert event["level"] == "critical"
    assert event["baseline_mean"] == pytest.approx(round(SEED_MEAN, 4))  # 加权均值与单窗一致


def test_non_adjacent_hours_stay_separate_events() -> None:
    """14:00 与 20:00 都触发但不是相邻小时 → 2 个事件，按 z 降序。"""
    points = make_points(hour=14, eval_count=31) + make_points(hour=20, eval_count=16)
    result = detect(points)

    assert len(result["events"]) == 2
    first, second = (event.to_dict() for event in result["events"])
    assert first["window_start"] == "2026-11-12T14:00:00+08:00"
    assert second["window_start"] == "2026-11-12T20:00:00+08:00"
    assert second["z_score"] == pytest.approx(3.1633)  # (16 − 4.8571) / 3.5225
    assert second["level"] == "watch"
    assert second["z_score"] < first["z_score"]


def test_two_groups_scan_two_days_worth_of_hour_buckets() -> None:
    """2 个组 × 24 小时桶 = 48 个扫描桶；每组各自独立判定。"""
    points = make_points(group_id="coffee-foreign", hour=14, eval_count=31) + make_points(
        group_id="snack-additive", brand_key="snack", hour=10, eval_count=7, series=[2, 2, 2, 3, 2, 2, 2]
    )
    result = detect(points)

    assert result["scanned_hours"] == 48
    assert len(result["events"]) == 2
    by_group = {event.group_id: event.to_dict() for event in result["events"]}
    assert by_group["coffee-foreign"]["level"] == "critical"
    # snack-additive: μ=15/7=2.1429, σ=0.3499→1.0, z=(7−2.1429)/1=4.8571 → alert
    snack = by_group["snack-additive"]
    assert snack["baseline_mean"] == pytest.approx(2.1429)
    assert snack["baseline_std"] == pytest.approx(0.3499)
    assert snack["z_score"] == pytest.approx(4.8571)
    assert snack["level"] == "alert"


@pytest.mark.parametrize(
    ("z", "expected"),
    [
        (3.0001, "watch"),
        (4.0, "watch"),
        (4.0001, "alert"),
        (6.0, "alert"),
        (6.0001, "critical"),
        (7.4216, "critical"),
    ],
)
def test_level_boundaries(z: float, expected: str) -> None:
    """watch(3,4] / alert(4,6] / critical(>6) —— 边界含在低一级。"""
    assert level_for_z(z) == expected


# --------------------------------------------------------------- 边界情况 ----


def test_empty_points_returns_empty_result() -> None:
    result = detect([])

    assert result == {
        "events": [],
        "eval_day": None,
        "unknown_windows": [],
        "scanned_hours": 0,
    }


def test_insufficient_history_reports_unknown_instead_of_event() -> None:
    """非零基线天数 = 1 < 3 → 记 unknown，不产生事件（历史不足不告警）。"""
    result = detect(make_points(hour=9, series=[0, 0, 0, 0, 0, 0, 1], eval_count=6))

    assert result["events"] == []
    assert len(result["unknown_windows"]) == 1
    unknown = result["unknown_windows"][0]
    assert unknown["group_id"] == "coffee-foreign"
    assert unknown["window_start"] == "2026-11-12T09:00:00+08:00"
    assert unknown["count"] == 6
    assert unknown["baseline_days"] == 1
    assert unknown["z_score"] == pytest.approx(5.8571)  # (6 − 0.1429) / 1.0


def test_zero_variance_uses_sigma_floor_not_division_by_zero() -> None:
    """全相同基线 [6]×7 → σ=0，按 floor=1 平滑：z=(12−6)/1=6.0 → alert（不是 critical）。"""
    result = detect(make_points(hour=9, series=[6, 6, 6, 6, 6, 6, 6], eval_count=12))

    assert len(result["events"]) == 1
    event = result["events"][0].to_dict()
    assert event["baseline_mean"] == pytest.approx(6.0)
    assert event["baseline_std"] == pytest.approx(0.0)  # 回传原始 σ，不回传平滑值
    assert event["z_score"] == pytest.approx(6.0)
    assert event["level"] == "alert"


def test_ratio_gate_blocks_high_baseline_moderate_z() -> None:
    """基线 μ=10 时 min_required = max(5, 2μ) = 20：量 14 → z=4 但被量级门禁挡住。"""
    result = detect(make_points(hour=9, series=[10] * 7, eval_count=14))

    assert result["events"] == []
    assert result["unknown_windows"] == []


def test_ratio_gate_accepts_exact_threshold() -> None:
    """量刚好等于 2μ=20 且 z=10 → critical（门禁是 ≥ 不是 >）。"""
    result = detect(make_points(hour=9, series=[10] * 7, eval_count=20))

    event = result["events"][0].to_dict()
    assert event["count"] == 20
    assert event["z_score"] == pytest.approx(10.0)
    assert event["level"] == "critical"


def test_no_history_at_all_reports_unknown() -> None:
    """完全没有基线（7 天全 0）+ 评估日突增到 6 → 记 unknown（baseline_days=0），不告警。"""
    result = detect(make_points(hour=9, series=[0] * 7, eval_count=6))

    assert result["events"] == []
    assert len(result["unknown_windows"]) == 1
    unknown = result["unknown_windows"][0]
    assert unknown["baseline_days"] == 0
    assert unknown["count"] == 6
    assert unknown["z_score"] == pytest.approx(6.0)  # (6 − 0) / sigma_floor 1.0


def test_single_point_stays_below_min_count_silently() -> None:
    """样本不足（1 条）且低于 min_count=5 → 既没有事件也不塞 unknown 噪声。"""
    result = detect([MentionPoint("coffee-foreign", "coffee", _at(EVAL_DAY, 14), "唯一一条", 0)])

    assert result["events"] == []
    assert result["unknown_windows"] == []
    assert result["scanned_hours"] == 24


def test_hours_with_zero_count_are_skipped() -> None:
    """评估日只有 14:00 有量：其余 23 个小时桶 x=0 → 既不告警也不记 unknown。"""
    result = detect(make_points(hour=14, eval_count=31))

    assert result["unknown_windows"] == []
    assert len(result["events"]) == 1
    assert result["scanned_hours"] == 24


# ----------------------------------------------------- 时间桶 / 评估日 ----


def test_floor_hour_is_shanghai_local_and_naive_is_shanghai() -> None:
    naive = datetime(2026, 11, 12, 14, 37, 12, 999)
    aware_utc_like = datetime(2026, 11, 12, 6, 37, 12, tzinfo=TZ_SHANGHAI)

    assert floor_hour(naive) == datetime(2026, 11, 12, 14, 0, tzinfo=TZ_SHANGHAI)
    assert floor_hour(aware_utc_like) == datetime(2026, 11, 12, 6, 0, tzinfo=TZ_SHANGHAI)


def test_evaluation_day_from_data_and_explicit_override() -> None:
    points = make_points(hour=14, eval_count=3)

    assert evaluation_day([]) is None
    assert evaluation_day(points) == EVAL_DAY
    assert evaluation_day(points, date(2026, 11, 1)) == date(2026, 11, 1)


def test_explicit_day_with_no_counts_yields_no_events() -> None:
    """显式指定一个语料里没有的日子 → 所有桶 x=0 → 明确空结果（不是脏数据）。"""
    result = detect(make_points(hour=14, eval_count=31), explicit_day=date(2026, 10, 1))

    assert result["eval_day"] == date(2026, 10, 1)
    assert result["events"] == []
    assert result["scanned_hours"] == 24


def test_build_hourly_counts_and_title_cap() -> None:
    points = make_points(hour=14, eval_count=7)
    buckets = build_hourly(points)

    key = ("coffee-foreign", datetime(2026, 11, 12, 14, 0, tzinfo=TZ_SHANGHAI))
    assert buckets[key].count == 7
    assert len(buckets[key].titles) == 5  # 每小时只留 5 条标题样本
    assert key in buckets


def test_trend_series_has_24_rows_and_seed_baseline() -> None:
    points = make_points(hour=14, eval_count=31)
    rows = trend_series(points, "coffee-foreign", EVAL_DAY)

    assert len(rows) == 24
    assert rows[14] == {"hour": 14, "count": 31, "baseline": pytest.approx(4.86)}
    assert rows[15] == {"hour": 15, "count": 0, "baseline": pytest.approx(0.0)}
    assert [row["hour"] for row in rows] == list(range(24))
