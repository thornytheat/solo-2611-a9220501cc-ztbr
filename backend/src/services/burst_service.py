"""爆发检测服务：跑检测 / 看板 / 认领 / 处置 / 趋势。"""
from __future__ import annotations

import time
from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import (
    BRAND_LABELS,
    BURST_LEVEL_LABELS,
    BURST_STATUS_LABELS,
    BurstStatus,
)
from src.constants.log_templates import ACTION_BURST_CLAIM, ACTION_BURST_DETECT, ACTION_BURST_DISPOSE
from src.models.burst_alert import BurstAlert
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services import audit_service
from src.services.analysis.burst_detector import DETECTION_VERSION, MentionPoint, detect, trend_series
from src.utils.errors import AppError
from src.utils.timeutil import utcnow


def _load_points(db: Session, brand_scope: str | None) -> list[MentionPoint]:
    stmt = select(Mention.id, Mention.group_id, Mention.brand_key, Mention.published_at, Mention.title, Mention.engagement)
    if brand_scope:
        stmt = stmt.where(Mention.brand_key == brand_scope)
    return [
        MentionPoint(
            group_id=str(row[1]),
            brand_key=row[2],
            published_at=row[3],
            title=row[4],
            engagement=row[5],
        )
        for row in db.execute(stmt).all()
    ]


def run_detection(db: Session, user: User, brand_scope: str | None, trace_id: str = "") -> dict:
    started = time.perf_counter()
    points = _load_points(db, brand_scope)
    group_rows = db.execute(select(KeywordGroup)).scalars().all()
    groups = {str(group.id): group for group in group_rows}
    thresholds = {gid: (group.z_threshold, group.min_count) for gid, group in groups.items()}
    result = detect(points, group_thresholds=thresholds)

    created = 0
    updated = 0
    events_payload = []
    for event in result["events"]:
        group = groups.get(event.group_id)
        if group is None:
            continue
        existing = db.execute(
            select(BurstAlert).where(
                BurstAlert.group_id == group.id, BurstAlert.window_start == event.window_start
            )
        ).scalar_one_or_none()
        if existing is None:
            alert = BurstAlert(
                group_id=group.id,
                brand_key=group.brand_key,
                window_start=event.window_start,
                window_end=event.window_end,
                count=event.count,
                baseline_mean=round(event.baseline_mean, 4),
                baseline_std=round(event.baseline_std, 4),
                z_score=round(event.z_score, 4),
                level=event.level,
                status=BurstStatus.OPEN.value,
                merged_windows=event.merged_windows,
                baseline_series=event.baseline_series,
                sample_titles=event.sample_titles,
                detection_version=event.detection_version,
            )
            db.add(alert)
            db.flush()
            created += 1
        else:
            alert = existing
            alert.window_end = event.window_end
            alert.count = event.count
            alert.baseline_mean = round(event.baseline_mean, 4)
            alert.baseline_std = round(event.baseline_std, 4)
            alert.z_score = round(event.z_score, 4)
            alert.level = event.level
            alert.merged_windows = event.merged_windows
            alert.baseline_series = event.baseline_series
            alert.sample_titles = event.sample_titles
            alert.detection_version = event.detection_version
            updated += 1
        events_payload.append(serialize(alert, group))

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    payload = {
        "eval_day": result["eval_day"].isoformat() if result["eval_day"] else None,
        "scanned_hours": result["scanned_hours"],
        "events": events_payload,
        "created": created,
        "updated": updated,
        "unknown_windows": result["unknown_windows"],
        "algorithm_version": DETECTION_VERSION,
        "thresholds": {
            "baseline_days": settings.burst_baseline_days,
            "z_threshold": settings.burst_z_threshold,
            "min_count": settings.burst_min_count,
            "ratio": settings.burst_ratio,
            "sigma_floor": settings.burst_sigma_floor,
            "alert_z": settings.burst_alert_z,
            "critical_z": settings.burst_critical_z,
        },
        "elapsed_ms": elapsed_ms,
    }
    audit_service.record(
        db,
        action=ACTION_BURST_DETECT,
        actor=user,
        entity_type="burst_alert",
        entity_id=f"eval-{payload['eval_day']}",
        detail={"events": len(events_payload), "created": created, "updated": updated, "elapsed_ms": elapsed_ms},
        trace_id=trace_id,
    )
    db.commit()
    return payload


