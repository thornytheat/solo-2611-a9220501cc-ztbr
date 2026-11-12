"""幂等演示数据：`python -m scripts.seed_demo`（SEED_DEMO=true 时容器启动自动跑一次）。

自然键：
  User.email / KeywordGroup.code / Mention.external_id / BurstAlert(group_id, window_start)
首次：4 来源 / 12 组 / 900 提及（正 512 中 241 负 147）/ 5 个爆发事件 / 3 账号
重复：全部 SEED_SKIPPED，末尾 SEED_SUMMARY 行逐字一致（Lead 用它校验幂等）。
"""
from __future__ import annotations

import sys
from collections import Counter
from typing import Any

from sqlalchemy import func, select

from src.config.database import session_scope
from src.constants.brands import BRAND_CATALOG
from src.constants.enums import SourceCode
from src.constants.roles import ROLE_ADMIN
from src.constants.sources import SOURCE_CATALOG
from src.models.burst_alert import BurstAlert
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services.analysis.sentiment_analyzer import analyze
from src.services.burst_service import run_detection
from src.utils.password import hash_password
from scripts import fixtures

LABEL = fixtures.LABEL
CREATED = 0
SKIPPED = 0


def _log(kind: str, entity: str, key: object) -> None:
    global CREATED, SKIPPED
    if kind == "SEED_CREATED":
        CREATED += 1
    else:
        SKIPPED += 1
    print(f"{kind} entity={entity} key={key}", flush=True)


def _created(entity: str, key: object) -> None:
    _log("SEED_CREATED", entity, key)


def _skipped(entity: str, key: object) -> None:
    _log("SEED_SKIPPED", entity, key)


# ------------------------------------------------------------------ 账号 ----


def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role, brand_key in fixtures.DEMO_USERS:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(fixtures.DEMO_PASSWORD),
                display_name=display_name,
                role=role,
                brand_key=brand_key,
                is_active=True,
            )
            db.add(user)
            db.flush()
            _created("User", email)
        else:
            _skipped("User", email)
        users[role] = user
    return users


# -------------------------------------------------------------- 关键词组 ----


def seed_groups(db) -> dict[str, KeywordGroup]:
    groups: dict[str, KeywordGroup] = {}
    for spec in fixtures.GROUP_SPECS:
        group = db.execute(select(KeywordGroup).where(KeywordGroup.code == spec["code"])).scalar_one_or_none()
        if group is None:
            group = KeywordGroup(
                code=spec["code"],
                name=spec["name"],
                brand_key=spec["brand_key"],
                keywords=spec["keywords"],
                synonyms=spec["synonyms"],
                excludes=spec["excludes"],
                enabled=True,
                priority=spec["priority"],
                z_threshold=spec["z_threshold"],
                min_count=spec["min_count"],
                owner_note=spec["owner_note"],
            )
            db.add(group)
            db.flush()
            _created("KeywordGroup", spec["code"])
        else:
            _skipped("KeywordGroup", spec["code"])
        groups[spec["code"]] = group
    return groups


# ------------------------------------------------------------------ 提及 ----


def seed_mentions(db, groups: dict[str, KeywordGroup]) -> tuple[int, Counter]:
    labels: Counter[str] = Counter()
    inserted = 0
    for item in fixtures.seed_mentions():
        existing = db.execute(select(Mention).where(Mention.external_id == item["external_id"])).first()
        if existing is not None:
            _skipped("Mention", item["external_id"])
            continue
        group = groups[item["group_code"]]
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
            fetched_at=item["published_at"],
            content_hash=item["content_hash"],
        )
        db.add(mention)
        db.flush()
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
            review_status=item["review_status"],
        )
        db.add(score)
        labels[result.label] += 1
        inserted += 1
    db.flush()
    if inserted:
        _created("Mention", f"bulk={inserted}")
    else:
        _skipped("Mention", "bulk=0")
    return inserted, labels


# ------------------------------------------------------------------ 汇总 ----


def summary_counts(db) -> dict[str, Any]:
    return {
        "brand": LABEL,
        "sources": len(SOURCE_CATALOG),
        "groups": int(db.execute(select(func.count(KeywordGroup.id))).scalar_one()),
        "mentions": int(db.execute(select(func.count(Mention.id))).scalar_one()),
        "bursts": int(db.execute(select(func.count(BurstAlert.id))).scalar_one()),
        "users": int(db.execute(select(func.count(User.id))).scalar_one()),
    }


def format_summary(counts: dict[str, Any]) -> str:
    """键与顺序逐字固定：brand sources groups mentions bursts users。"""
    return (
        f"SEED_SUMMARY brand={counts['brand']} sources={counts['sources']} groups={counts['groups']} "
        f"mentions={counts['mentions']} bursts={counts['bursts']} users={counts['users']}"
    )


def seed_all() -> dict[str, Any]:
    with session_scope() as db:
        users = seed_users(db)
        groups = seed_groups(db)
        inserted, inserted_labels = seed_mentions(db, groups)
        db.flush()

        admin = users[ROLE_ADMIN]
        detection = run_detection(db, admin, None)
        db.flush()

        counts = summary_counts(db)
        distribution = dict(
            db.execute(
                select(SentimentScore.final_label, func.count(SentimentScore.id)).group_by(
                    SentimentScore.final_label
                )
            ).all()
        )
        levels = dict(
            db.execute(select(BurstAlert.level, func.count(BurstAlert.id)).group_by(BurstAlert.level)).all()
        )
        print(
            "SEED_LABELS "
            + " ".join(
                f"{key}={distribution.get(key, 0)}" for key in ("pos", "neu", "neg")
            )
            + f" total={sum(distribution.values())}",
            flush=True,
        )
        print(
            "SEED_BURSTS "
            + " ".join(f"{key}={levels.get(key, 0)}" for key in ("critical", "alert", "watch"))
            + f" events={len(detection['events'])} created={detection['created']} updated={detection['updated']}",
            flush=True,
        )
        print(
            "SEED_SOURCES "
            + " ".join(
                f"{item['code']}={item['name']}" for item in SOURCE_CATALOG
            )
            + f" brands={len(BRAND_CATALOG)}",
            flush=True,
        )
        print(f"SEED_ALGO sentiment=1.0.0 burst={detection['algorithm_version']} eval_day={detection['eval_day']}", flush=True)
        print(format_summary(counts), flush=True)
        return {
            "created": CREATED,
            "skipped": SKIPPED,
            "counts": counts,
            "inserted_labels": dict(inserted_labels),
            "detection": {"events": len(detection["events"]), "created": detection["created"]},
        }


if __name__ == "__main__":
    result = seed_all()
    print(f"SEED_DONE created={result['created']} skipped={result['skipped']}", flush=True)
    sys.exit(0)
