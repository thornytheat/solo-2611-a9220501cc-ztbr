"""采集运行：扫采集窗口 → 两级去重 → 入库 → 同步打分。

幂等：同一批候选第二次运行时新增 0、重复 92（external_id 命中 6 + 批次内重复）。
"""
from __future__ import annotations

import time
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import SOURCE_LABELS
from src.constants.log_templates import ACTION_COLLECT_RUN
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services import audit_service
from src.services.analysis.dedupe import hash_key, is_duplicate
from src.services.analysis.sentiment_analyzer import analyze
from src.services.fixtures_loader import inbox_corpus
from src.utils.timeutil import utcnow


def run_collection(db: Session, user: User, trace_id: str = "") -> dict:
    started = time.perf_counter()
    groups = {group.code: group for group in db.execute(select(KeywordGroup)).scalars().all()}
    existing_ids = {row[0] for row in db.execute(select(Mention.external_id)).all()}
    existing_hashes = {
        hash_key(row[0], row[1], row[2])
        for row in db.execute(select(Mention.content_hash, Mention.source_code, Mention.published_at)).all()
    }

    scanned = 0
    inserted = 0
    duplicates = 0
    duplicate_reasons: dict[str, int] = {"external_id": 0, "content_hash": 0}
    per_source: dict[str, int] = {}
    per_group: dict[str, int] = {}
    skipped_groups: list[str] = []
    new_mentions: list[Mention] = []

    for item in inbox_corpus():
        if item["group_code"] not in groups:
            continue
        group = groups[item["group_code"]]
        if not group.enabled:
            skipped_groups.append(group.code)
            continue
        scanned += 1
        key = hash_key(item["content_hash"], item["source_code"], item["published_at"])
        reason = is_duplicate(existing_ids, existing_hashes, item["external_id"], key)
        if reason:
            duplicates += 1
            duplicate_reasons[reason] = duplicate_reasons.get(reason, 0) + 1
            continue

        mention = Mention(
            external_id=item["external_id"],
            group_id=group.id,
            brand_key=group.brand_key,
            source_code=item["source_code"],
            title=item["title"],
            body=item["body"],
            author=item["author"],
            author_followers=item["author_followers"],
            url=item["url"],
            engagement=item["engagement"],
            published_at=item["published_at"],
            fetched_at=utcnow(),
            content_hash=item["content_hash"],
        )
        db.add(mention)
        new_mentions.append(mention)
        existing_ids.add(item["external_id"])
        existing_hashes.add(key)
        inserted += 1
        per_source[item["source_code"]] = per_source.get(item["source_code"], 0) + 1
        per_group[group.code] = per_group.get(group.code, 0) + 1

    db.flush()
    distribution = {"pos": 0, "neu": 0, "neg": 0}
    for mention in new_mentions:
        result = analyze(f"{mention.title}\n{mention.body}")
        score = SentimentScore(
            mention_id=mention.id,
            score=result.score,
            label=result.label,
            final_label=result.label,
            confidence=result.confidence,
            hits=result.hits,
            positive_count=result.positive_count,
            negative_count=result.negative_count,
            negation_count=result.negation_count,
            degree_count=result.degree_count,
            rhetoric_count=result.rhetoric_count,
            exclaim_count=result.exclaim_count,
            algorithm_version=result.algorithm_version,
        )
        db.add(score)
        distribution[result.label] += 1
    db.flush()

    total_mentions = int(db.execute(select(func.count(Mention.id))).scalar_one())
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    report = {
        "scanned": scanned,
        "inserted": inserted,
        "duplicates": duplicates,
        "duplicate_reasons": duplicate_reasons,
        "distribution": distribution,
        "per_source": [
            {"code": code, "label": SOURCE_LABELS.get(code, code), "count": count}
            for code, count in sorted(per_source.items())
        ],
        "per_group": per_group,
        "skipped_groups": sorted(set(skipped_groups)),
        "total_mentions": total_mentions,
        "elapsed_ms": elapsed_ms,
        "window_note": "采集窗口 = 过去 7 天 05:00-06:59 的补扫候选（确定性 fixture）",
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    audit_service.record(
        db,
        action=ACTION_COLLECT_RUN,
        actor=user,
        entity_type="collect_run",
        entity_id=f"run-{int(time.time())}",
        detail={key: report[key] for key in ("scanned", "inserted", "duplicates", "total_mentions", "elapsed_ms")},
        trace_id=trace_id,
    )
    db.commit()
    return report


def recent_runs(db: Session, limit: int = 8) -> list[dict]:
    return audit_service.recent(db, limit=limit, action=ACTION_COLLECT_RUN)
