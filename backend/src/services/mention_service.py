"""提及流 / 详情 / 情感复核。

所有查询都带品牌域裁剪：client 只能看自己 brand_key。
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import (
    BRAND_LABELS,
    REVIEW_STATUS_LABELS,
    SENTIMENT_LABELS,
    SOURCE_LABELS,
    ReviewStatus,
    SentimentLabel,
)
from src.constants.limits import MENTION_PAGE_DEFAULT, MENTION_PAGE_MAX
from src.constants.log_templates import ACTION_SENTIMENT_REVIEW
from src.models.burst_alert import BurstAlert
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services import audit_service
from src.utils.errors import AppError
from src.utils.textutils import snippet


def _base_query(brand_scope: str | None):
    stmt = select(Mention, SentimentScore, KeywordGroup).join(
        SentimentScore, SentimentScore.mention_id == Mention.id
    ).join(KeywordGroup, KeywordGroup.id == Mention.group_id)
    if brand_scope:
        stmt = stmt.where(Mention.brand_key == brand_scope)
    return stmt


def list_mentions(
    db: Session,
    *,
    brand_scope: str | None,
    group_code: str | None = None,
    source_code: str | None = None,
    label: str | None = None,
    review_status: str | None = None,
    q: str | None = None,
    days: int | None = None,
    sort: str = "published_desc",
    limit: int = MENTION_PAGE_DEFAULT,
    offset: int = 0,
) -> dict:
    limit = max(1, min(limit, MENTION_PAGE_MAX))
    stmt = _base_query(brand_scope)
    if group_code:
        stmt = stmt.where(KeywordGroup.code == group_code)
    if source_code:
        stmt = stmt.where(Mention.source_code == source_code)
    if label:
        stmt = stmt.where(SentimentScore.final_label == label)
    if review_status:
        stmt = stmt.where(SentimentScore.review_status == review_status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Mention.title.like(like), Mention.body.like(like)))
    anchor = db.execute(select(func.max(Mention.published_at))).scalar_one_or_none()
    if days and anchor is not None:
        stmt = stmt.where(Mention.published_at >= anchor - timedelta(days=days))

    if sort == "score_asc":
        stmt = stmt.order_by(SentimentScore.score.asc(), Mention.published_at.desc())
    elif sort == "score_desc":
        stmt = stmt.order_by(SentimentScore.score.desc(), Mention.published_at.desc())
    elif sort == "engagement_desc":
        stmt = stmt.order_by(Mention.engagement.desc(), Mention.published_at.desc())
    else:
        stmt = stmt.order_by(Mention.published_at.desc(), Mention.id)

    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    rows = db.execute(stmt.limit(limit).offset(offset)).all()
    items = [serialize_row(mention, score, group) for mention, score, group in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "anchor_at": anchor.isoformat() if anchor else None,
        "facets": _facets(db, brand_scope, group_code, source_code, label, review_status, q, days, anchor),
        "band": _band(db, brand_scope, group_code, source_code, review_status, q, days, anchor),
    }


def _filtered_pairs(
    db: Session,
    brand_scope: str | None,
    group_code: str | None,
    source_code: str | None,
    label: str | None,
    review_status: str | None,
    q: str | None,
    days: int | None,
    anchor,
):
    stmt = _base_query(brand_scope)
    if group_code:
        stmt = stmt.where(KeywordGroup.code == group_code)
    if source_code:
        stmt = stmt.where(Mention.source_code == source_code)
    if label:
        stmt = stmt.where(SentimentScore.final_label == label)
    if review_status:
        stmt = stmt.where(SentimentScore.review_status == review_status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Mention.title.like(like), Mention.body.like(like)))
    if days and anchor is not None:
        stmt = stmt.where(Mention.published_at >= anchor - timedelta(days=days))
    return stmt


def _facets(
    db: Session,
    brand_scope: str | None,
    group_code: str | None,
    source_code: str | None,
    label: str | None,
    review_status: str | None,
    q: str | None,
    days: int | None,
    anchor,
) -> dict:
    """筛选结果的分面计数：一次行扫描后在 Python 里聚合（900 行量级，避免子查询列名依赖）。"""
    stmt = _filtered_pairs(
        db, brand_scope, group_code, source_code, label, review_status, q, days, anchor
    )
    label_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    review_counts: dict[str, int] = {}
    group_counts: dict[str, int] = {}
    total = 0
    for _mention, score, group in db.execute(stmt).all():
        total += 1
        label_counts[score.final_label] = label_counts.get(score.final_label, 0) + 1
        source_counts[_mention.source_code] = source_counts.get(_mention.source_code, 0) + 1
        review_counts[score.review_status] = review_counts.get(score.review_status, 0) + 1
        group_counts[group.code] = group_counts.get(group.code, 0) + 1
    return {
        "label": [
            {
                "value": item.value,
                "label": SENTIMENT_LABELS[item.value],
                "count": label_counts.get(item.value, 0),
            }
            for item in SentimentLabel
        ],
        "source": [
            {
                "value": code,
                "label": SOURCE_LABELS.get(code, code),
                "count": source_counts.get(code, 0),
            }
            for code in SOURCE_LABELS
        ],
        "review": [
            {
                "value": item.value,
                "label": REVIEW_STATUS_LABELS[item.value],
                "count": review_counts.get(item.value, 0),
            }
            for item in ReviewStatus
        ],
        "group": group_counts,
        "total": total,
        "neg_rate": round(label_counts.get("neg", 0) / total, 4) if total else 0.0,
    }


def _band(
    db: Session,
    brand_scope: str | None,
    group_code: str | None,
    source_code: str | None,
    review_status: str | None,
    q: str | None,
    days: int | None,
    anchor,
) -> list[dict]:
    """评估日逐小时情感色带（负/中/正三段堆叠）。"""
    if anchor is None:
        return []
    stmt = _filtered_pairs(db, brand_scope, group_code, source_code, None, review_status, q, days, anchor)
    rows = db.execute(stmt).all()
    day = anchor.date()
    buckets = {hour: {"hour": hour, "pos": 0, "neu": 0, "neg": 0} for hour in range(24)}
    for mention, score, _group in rows:
        local = mention.published_at
        if local.date() != day:
            continue
        bucket = buckets[local.hour]
        bucket[score.final_label] = bucket.get(score.final_label, 0) + 1
    return [buckets[hour] for hour in range(24)]


def get_mention(db: Session, mention_id: str, brand_scope: str | None) -> dict:
    row = db.execute(
        select(Mention, SentimentScore, KeywordGroup)
        .join(SentimentScore, SentimentScore.mention_id == Mention.id)
        .join(KeywordGroup, KeywordGroup.id == Mention.group_id)
        .where(Mention.id == mention_id)
    ).first()
    if row is None:
        raise AppError(codes.NOT_FOUND, "提及不存在", f"mention_id={mention_id}")
    mention, score, group = row
    if brand_scope and mention.brand_key != brand_scope:
        raise AppError(codes.BRAND_SCOPE_DENIED, "该数据不属于你负责的品牌", "brand mismatch")

    related_rows = db.execute(
        select(Mention, SentimentScore)
        .join(SentimentScore, SentimentScore.mention_id == Mention.id)
        .where(
            Mention.group_id == mention.group_id,
            Mention.id != mention.id,
            Mention.published_at >= mention.published_at - timedelta(hours=2),
            Mention.published_at <= mention.published_at + timedelta(hours=2),
        )
        .order_by(Mention.published_at.desc())
        .limit(6)
    ).all()

    alerts = db.execute(
        select(BurstAlert)
        .where(
            BurstAlert.group_id == mention.group_id,
            BurstAlert.window_start <= mention.published_at,
            BurstAlert.window_end >= mention.published_at,
        )
        .order_by(BurstAlert.z_score.desc())
    ).scalars().all()

    payload = serialize_row(mention, score, group, detail=True)
    payload["related"] = [
        {
            "id": str(item.id),
            "title": item.title,
            "published_at": item.published_at.isoformat(),
            "label": item_score.final_label,
            "source_code": item.source_code,
            "score": item_score.score,
        }
        for item, item_score in related_rows
    ]
    payload["alerts"] = [
        {
            "id": str(alert.id),
            "level": alert.level,
            "z_score": alert.z_score,
            "count": alert.count,
            "window_start": alert.window_start.isoformat(),
            "status": alert.status,
        }
        for alert in alerts
    ]
    payload["audit"] = audit_service.for_entity(db, "mention", str(mention.id))
    return payload


def review(
    db: Session,
    mention_id: str,
    final_label: str,
    note: str,
    user: User,
    brand_scope: str | None,
    trace_id: str = "",
) -> dict:
    row = db.execute(
        select(Mention, SentimentScore, KeywordGroup)
        .join(SentimentScore, SentimentScore.mention_id == Mention.id)
        .join(KeywordGroup, KeywordGroup.id == Mention.group_id)
        .where(Mention.id == mention_id)
    ).first()
    if row is None:
        raise AppError(codes.NOT_FOUND, "提及不存在", f"mention_id={mention_id}")
    mention, score, group = row
    if brand_scope and mention.brand_key != brand_scope:
        raise AppError(codes.BRAND_SCOPE_DENIED, "该数据不属于你负责的品牌", "brand mismatch")
    if final_label not in {item.value for item in SentimentLabel}:
        raise AppError(codes.VALIDATION_ERROR, "情感标签不合法", f"label={final_label}")
    if score.review_status in (ReviewStatus.CONFIRMED.value, ReviewStatus.CORRECTED.value):
        raise AppError(codes.MENTION_ALREADY_REVIEWED, "该条提及已完成复核", f"mention_id={mention_id}")

    original = score.final_label
    score.final_label = final_label
    score.review_status = (
        ReviewStatus.CONFIRMED.value if final_label == score.label else ReviewStatus.CORRECTED.value
    )
    score.reviewer_id = user.id
    score.reviewer_email = user.email
    score.review_note = note[:400]
    from src.utils.timeutil import utcnow

    score.reviewed_at = utcnow()
    audit_service.record(
        db,
        action=ACTION_SENTIMENT_REVIEW,
        actor=user,
        entity_type="mention",
        entity_id=mention.id,
        detail={
            "from": original,
            "to": final_label,
            "label": score.label,
            "score": score.score,
            "note": note[:120],
            "group": group.code,
        },
        trace_id=trace_id,
    )
    db.commit()
    return serialize_row(mention, score, group, detail=True)


def review_queue(db: Session, brand_scope: str | None, limit: int = 20) -> dict:
    stmt = _base_query(brand_scope).where(SentimentScore.review_status == ReviewStatus.PENDING.value)
    stmt = stmt.order_by(SentimentScore.score.asc(), Mention.published_at.desc()).limit(limit)
    rows = db.execute(stmt).all()
    items = [serialize_row(mention, score, group) for mention, score, group in rows]
    total = int(
        db.execute(
            select(func.count())
            .select_from(
                _base_query(brand_scope).where(SentimentScore.review_status == ReviewStatus.PENDING.value).subquery()
            )
        ).scalar_one()
    )
    return {"items": items, "total": total}


def serialize_row(mention: Mention, score: SentimentScore, group: KeywordGroup, detail: bool = False) -> dict[str, Any]:
    hits = score.hits or []
    payload: dict[str, Any] = {
        "id": str(mention.id),
        "external_id": mention.external_id,
        "group_id": str(group.id),
        "group_code": group.code,
        "group_name": group.name,
        "brand_key": mention.brand_key,
        "brand_label": BRAND_LABELS.get(mention.brand_key, mention.brand_key),
        "source_code": mention.source_code,
        "source_label": SOURCE_LABELS.get(mention.source_code, mention.source_code),
        "title": mention.title,
        "excerpt": snippet(mention.body, 90),
        "author": mention.author,
        "author_followers": mention.author_followers,
        "url": mention.url,
        "engagement": mention.engagement,
        "published_at": mention.published_at.isoformat(),
        "sentiment": {
            "score": score.score,
            "label": score.label,
            "final_label": score.final_label,
            "label_text": SENTIMENT_LABELS.get(score.final_label, score.final_label),
            "confidence": score.confidence,
            "review_status": score.review_status,
            "review_status_text": REVIEW_STATUS_LABELS.get(score.review_status, score.review_status),
            "positive_count": score.positive_count,
            "negative_count": score.negative_count,
            "negation_count": score.negation_count,
            "degree_count": score.degree_count,
            "rhetoric_count": score.rhetoric_count,
            "exclaim_count": score.exclaim_count,
            "reviewer_email": score.reviewer_email,
            "review_note": score.review_note,
            "reviewed_at": score.reviewed_at.isoformat() if score.reviewed_at else None,
            "algorithm_version": score.algorithm_version,
            "hits": hits if detail else hits[:5],
        },
    }
    if detail:
        payload["body"] = mention.body
        payload["content_hash"] = mention.content_hash
        payload["fetched_at"] = mention.fetched_at.isoformat()
        payload["group"] = {
            "code": group.code,
            "name": group.name,
            "keywords": group.keywords,
            "synonyms": group.synonyms,
            "excludes": group.excludes,
            "z_threshold": group.z_threshold,
            "min_count": group.min_count,
        }
    return payload