def list_alerts(
    db: Session,
    brand_scope: str | None,
    level: str | None = None,
    status: str | None = None,
    limit: int = 40,
) -> dict:
    stmt = select(BurstAlert, KeywordGroup).join(KeywordGroup, KeywordGroup.id == BurstAlert.group_id)
    if brand_scope:
        stmt = stmt.where(BurstAlert.brand_key == brand_scope)
    if level:
        stmt = stmt.where(BurstAlert.level == level)
    if status:
        stmt = stmt.where(BurstAlert.status == status)
    stmt = stmt.order_by(BurstAlert.z_score.desc(), BurstAlert.window_start.desc()).limit(limit)
    rows = db.execute(stmt).all()
    items = [serialize(alert, group) for alert, group in rows]

    counter_stmt = select(BurstAlert.level, BurstAlert.status, func.count()).group_by(
        BurstAlert.level, BurstAlert.status
    )
    if brand_scope:
        counter_stmt = counter_stmt.where(BurstAlert.brand_key == brand_scope)
    by_level: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    mentions_total = 0
    for level_value, status_value, count in db.execute(counter_stmt).all():
        by_level[level_value] += count
        by_status[status_value] += count
        mentions_total += count
    return {
        "items": items,
        "levels": [
            {"value": key, "label": BURST_LEVEL_LABELS[key], "count": by_level.get(key, 0)}
            for key in ("critical", "alert", "watch")
        ],
        "statuses": [
            {"value": key, "label": BURST_STATUS_LABELS[key], "count": by_status.get(key, 0)}
            for key in ("open", "claimed", "handled", "dismissed")
        ],
        "total": mentions_total,
        "thresholds": {
            "z_threshold": settings.burst_z_threshold,
            "min_count": settings.burst_min_count,
            "baseline_days": settings.burst_baseline_days,
            "sigma_floor": settings.burst_sigma_floor,
        },
    }


def get_alert(db: Session, alert_id: str) -> tuple[BurstAlert, KeywordGroup]:
    row = db.execute(
        select(BurstAlert, KeywordGroup)
        .join(KeywordGroup, KeywordGroup.id == BurstAlert.group_id)
        .where(BurstAlert.id == alert_id)
    ).first()
    if row is None:
        raise AppError(codes.NOT_FOUND, "预警事件不存在", f"alert_id={alert_id}")
    return row[0], row[1]


def detail(db: Session, alert_id: str, brand_scope: str | None) -> dict:
    alert, group = get_alert(db, alert_id)
    if brand_scope and alert.brand_key != brand_scope:
        raise AppError(codes.BRAND_SCOPE_DENIED, "该数据不属于你负责的品牌", "brand mismatch")
    payload = serialize(alert, group)
    day = alert.window_start.date()
    points = _load_points(db, brand_scope)
    payload["trend"] = trend_series(points, str(group.id), day)
    payload["audit"] = audit_service.for_entity(db, "burst_alert", str(alert.id))
    mentions = db.execute(
        select(Mention, SentimentScore)
        .join(SentimentScore, SentimentScore.mention_id == Mention.id)
        .where(
            Mention.group_id == group.id,
            Mention.published_at >= alert.window_start,
            Mention.published_at <= alert.window_end,
        )
        .order_by(SentimentScore.score.asc())
        .limit(8)
    ).all()
    payload["window_mentions"] = [
        {
            "id": str(mention.id),
            "title": mention.title,
            "published_at": mention.published_at.isoformat(),
            "label": score.final_label,
            "score": score.score,
            "source_code": mention.source_code,
        }
        for mention, score in mentions
    ]
    return payload


def claim(db: Session, alert_id: str, user: User, brand_scope: str | None, trace_id: str = "") -> dict:
    alert, group = get_alert(db, alert_id)
    if brand_scope and alert.brand_key != brand_scope:
        raise AppError(codes.BRAND_SCOPE_DENIED, "该数据不属于你负责的品牌", "brand mismatch")
    if alert.status in (BurstStatus.HANDLED.value, BurstStatus.DISMISSED.value):
        raise AppError(codes.BURST_NOT_OPEN, "该事件已结束，无需认领", f"status={alert.status}")
    if alert.status == BurstStatus.CLAIMED.value and str(alert.claimed_by) != str(user.id):
        raise AppError(
            codes.BURST_ALREADY_CLAIMED,
            "该事件已被其他值班员认领",
            f"claimed_by={alert.claimed_by_email}",
        )
    alert.status = BurstStatus.CLAIMED.value
    alert.claimed_by = user.id
    alert.claimed_by_email = user.email
    alert.claimed_at = utcnow()
    audit_service.record(
        db,
        action=ACTION_BURST_CLAIM,
        actor=user,
        entity_type="burst_alert",
        entity_id=alert.id,
        detail={"group": group.code, "level": alert.level, "z": alert.z_score},
        trace_id=trace_id,
    )
    db.commit()
    return serialize(alert, group)


