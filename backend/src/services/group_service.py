"""关键词组与词典服务：列表统计 / 编辑 / 召回试算。

品牌域：client 账号只能看到自己 brand_key 的组。
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.brands import brand_meta
from src.constants.enums import BRAND_LABELS
from src.constants.log_templates import ACTION_GROUP_CREATE, ACTION_GROUP_TRIAL, ACTION_GROUP_UPDATE
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.schemas.group import GroupCreateRequest, GroupTrialRequest, GroupUpdateRequest
from src.services import audit_service
from src.services.analysis.sentiment_analyzer import analyze_keyword_recall
from src.services.fixtures_loader import inbox_corpus
from src.utils.errors import AppError


def _stats(db: Session, anchor) -> dict[str, dict]:
    totals = dict(db.execute(select(Mention.group_id, func.count(Mention.id)).group_by(Mention.group_id)).all())
    negatives = dict(
        db.execute(
            select(Mention.group_id, func.count(SentimentScore.id))
            .join(SentimentScore, SentimentScore.mention_id == Mention.id)
            .where(SentimentScore.final_label == "neg")
            .group_by(Mention.group_id)
        ).all()
    )
    neus = dict(
        db.execute(
            select(Mention.group_id, func.count(SentimentScore.id))
            .join(SentimentScore, SentimentScore.mention_id == Mention.id)
            .where(SentimentScore.final_label == "neu")
            .group_by(Mention.group_id)
        ).all()
    )
    latest = dict(db.execute(select(Mention.group_id, func.max(Mention.published_at)).group_by(Mention.group_id)).all())
    recent: dict = {}
    if anchor is not None:
        cutoff = anchor - timedelta(hours=24)
        recent = dict(
            db.execute(
                select(Mention.group_id, func.count(Mention.id))
                .where(Mention.published_at >= cutoff)
                .group_by(Mention.group_id)
            ).all()
        )
    return {"totals": totals, "negatives": negatives, "neus": neus, "latest": latest, "recent": recent}


def list_groups(db: Session, brand_scope: str | None = None) -> dict:
    stmt = select(KeywordGroup).order_by(KeywordGroup.priority.desc(), KeywordGroup.code)
    if brand_scope:
        stmt = stmt.where(KeywordGroup.brand_key == brand_scope)
    groups = db.execute(stmt).scalars().all()
    anchor = db.execute(select(func.max(Mention.published_at))).scalar_one_or_none()
    stats = _stats(db, anchor)

    items = []
    for group in groups:
        total = int(stats["totals"].get(group.id, 0))
        neg = int(stats["negatives"].get(group.id, 0))
        neu = int(stats["neus"].get(group.id, 0))
        pos = total - neg - neu
        items.append(
            {
                "id": str(group.id),
                "code": group.code,
                "name": group.name,
                "brand_key": group.brand_key,
                "brand_label": BRAND_LABELS.get(group.brand_key, group.brand_key),
                "brand_category": (brand_meta(group.brand_key) or {}).get("category", ""),
                "keywords": group.keywords,
                "synonyms": group.synonyms,
                "excludes": group.excludes,
                "enabled": group.enabled,
                "priority": group.priority,
                "z_threshold": group.z_threshold,
                "min_count": group.min_count,
                "owner_note": group.owner_note,
                "stats": {
                    "mentions": total,
                    "recent_24h": int(stats["recent"].get(group.id, 0)),
                    "neg": neg,
                    "pos": pos,
                    "neu": neu,
                    "neg_rate": round(neg / total, 4) if total else 0.0,
                    "last_mention_at": stats["latest"].get(group.id).isoformat()
                    if stats["latest"].get(group.id)
                    else None,
                },
            }
        )
    return {
        "items": items,
        "totals": {
            "groups": len(items),
            "enabled": sum(1 for item in items if item["enabled"]),
            "mentions": sum(item["stats"]["mentions"] for item in items),
            "neg": sum(item["stats"]["neg"] for item in items),
        },
        "anchor_at": anchor.isoformat() if anchor else None,
    }


def get_group(db: Session, group_id: str) -> KeywordGroup:
    group = db.get(KeywordGroup, group_id)
    if group is None:
        raise AppError(codes.NOT_FOUND, "关键词组不存在", f"group_id={group_id}")
    return group


def _validate_payload(keywords: list[str], synonyms: list[str], excludes: list[str]) -> None:
    if not keywords:
        raise AppError(codes.GROUP_EMPTY_KEYWORDS, "关键词组至少需要一个主关键词", "keywords=[]")
    if len(keywords) > 12 or len(synonyms) > 24 or len(excludes) > 24:
        raise AppError(codes.VALIDATION_ERROR, "关键词 / 同义词 / 排除词数量超出上限", "max 12/24/24")


def create_group(db: Session, payload: GroupCreateRequest, user: User, trace_id: str = "") -> dict:
    existing = db.execute(select(KeywordGroup).where(KeywordGroup.code == payload.code)).scalar_one_or_none()
    if existing is not None:
        raise AppError(codes.GROUP_CODE_TAKEN, "关键词组编码已存在", f"code={payload.code}")
    _validate_payload(payload.keywords, payload.synonyms, payload.excludes)
    group = KeywordGroup(
        code=payload.code,
        name=payload.name,
        brand_key=payload.brand_key,
        keywords=payload.keywords,
        synonyms=payload.synonyms,
        excludes=payload.excludes,
        enabled=payload.enabled,
        priority=payload.priority,
        z_threshold=payload.z_threshold,
        min_count=payload.min_count,
        owner_note=payload.owner_note,
    )
    db.add(group)
    db.flush()
    audit_service.record(
        db,
        action=ACTION_GROUP_CREATE,
        actor=user,
        entity_type="keyword_group",
        entity_id=group.id,
        detail={"code": group.code, "brand": group.brand_key},
        trace_id=trace_id,
    )
    db.commit()
    return serialize(group)


def update_group(db: Session, group_id: str, payload: GroupUpdateRequest, user: User, trace_id: str = "") -> dict:
    group = get_group(db, group_id)
    changed: dict = {}
    data = payload.model_dump(exclude_none=True)
    for field, value in data.items():
        if field in ("keywords", "synonyms", "excludes"):
            _validate_payload(
                value if field == "keywords" else group.keywords,
                value if field == "synonyms" else group.synonyms,
                value if field == "excludes" else group.excludes,
            )
        setattr(group, field, value)
        changed[field] = value
    audit_service.record(
        db,
        action=ACTION_GROUP_UPDATE,
        actor=user,
        entity_type="keyword_group",
        entity_id=group.id,
        detail={"changed": list(changed.keys()), "code": group.code},
        trace_id=trace_id,
    )
    db.commit()
    return serialize(group)


def trial_recall(db: Session, payload: GroupTrialRequest, user: User, brand_scope: str | None, trace_id: str = "") -> dict:
    _validate_payload(payload.keywords, payload.synonyms, payload.excludes)
    corpus = inbox_corpus()
    samples = []
    matched = 0
    kept = 0
    excluded = 0
    per_source: dict[str, int] = {}
    for item in corpus:
        if payload.source_code and item["source_code"] != payload.source_code:
            continue
        if brand_scope and item["brand_key"] != brand_scope:
            continue
        result = analyze_keyword_recall(
            f"{item['title']} {item['body']}", payload.keywords, payload.synonyms, payload.excludes
        )
        if result["matched"]:
            matched += 1
        if result["hit_excludes"]:
            excluded += 1
        if result["kept"]:
            kept += 1
            per_source[item["source_code"]] = per_source.get(item["source_code"], 0) + 1
            if len(samples) < 8:
                samples.append(
                    {
                        "external_id": item["external_id"],
                        "title": item["title"],
                        "source_code": item["source_code"],
                        "brand_key": item["brand_key"],
                        "published_at": item["published_at"].isoformat(),
                        "hit_keywords": result["hit_keywords"],
                        "hit_synonyms": result["hit_synonyms"],
                        "hit_excludes": result["hit_excludes"],
                    }
                )
    scanned = len(corpus)
    audit_service.record(
        db,
        action=ACTION_GROUP_TRIAL,
        actor=user,
        entity_type="keyword_group",
        entity_id=payload.code or "draft",
        detail={"scanned": scanned, "matched": matched, "kept": kept, "excluded": excluded},
        trace_id=trace_id,
    )
    db.commit()
    return {
        "scanned": scanned,
        "matched": matched,
        "kept": kept,
        "excluded": excluded,
        "recall_rate": round(kept / scanned, 4) if scanned else 0.0,
        "precision_hint": round(kept / matched, 4) if matched else 0.0,
        "per_source": per_source,
        "samples": samples,
        "corpus_note": "试算基于采集窗口最近 92 条原始候选（与采集运行同一份语料）",
    }


def serialize(group: KeywordGroup) -> dict:
    return {
        "id": str(group.id),
        "code": group.code,
        "name": group.name,
        "brand_key": group.brand_key,
        "brand_label": BRAND_LABELS.get(group.brand_key, group.brand_key),
        "keywords": group.keywords,
        "synonyms": group.synonyms,
        "excludes": group.excludes,
        "enabled": group.enabled,
        "priority": group.priority,
        "z_threshold": group.z_threshold,
        "min_count": group.min_count,
        "owner_note": group.owner_note,
    }
