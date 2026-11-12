"""元信息：把枚举 / 来源 / 品牌 / 阈值 / 算法版本一次性交给前端（前端不硬编码）。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.brands import BRAND_CATALOG
from src.constants.enums import (
    BRAND_LABELS,
    BURST_LEVEL_LABELS,
    BURST_STATUS_LABELS,
    REVIEW_STATUS_LABELS,
    ROLE_LABELS,
    SENTIMENT_LABELS,
    SOURCE_LABELS,
    BrandKey,
    BurstLevel,
    BurstStatus,
    ReviewStatus,
    SentimentLabel,
    SourceCode,
    UserRole,
)
from src.constants.log_templates import ACTION_LABELS
from src.constants.roles import PERMISSIONS
from src.constants.sources import SOURCE_CATALOG
from src.models.burst_alert import BurstAlert
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.services.analysis.burst_detector import DETECTION_VERSION
from src.services.analysis.lexicon import lexicon_size
from src.services.analysis.sentiment_analyzer import ALGORITHM_VERSION


def bootstrap(db: Session, brand_scope: str | None) -> dict:
    group_stmt = select(KeywordGroup).order_by(KeywordGroup.priority.desc(), KeywordGroup.code)
    if brand_scope:
        group_stmt = group_stmt.where(KeywordGroup.brand_key == brand_scope)
    groups = db.execute(group_stmt).scalars().all()

    mention_count = int(db.execute(select(func.count(Mention.id))).scalar_one())
    burst_count = int(db.execute(select(func.count(BurstAlert.id))).scalar_one())

    return {
        "brand": settings.brand,
        "org": {
            "name": settings.org_name,
            "size": settings.org_size,
            "brands_served": len(BRAND_CATALOG),
            "sources": len(SOURCE_CATALOG),
        },
        "enums": {
            "sentiment": [{"value": item.value, "label": SENTIMENT_LABELS[item.value]} for item in SentimentLabel],
            "burst_level": [{"value": item.value, "label": BURST_LEVEL_LABELS[item.value]} for item in BurstLevel],
            "burst_status": [{"value": item.value, "label": BURST_STATUS_LABELS[item.value]} for item in BurstStatus],
            "review_status": [
                {"value": item.value, "label": REVIEW_STATUS_LABELS[item.value]} for item in ReviewStatus
            ],
            "source": [{"value": item.value, "label": SOURCE_LABELS[item.value]} for item in SourceCode],
            "brand": [{"value": item.value, "label": BRAND_LABELS[item.value]} for item in BrandKey],
            "role": [{"value": item.value, "label": ROLE_LABELS[item.value]} for item in UserRole],
            "audit_action": [{"value": key, "label": label} for key, label in ACTION_LABELS.items()],
        },
        "sources": SOURCE_CATALOG,
        "brands": BRAND_CATALOG,
        "groups": [
            {
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
            }
            for group in groups
        ],
        "thresholds": {
            "sentiment_pos": settings.sentiment_pos_threshold,
            "sentiment_neg": settings.sentiment_neg_threshold,
            "sentiment_normalizer": settings.sentiment_normalizer,
            "negation_window": settings.negation_window,
            "negation_damping": settings.negation_damping,
            "burst_baseline_days": settings.burst_baseline_days,
            "burst_z_threshold": settings.burst_z_threshold,
            "burst_min_count": settings.burst_min_count,
            "burst_ratio": settings.burst_ratio,
            "burst_sigma_floor": settings.burst_sigma_floor,
            "burst_alert_z": settings.burst_alert_z,
            "burst_critical_z": settings.burst_critical_z,
        },
        "algorithms": {
            "sentiment": {"version": ALGORITHM_VERSION, "lexicon": lexicon_size()},
            "burst": {"version": DETECTION_VERSION},
        },
        "permissions": {action: list(roles) for action, roles in PERMISSIONS.items()},
        "counts": {"mentions": mention_count, "bursts": burst_count, "groups": len(groups)},
        "scope": brand_scope,
    }


def sentiment_dictionary() -> dict:
    """词典可视化（页面「词典管理」用）：正负词与权重、程度副词、否定词。"""
    from src.services.analysis.lexicon import DEGREE_ADVERBS, NEGATIVE_LEXICON, NEGATORS, POSITIVE_LEXICON, RHETORICAL_MARKERS

    def rows(lexicon: dict[str, float]) -> list[dict]:
        return [{"word": word, "weight": weight} for word, weight in sorted(lexicon.items(), key=lambda kv: -kv[1])]

    return {
        "positive": rows(POSITIVE_LEXICON),
        "negative": rows(NEGATIVE_LEXICON),
        "degree": [{"word": word, "weight": weight} for word, weight in DEGREE_ADVERBS.items()],
        "negators": list(NEGATORS),
        "rhetorical": list(RHETORICAL_MARKERS),
        "sizes": lexicon_size(),
    }
