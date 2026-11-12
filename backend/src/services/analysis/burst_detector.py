"""爆发检测（算法 2）：关键词组 × 小时桶 + 同小时基线 z。

口径（逐字对应 settings）：
1. 计数：把提及按 Asia/Shanghai 的整点小时分桶（group_id, hour_start）；
2. 基线：对评估日某小时 H，取过去 7 天同小时（H 点）计数的均值 μ 与总体标准差 σ；
   σ < 1 时按 1 平滑（避免小样本把 z 放大到无穷）；
3. 触发：z = (x - μ) / σ_eff > 3 且 x ≥ max(5, 2μ)；
4. 等级：3<z≤4 watch / 4<z≤6 alert / z>6 critical；
5. 相邻触发小时合并为一个事件（count 累加、z 取最大、基线按计数加权）；
6. 历史不足（非零基线天数 < 3）→ unknown，不产生事件。

同输入同输出：不依赖当前时间，评估日 = 语料里最新一条提及所在的自然日。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from src.config.settings import settings
from src.utils.timeutil import TZ_SHANGHAI

DETECTION_VERSION = "burst-1.0.0"
MIN_BASELINE_NONZERO_DAYS = 3


@dataclass
class MentionPoint:
    group_id: str
    brand_key: str
    published_at: datetime
    title: str
    engagement: int = 0


@dataclass
class HourStat:
    count: int = 0
    titles: list[str] = field(default_factory=list)


@dataclass
class BurstEvent:
    group_id: str
    brand_key: str
    window_start: datetime
    window_end: datetime
    count: int
    baseline_mean: float
    baseline_std: float
    z_score: float
    level: str
    merged_windows: list[str]
    baseline_series: list[int]
    sample_titles: list[str]
    detection_version: str = DETECTION_VERSION

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "brand_key": self.brand_key,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "count": self.count,
            "baseline_mean": round(self.baseline_mean, 4),
            "baseline_std": round(self.baseline_std, 4),
            "z_score": round(self.z_score, 4),
            "level": self.level,
            "merged_windows": self.merged_windows,
            "baseline_series": self.baseline_series,
            "sample_titles": self.sample_titles,
            "detection_version": self.detection_version,
        }


def _local(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=TZ_SHANGHAI)
    return value.astimezone(TZ_SHANGHAI)


def floor_hour(value: datetime) -> datetime:
    local = _local(value)
    return local.replace(minute=0, second=0, microsecond=0)


def level_for_z(z: float) -> str:
    if z > settings.burst_critical_z:
        return "critical"
    if z > settings.burst_alert_z:
        return "alert"
    return "watch"


def build_hourly(points: list[MentionPoint]) -> dict[tuple[str, datetime], HourStat]:
    buckets: dict[tuple[str, datetime], HourStat] = {}
    for point in points:
        key = (point.group_id, floor_hour(point.published_at))
        stat = buckets.setdefault(key, HourStat())
        stat.count += 1
        if len(stat.titles) < 5:
            stat.titles.append(point.title)
    return buckets


def evaluation_day(points: list[MentionPoint], explicit: date | None = None) -> date | None:
    if explicit:
        return explicit
    if not points:
        return None
    return max(_local(p.published_at).date() for p in points)


def _population_std(values: list[float], mean: float) -> float:
    if not values:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(max(variance, 0.0))


def detect(
    points: list[MentionPoint],
    *,
    group_thresholds: dict[str, tuple[float, int]] | None = None,
    explicit_day: date | None = None,
) -> dict:
    """返回 {"events": [BurstEvent], "eval_day": date, "unknown_windows": [...], "scanned_hours": n}"""
    buckets = build_hourly(points)
    eval_day = evaluation_day(points, explicit_day)
    events: list[BurstEvent] = []
    unknown: list[dict] = []
    if eval_day is None:
        return {"events": [], "eval_day": None, "unknown_windows": [], "scanned_hours": 0}

    thresholds = group_thresholds or {}
    groups = sorted({p.group_id for p in points})
    scanned = 0

    for group_id in groups:
        z_threshold, min_count = thresholds.get(group_id, (settings.burst_z_threshold, settings.burst_min_count))
        brand_key = next(p.brand_key for p in points if p.group_id == group_id)
        triggered_hours: list[dict] = []
        for hour in range(24):
            start = datetime(eval_day.year, eval_day.month, eval_day.day, hour, tzinfo=TZ_SHANGHAI)
            stat = buckets.get((group_id, start))
            x = stat.count if stat else 0
            scanned += 1
            if x == 0:
                continue
            series: list[int] = []
            for back in range(1, settings.burst_baseline_days + 1):
                day = eval_day - timedelta(days=back)
                past = datetime(day.year, day.month, day.day, hour, tzinfo=TZ_SHANGHAI)
                series.append(buckets.get((group_id, past)).count if buckets.get((group_id, past)) else 0)
            nonzero = sum(1 for value in series if value > 0)
            mean = sum(series) / len(series)
            std = _population_std([float(v) for v in series], mean)
            std_eff = max(std, settings.burst_sigma_floor)
            z = (x - mean) / std_eff
            if nonzero < MIN_BASELINE_NONZERO_DAYS:
                if z > settings.burst_z_threshold and x >= min_count:
                    unknown.append(
                        {
                            "group_id": group_id,
                            "window_start": start.isoformat(),
                            "count": x,
                            "baseline_days": nonzero,
                            "z_score": round(z, 4),
                        }
                    )
                continue
            min_required = max(min_count, settings.burst_ratio * mean)
            if z > z_threshold and x >= min_required:
                triggered_hours.append(
                    {
                        "start": start,
                        "count": x,
                        "mean": mean,
                        "std": std,
                        "z": z,
                        "level": level_for_z(z),
                        "series": series,
                        "titles": stat.titles if stat else [],
                    }
                )

        # 相邻小时合并
        merged: list[list[dict]] = []
        for item in triggered_hours:
            if merged and item["start"] - merged[-1][-1]["start"] == timedelta(hours=1):
                merged[-1].append(item)
            else:
                merged.append([item])

        for cluster in merged:
            total = sum(item["count"] for item in cluster)
            weighted_mean = sum(item["mean"] * item["count"] for item in cluster) / total
            weighted_std = sum(item["std"] * item["count"] for item in cluster) / total
            max_item = max(cluster, key=lambda item: item["z"])
            titles: list[str] = []
            for item in cluster:
                for title in item["titles"]:
                    if title not in titles:
                        titles.append(title)
            events.append(
                BurstEvent(
                    group_id=group_id,
                    brand_key=brand_key,
                    window_start=cluster[0]["start"],
                    window_end=cluster[-1]["start"] + timedelta(hours=1),
                    count=total,
                    baseline_mean=weighted_mean,
                    baseline_std=weighted_std,
                    z_score=max_item["z"],
                    level=level_for_z(max_item["z"]),
                    merged_windows=[item["start"].strftime("%Y-%m-%dT%H:%M") for item in cluster],
                    baseline_series=max_item["series"],
                    sample_titles=titles[:3],
                )
            )

    events.sort(key=lambda e: (-e.z_score, e.window_start))
    return {
        "events": events,
        "eval_day": eval_day,
        "unknown_windows": unknown,
        "scanned_hours": scanned,
        "version": DETECTION_VERSION,
    }


def trend_series(points: list[MentionPoint], group_id: str, day: date, hours: int = 24) -> list[dict]:
    """某组某天的逐小时量与基线，供看板折线 / 柱状自绘。"""
    buckets = build_hourly(points)
    out: list[dict] = []
    for hour in range(hours):
        start = datetime(day.year, day.month, day.day, hour, tzinfo=TZ_SHANGHAI)
        stat = buckets.get((group_id, start))
        count = stat.count if stat else 0
        series = []
        for back in range(1, settings.burst_baseline_days + 1):
            past_day = day - timedelta(days=back)
            past = datetime(past_day.year, past_day.month, past_day.day, hour, tzinfo=TZ_SHANGHAI)
            stat_past = buckets.get((group_id, past))
            series.append(stat_past.count if stat_past else 0)
        out.append({"hour": hour, "count": count, "baseline": round(sum(series) / len(series), 2)})
    return out