def dispose(
    db: Session,
    alert_id: str,
    status: str,
    note: str,
    user: User,
    brand_scope: str | None,
    trace_id: str = "",
) -> dict:
    alert, group = get_alert(db, alert_id)
    if brand_scope and alert.brand_key != brand_scope:
        raise AppError(codes.BRAND_SCOPE_DENIED, "该数据不属于你负责的品牌", "brand mismatch")
    if status not in (BurstStatus.HANDLED.value, BurstStatus.DISMISSED.value):
        raise AppError(codes.VALIDATION_ERROR, "处置状态只能是 handled 或 dismissed", f"status={status}")
    if alert.status == BurstStatus.CLAIMED.value and str(alert.claimed_by) != str(user.id):
        raise AppError(codes.BURST_ALREADY_CLAIMED, "该事件由其他人认领，不能代为处置", "claimed by other")
    alert.status = status
    alert.disposition_note = note[:400]
    alert.disposed_at = utcnow()
    if alert.claimed_by is None:
        alert.claimed_by = user.id
        alert.claimed_by_email = user.email
        alert.claimed_at = utcnow()
    audit_service.record(
        db,
        action=ACTION_BURST_DISPOSE,
        actor=user,
        entity_type="burst_alert",
        entity_id=alert.id,
        detail={"status": status, "note": note[:120], "group": group.code},
        trace_id=trace_id,
    )
    db.commit()
    return serialize(alert, group)


def dashboard(db: Session, brand_scope: str | None) -> dict:
    listing = list_alerts(db, brand_scope, limit=100)
    events = listing["items"]
    top = events[0] if events else None
    today = datetime.now().date()
    day_events = [item for item in events if item["window_start"][:10] == str(today)] or events
    counts = Counter(item["level"] for item in day_events)
    groups: Counter[str] = Counter()
    for item in day_events:
        groups[item["group_name"]] += item["count"]
    return {
        "levels": listing["levels"],
        "statuses": listing["statuses"],
        "total": listing["total"],
        "top_event": top,
        "level_counts": {key: counts.get(key, 0) for key in ("critical", "alert", "watch")},
        "top_groups": [{"name": name, "count": count} for name, count in groups.most_common(5)],
        "thresholds": listing["thresholds"],
        "eval_day": events[0]["eval_day"] if events else None,
    }


def serialize(alert: BurstAlert, group: KeywordGroup) -> dict:
    return {
        "id": str(alert.id),
        "group_id": str(group.id),
        "group_code": group.code,
        "group_name": group.name,
        "brand_key": alert.brand_key,
        "brand_label": BRAND_LABELS.get(alert.brand_key, alert.brand_key),
        "window_start": alert.window_start.isoformat(),
        "window_end": alert.window_end.isoformat(),
        "eval_day": alert.window_start.date().isoformat(),
        "count": alert.count,
        "baseline_mean": round(alert.baseline_mean, 4),
        "baseline_std": round(alert.baseline_std, 4),
        "z_score": round(alert.z_score, 4),
        "level": alert.level,
        "level_label": BURST_LEVEL_LABELS.get(alert.level, alert.level),
        "status": alert.status,
        "status_label": BURST_STATUS_LABELS.get(alert.status, alert.status),
        "merged_windows": alert.merged_windows,
        "baseline_series": alert.baseline_series,
        "sample_titles": alert.sample_titles,
        "claimed_by_email": alert.claimed_by_email,
        "claimed_at": alert.claimed_at.isoformat() if alert.claimed_at else None,
        "disposition_note": alert.disposition_note,
        "disposed_at": alert.disposed_at.isoformat() if alert.disposed_at else None,
        "detection_version": alert.detection_version,
        "thresholds": {"z": group.z_threshold, "min_count": group.min_count},
    }
