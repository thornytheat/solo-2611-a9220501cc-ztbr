"""情感计算服务：批量重算 + 分布统计 + 复核队列概览。

重算不会覆盖人工复核结果（review_status 已是 confirmed/corrected 的行只更新分数）。
"""
from __future__ import annotations

import time
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import BRAND_LABELS, REVIEW_STATUS_LABELS, SENTIMENT_LABELS
from src.constants.log_templates import ACTION_SENTIMENT_RESCORE
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services import audit_service
from src.services.analysis.sentiment_analyzer import ALGORITHM_VERSION, analyze
from src.utils.timeutil import utcnow


def rescore_all(db: Session, user: User, brand_scope: str | None, trace_id: str = "") -> dict:
    started = time.perf_counter()
    stmt = select(Mention, SentimentScore).join(SentimentScore, SentimentScore.mention_id == Mention.id)
    if brand_scope:
        stmt = stmt.where(Mention.brand_key == brand_scope)
    rows = db.execute(stmt).all()

    changed = 0
    preserved = 0
    distribution: Counter[str] = Counter()
    for mention, score in rows:
        result = analyze(f"{mention.title}\n{mention.body}")
        if score.score != result.score or score.label != result.label:
            changed += 1
        score.score = result.score
        score.label = result.label
        score.confidence = result.confidence
        score.hits = result.hits
        score.positive_count = result.positive_count
        score.negative_count = result.negative_count
        score.negation_count = result.negation_count
        score.degree_count = result.degree_count
        score.rhetoric_count = result.rhetoric_count
        score.exclaim_count = result.exclaim_count
        score.algorithm_version = result.algorithm_version
        if score.review_status in ("confirmed", "corrected"):
            preserved += 1
        else:
            score.final_label = result.label
        distribution[score.final_label] += 1
    db.flush()

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    payload = {
        "scored": len(rows),
        "changed": changed,
        "review_preserved": preserved,
        "distribution": {
            "pos": distribution.get("pos", 0),
            "neu": distribution.get("neu", 0),
            "neg": distribution.get("neg", 0),
            "total": len(rows),
        },
        "neg_rate": round(distribution.get("neg", 0) / len(rows), 4) if rows else 0.0,
        "algorithm_version": ALGORITHM_VERSION,
        "elapsed_ms": elapsed_ms,
        "scored_at": utcnow().isoformat(),
    }
    audit_service.record(
        db,
        action=ACTION_SENTIMENT_RESCORE,
        actor=user,
        entity_type="sentiment",
        entity_id="all",
        detail={key: payload[key] for key in ("scored", "changed", "neg_rate", "elapsed_ms")},
        trace_id=trace_id,
    )
    db.commit()
    return payload


def summary(db: Session, brand_scope: str | None) -> dict:
    group_stmt = select(KeywordGroup)
    if brand_scope:
        group_stmt = group_stmt.where(KeywordGroup.brand_key == brand_scope)
    groups = {group.id: group for group in db.execute(group_stmt).scalars().all()}

    rows = []
    if groups:
        rows = db.execute(
            select(Mention.group_id, SentimentScore.final_label, SentimentScore.review_status, func.count())
            .join(SentimentScore, SentimentScore.mention_id == Mention.id)
            .where(Mention.group_id.in_(list(groups.keys())))
            .group_by(Mention.group_id, SentimentScore.final_label, SentimentScore.review_status)
        ).all()

    totals: Counter[str] = Counter()
    review: Counter[str] = Counter()
    per_group: dict = {gid: Counter() for gid in groups}
    for group_id, label, status, count in rows:
        totals[label] += count
        review[status] += count
        per_group[group_id][label] += count

    total = sum(totals.values())
    group_rows = []
    for group_id, group in groups.items():
        counter = per_group[group_id]
        group_total = sum(counter.values())
        group_rows.append(
            {
                "id": str(group.id),
                "code": group.code,
                "name": group.name,
                "brand_key": group.brand_key,
                "brand_label": BRAND_LABELS.get(group.brand_key, group.brand_key),
                "mentions": group_total,
                "pos": counter.get("pos", 0),
                "neu": counter.get("neu", 0),
                "neg": counter.get("neg", 0),
                "neg_rate": round(counter.get("neg", 0) / group_total, 4) if group_total else 0.0,
            }
        )
    group_rows.sort(key=lambda item: (-item["neg_rate"], -item["mentions"]))

    negative_rates = [item["neg_rate"] for item in group_rows if item["mentions"] >= 20]
    return {
        "distribution": [
            {
                "value": label,
                "label": SENTIMENT_LABELS[label],
                "count": totals.get(label, 0),
                "ratio": round(totals.get(label, 0) / total, 4) if total else 0.0,
            }
            for label in ("pos", "neu", "neg")
        ],
        "total": total,
        "neg_rate": round(totals.get("neg", 0) / total, 4) if total else 0.0,
        "avg_neg_rate": round(sum(negative_rates) / len(negative_rates), 4) if negative_rates else 0.0,
        "review": [
            {"value": status, "label": REVIEW_STATUS_LABELS.get(status, status), "count": review.get(status, 0)}
            for status in ("auto", "pending", "confirmed", "corrected")
        ],
        "groups": group_rows,
        "algorithm_version": ALGORITHM_VERSION,
        "scope": brand_scope,
    }


def top_evidence_words(db: Session, brand_scope: str | None, limit: int = 12) -> list[dict]:
    """负面命中词频（导出日报与看板共用）。"""
    stmt = (
        select(SentimentScore.hits)
        .join(Mention, Mention.id == SentimentScore.mention_id)
        .where(SentimentScore.final_label == "neg")
    )
    if brand_scope:
        stmt = stmt.where(Mention.brand_key == brand_scope)
    counter: Counter[str] = Counter()
    for (hits,) in db.execute(stmt).all():
        for hit in hits or []:
            if hit.get("polarity", 0) < 0:
                counter[hit["word"]] += 1
    return [{"word": word, "count": count} for word, count in counter.most_common(limit)]
