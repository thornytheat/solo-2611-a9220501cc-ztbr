"""补采批次服务：创建批次 → 逐源处理 → 断点续跑 → 对账回看。

设计要点：
1. 逐源事务（SAVEPOINT）：单个来源失败只回滚该来源的入库，已成功来源的结果保留；
2. 断点 = CollectBatchSource.status + cursor：续跑/重试只挑 pending/failed 来源，
   成功来源永不重放，重复运行同一批次不新增提及；
3. 两级去重沿用 collect_service 的 external_id + content_hash 口径，
   重复条目只记台账不入库；
4. 新提及同步写 SentimentScore（情感分析），批次封口后按品牌重跑爆发检测；
5. 页面计数全部从 collect_batch_items 台账聚合，保证与入库明细对得上。
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import BRAND_LABELS, SOURCE_LABELS
from src.constants.log_templates import (
    ACTION_COLLECT_BATCH_CREATE,
    ACTION_COLLECT_BATCH_RUN,
)
from src.models.collect_batch import (
    BATCH_COMPLETED,
    BATCH_PARTIAL,
    BATCH_PENDING,
    BATCH_RUNNING,
    ITEM_DUPLICATE,
    ITEM_FAILED,
    ITEM_INSERTED,
    ITEM_PENDING,
    ITEM_SKIPPED,
    SOURCE_FAILED,
    SOURCE_FINAL_STATUSES,
    SOURCE_PENDING,
    SOURCE_RUNNING,
    SOURCE_SUCCESS,
    BATCH_STATUS_LABELS,
    SOURCE_STATUS_LABELS,
    CollectBatch,
    CollectBatchItem,
    CollectBatchSource,
)
from src.models.keyword_group import KeywordGroup
from src.models.mention import Mention
from src.models.sentiment_score import SentimentScore
from src.models.user import User
from src.services import audit_service, burst_service
from src.services.analysis.collect_planner import (
    build_item_ledger,
    build_source_plan,
    select_candidates,
)
from src.services.analysis.dedupe import hash_key, is_duplicate
from src.services.analysis.sentiment_analyzer import analyze
from src.services.analysis.source_gateway import gateway
from src.services.fixtures_loader import inbox_corpus
from src.utils.errors import AppError
from src.utils.timeutil import utcnow

# 批次台账分页上限与默认
ITEMS_PAGE_MAX = 100


# --------------------------------------------------------------- 批次创建 ----


def _next_batch_no(db: Session, now: datetime) -> str:
    prefix = f"CB{now.strftime('%Y%m%d')}"
    like = f"{prefix}-%"
    last = db.execute(
        select(CollectBatch.batch_no).where(CollectBatch.batch_no.like(like)).order_by(
            CollectBatch.batch_no.desc()
        ).limit(1)
    ).scalar_one_or_none()
    seq = 1
    if last:
        try:
            seq = int(last.rsplit("-", 1)[1]) + 1
        except (IndexError, ValueError):
            seq = 1
    return f"{prefix}-{seq:03d}"


def create_batch(
    db: Session,
    user: User,
    *,
    brand_key: str,
    source_codes: tuple[str, ...],
    window_start: datetime,
    window_end: datetime,
    trace_id: str = "",
) -> dict:
    if window_end <= window_start:
        raise AppError(codes.VALIDATION_ERROR, "结束时间必须晚于开始时间", "window range invalid")
    if not source_codes:
        raise AppError(codes.VALIDATION_ERROR, "至少选择一个采集来源", "empty sources")

    groups = db.execute(
        select(KeywordGroup).where(KeywordGroup.brand_key == brand_key)
    ).scalars().all()
    enabled_codes = frozenset(group.code for group in groups if group.enabled)

    candidates = select_candidates(
        inbox_corpus(),
        brand_key=brand_key,
        source_codes=source_codes,
        window_start=window_start,
        window_end=window_end,
        enabled_group_codes=enabled_codes,
    )
    if not candidates:
        raise AppError(
            codes.COLLECT_EMPTY,
            "所选品牌 / 来源 / 时间段内没有补采候选",
            f"brand={brand_key} sources={source_codes}",
        )

    now = utcnow()
    batch = CollectBatch(
        batch_no=_next_batch_no(db, now),
        brand_key=brand_key,
        window_start=window_start,
        window_end=window_end,
        status=BATCH_PENDING,
        total_candidates=len(candidates),
        created_by=user.id,
        created_by_email=user.email,
    )
    db.add(batch)
    db.flush()

    for plan in build_source_plan(candidates, source_codes):
        db.add(
            CollectBatchSource(
                batch_id=batch.id,
                source_code=plan["source_code"],
                position=plan["position"],
                status=plan["status"],
                candidates=plan["candidates"],
                cursor=0,
            )
        )
    for row in build_item_ledger(candidates):
        db.add(
            CollectBatchItem(
                batch_id=batch.id,
                source_code=row["source_code"],
                position=row["position"],
                external_id=row["external_id"],
                group_code=row["group_code"],
                title=row["title"],
                published_at=row["published_at"],
                status=ITEM_PENDING,
            )
        )
    db.flush()
    audit_service.record(
        db,
        action=ACTION_COLLECT_BATCH_CREATE,
        actor=user,
        entity_type="collect_batch",
        entity_id=batch.batch_no,
        detail={
            "brand": brand_key,
            "sources": list(source_codes),
            "candidates": len(candidates),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        },
        trace_id=trace_id,
    )
    db.commit()
    db.refresh(batch)
    return detail(db, batch.id, user)


# --------------------------------------------------------------- 批次运行 ----


def run_batch(db: Session, user: User, batch_id: str, trace_id: str = "") -> dict:
    """续跑/重试入口：只处理 pending/failed 来源，成功来源不重放。"""
    batch = _get_batch(db, batch_id)
    if batch.status in (BATCH_COMPLETED,):
        # 已完成批次重复运行：直接回显，不新增任何提及
        return detail(db, batch.id, user)

    started = time.perf_counter()
    batch.status = BATCH_RUNNING
    if batch.started_at is None:
        batch.started_at = utcnow()
    batch.run_count += 1
    db.flush()

    # 只挑未终态来源（pending 首跑；failed 重试；running 为崩溃残留，同样续跑）
    # 每次调用每来源最多尝试一次：本轮尝试过的来源（无论成败）不再重放，
    # 失败来源留待下一次 run_batch 调用（前端「重试失败来源」）处理。
    run_errors: list[str] = []
    attempted_this_run: set[str] = set()
    while True:
        # 每次提交后 ORM 对象会过期，统一重新加载，避免操作失效实例
        batch = _get_batch(db, batch_id)
        due_sources = [
            row
            for row in batch.sources
            if row.status not in SOURCE_FINAL_STATUSES and row.source_code not in attempted_this_run
        ]
        if not due_sources:
            break
        source_row = min(due_sources, key=lambda row: row.position)
        source_code = source_row.source_code
        try:
            _process_source(db, batch, source_row)
            # 逐源提交：单源崩溃/中断不影响已成功来源，续跑从下一来源或断点继续
            db.commit()
        except Exception as exc:  # noqa: BLE001 - 单源失败不拖垮整批
            db.rollback()
            # rollback 后 ORM 对象失效，重新加载再落失败态
            batch = _get_batch(db, batch_id)
            source_row = _get_source_row(db, batch.id, source_code)
            reason = str(exc)[:300]
            source_row.status = SOURCE_FAILED
            # 函数内的自增随 rollback 一并回滚，这里补记本次尝试（每次调用每源仅一次）
            source_row.attempts += 1
            source_row.error_message = reason
            source_row.finished_at = utcnow()
            _mark_pending_items_failed(db, batch.id, source_code, reason)
            run_errors.append(f"{source_code}: {reason}")
            db.commit()
        finally:
            attempted_this_run.add(source_code)

    # 重新聚合批次计数并封口
    batch = _get_batch(db, batch_id)
    _recalc_batch_counts(db, batch)
    any_failed = any(row.status == SOURCE_FAILED for row in batch.sources)
    any_pending = any(row.status == SOURCE_PENDING for row in batch.sources)
    if any_failed or any_pending:
        batch.status = BATCH_PARTIAL
    else:
        batch.status = BATCH_COMPLETED
    batch.last_error = " | ".join(run_errors)[:500]
    batch.finished_at = utcnow()

    inserted_total = batch.inserted_count
    # 情感同步在入库时逐条完成；批次封口后触发爆发统计
    if not any_pending:
        batch.sentiment_synced = True
    if batch.status == BATCH_COMPLETED and inserted_total:
        try:
            detection = burst_service.run_detection(db, user, batch.brand_key, trace_id)
            batch.burst_synced = True
            batch.burst_events = len(detection["events"])
        except Exception as exc:  # noqa: BLE001 - 爆发统计失败不回滚采集结果
            db.rollback()
            batch = _get_batch(db, batch_id)
            batch.burst_synced = False
            batch.last_error = (batch.last_error + f" | burst: {exc}")[:500]
    elif batch.status == BATCH_COMPLETED:
        batch.burst_synced = True

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    audit_service.record(
        db,
        action=ACTION_COLLECT_BATCH_RUN,
        actor=user,
        entity_type="collect_batch",
        entity_id=batch.batch_no,
        detail={
            "status": batch.status,
            "inserted": batch.inserted_count,
            "duplicates": batch.duplicate_count,
            "failed": batch.failed_count,
            "run_count": batch.run_count,
            "elapsed_ms": elapsed_ms,
        },
        trace_id=trace_id,
    )
    db.commit()
    db.refresh(batch)
    return detail(db, batch.id, user)


def _process_source(db: Session, batch: CollectBatch, source_row: CollectBatchSource) -> None:
    """逐源处理。

    顺序很关键：先抓取（不产生任何写），再在 SAVEPOINT 内写台账与入库；
    抓取阶段中断时本函数不改动台账，由外层统一把 pending 条目留痕 failed。
    """
    # 网关中断：直接向上抛，不碰数据库状态
    candidates = gateway.fetch(
        brand_key=batch.brand_key,
        source_code=source_row.source_code,
        window_start=batch.window_start,
        window_end=batch.window_end,
    )

    source_row.status = SOURCE_RUNNING
    source_row.attempts += 1
    source_row.error_message = ""
    if source_row.started_at is None:
        source_row.started_at = utcnow()

    # 重试：上次失败留痕的条目重新置为待处理（成功来源不会进入本函数）
    failed_rows = db.execute(
        select(CollectBatchItem).where(
            CollectBatchItem.batch_id == batch.id,
            CollectBatchItem.source_code == source_row.source_code,
            CollectBatchItem.status == ITEM_FAILED,
        )
    ).scalars().all()
    if failed_rows:
        for row in failed_rows:
            row.status = ITEM_PENDING
            row.error_message = ""
        source_row.failed = 0
        source_row.cursor = 0
    db.flush()

    groups = {
        group.code: group
        for group in db.execute(
            select(KeywordGroup).where(KeywordGroup.brand_key == batch.brand_key)
        ).scalars().all()
    }
    candidate_index = {item["external_id"]: item for item in candidates}

    items = db.execute(
        select(CollectBatchItem)
        .where(
            CollectBatchItem.batch_id == batch.id,
            CollectBatchItem.source_code == source_row.source_code,
        )
        .order_by(CollectBatchItem.position)
    ).scalars().all()

    # 断点续跑：只处理仍处于 pending 的台账行（已 inserted/duplicate/skipped 的跳过）
    pending_items = [item for item in items if item.status == ITEM_PENDING]

    existing_ids = {row[0] for row in db.execute(select(Mention.external_id)).all()}
    existing_hashes = {
        hash_key(row[0], row[1], row[2])
        for row in db.execute(
            select(Mention.content_hash, Mention.source_code, Mention.published_at)
        ).all()
    }

    inserted = source_row.inserted
    duplicates = source_row.duplicates
    failed = source_row.failed
    skipped = source_row.skipped
    max_position = source_row.cursor

    savepoint = db.begin_nested()
    try:
        for ledger in pending_items:
            candidate = candidate_index.get(ledger.external_id)
            max_position = max(max_position, ledger.position + 1)
            if candidate is None:
                # 网关本次没返回该候选（窗口漂移等）：保守标记失败留痕
                ledger.status = ITEM_FAILED
                ledger.error_message = "来源本次未返回该候选"
                failed += 1
                continue
            group = groups.get(candidate["group_code"])
            if group is None or not group.enabled:
                ledger.status = ITEM_SKIPPED
                ledger.duplicate_reason = "group_disabled"
                skipped += 1
                continue

            key = hash_key(
                candidate["content_hash"], candidate["source_code"], candidate["published_at"]
            )
            reason = is_duplicate(
                existing_ids, existing_hashes, candidate["external_id"], key
            )
            if reason:
                ledger.status = ITEM_DUPLICATE
                ledger.duplicate_reason = reason
                duplicates += 1
                continue

            mention = Mention(
                external_id=candidate["external_id"],
                group_id=group.id,
                brand_key=group.brand_key,
                source_code=candidate["source_code"],
                title=candidate["title"],
                body=candidate["body"],
                author=candidate["author"],
                author_followers=candidate["author_followers"],
                url=candidate["url"],
                engagement=candidate["engagement"],
                published_at=candidate["published_at"],
                fetched_at=utcnow(),
                content_hash=candidate["content_hash"],
                collect_batch_id=batch.id,
            )
            db.add(mention)
            db.flush()
            result = analyze(f"{mention.title}\n{mention.body}")
            db.add(
                SentimentScore(
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
            )
            ledger.status = ITEM_INSERTED
            ledger.mention_id = mention.id
            ledger.error_message = ""
            existing_ids.add(candidate["external_id"])
            existing_hashes.add(key)
            inserted += 1
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        raise

    source_row.status = SOURCE_SUCCESS
    source_row.inserted = inserted
    source_row.duplicates = duplicates
    source_row.failed = failed
    source_row.skipped = skipped
    source_row.cursor = max_position
    source_row.error_message = ""
    source_row.finished_at = utcnow()
    db.flush()


def _mark_pending_items_failed(db: Session, batch_id, source_code: str, reason: str) -> None:
    rows = db.execute(
        select(CollectBatchItem).where(
            CollectBatchItem.batch_id == batch_id,
            CollectBatchItem.source_code == source_code,
            CollectBatchItem.status == ITEM_PENDING,
        )
    ).scalars().all()
    for row in rows:
        row.status = ITEM_FAILED
        row.error_message = reason[:300]


def _recalc_batch_counts(db: Session, batch: CollectBatch) -> None:
    """从台账重算批次四计数（唯一事实源），并回写来源行的 failed 数。"""
    rows = db.execute(
        select(CollectBatchItem.status, func.count())
        .where(CollectBatchItem.batch_id == batch.id)
        .group_by(CollectBatchItem.status)
    ).all()
    counts = {ITEM_PENDING: 0, ITEM_INSERTED: 0, ITEM_DUPLICATE: 0, ITEM_FAILED: 0, ITEM_SKIPPED: 0}
    for status, count in rows:
        counts[status] = count
    batch.total_candidates = sum(counts.values())
    batch.inserted_count = counts[ITEM_INSERTED]
    batch.duplicate_count = counts[ITEM_DUPLICATE]
    batch.failed_count = counts[ITEM_FAILED]
    batch.skipped_count = counts[ITEM_SKIPPED]

    for source_row in batch.sources:
        item_stats = dict(
            db.execute(
                select(CollectBatchItem.status, func.count())
                .where(
                    CollectBatchItem.batch_id == batch.id,
                    CollectBatchItem.source_code == source_row.source_code,
                )
                .group_by(CollectBatchItem.status)
            ).all()
        )
        source_row.inserted = item_stats.get(ITEM_INSERTED, 0)
        source_row.duplicates = item_stats.get(ITEM_DUPLICATE, 0)
        source_row.failed = item_stats.get(ITEM_FAILED, 0)
        source_row.skipped = item_stats.get(ITEM_SKIPPED, 0)
        source_row.candidates = sum(item_stats.values())
    db.flush()


# --------------------------------------------------------------- 查询/回看 ----


def _get_batch(db: Session, batch_id: str) -> CollectBatch:
    batch = db.get(CollectBatch, _to_uuid(batch_id))
    if batch is None:
        raise AppError(codes.NOT_FOUND, "补采批次不存在", f"batch_id={batch_id}")
    return batch


def _get_source_row(db: Session, batch_id, source_code: str) -> CollectBatchSource:
    row = db.execute(
        select(CollectBatchSource).where(
            CollectBatchSource.batch_id == batch_id,
            CollectBatchSource.source_code == source_code,
        )
    ).scalar_one()
    return row


def _to_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError) as exc:
        raise AppError(codes.VALIDATION_ERROR, "批次 id 不合法", str(exc)) from exc


def list_batches(db: Session, brand_scope: str | None, limit: int, offset: int) -> dict:
    stmt = select(CollectBatch).order_by(CollectBatch.created_at.desc(), CollectBatch.id.desc())
    if brand_scope:
        stmt = stmt.where(CollectBatch.brand_key == brand_scope)
    total = int(
        db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    )
    rows = db.execute(stmt.limit(limit).offset(offset)).scalars().all()
    return {"items": [_serialize_batch(row) for row in rows], "total": total, "limit": limit, "offset": offset}


def detail(db: Session, batch_id: str, user: User | None = None) -> dict:
    batch = _get_batch(db, batch_id)
    return _serialize_batch(batch, include_items=False)


def items(
    db: Session,
    batch_id: str,
    *,
    source_code: str | None = None,
    status: str | None = None,
    limit: int = 30,
    offset: int = 0,
) -> dict:
    batch = _get_batch(db, batch_id)
    stmt = select(CollectBatchItem).where(CollectBatchItem.batch_id == batch.id)
    if source_code:
        stmt = stmt.where(CollectBatchItem.source_code == source_code)
    if status:
        stmt = stmt.where(CollectBatchItem.status == status)
    total = int(
        db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    )
    rows = db.execute(
        stmt.order_by(CollectBatchItem.position).limit(limit).offset(offset)
    ).scalars().all()
    return {
        "items": [_serialize_item(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def reconciliation(db: Session, batch_id: str) -> dict:
    """对账：台账计数 vs 实际入库（mentions 表中带本批次 id 的行数）。"""
    batch = _get_batch(db, batch_id)
    ledger = dict(
        db.execute(
            select(CollectBatchItem.status, func.count())
            .where(CollectBatchItem.batch_id == batch.id)
            .group_by(CollectBatchItem.status)
        ).all()
    )
    inserted_ledger = ledger.get(ITEM_INSERTED, 0)
    inserted_in_db = int(
        db.execute(
            select(func.count(Mention.id)).where(Mention.collect_batch_id == batch.id)
        ).scalar_one()
    )
    scored_in_db = int(
        db.execute(
            select(func.count(SentimentScore.id))
            .join(Mention, Mention.id == SentimentScore.mention_id)
            .where(Mention.collect_batch_id == batch.id)
        ).scalar_one()
    )
    return {
        "batch_no": batch.batch_no,
        "ledger": {
            "pending": ledger.get(ITEM_PENDING, 0),
            "inserted": inserted_ledger,
            "duplicate": ledger.get(ITEM_DUPLICATE, 0),
            "failed": ledger.get(ITEM_FAILED, 0),
            "skipped": ledger.get(ITEM_SKIPPED, 0),
        },
        "mentions_in_db": inserted_in_db,
        "sentiment_scored_in_db": scored_in_db,
        "matched": inserted_ledger == inserted_in_db == scored_in_db,
        "closed": ledger.get(ITEM_PENDING, 0) == 0,
    }


# --------------------------------------------------------------- 序列化 ----


def _serialize_batch(batch: CollectBatch, *, include_items: bool = False) -> dict:
    pending = batch.total_candidates - (
        batch.inserted_count + batch.duplicate_count + batch.failed_count + batch.skipped_count
    )
    payload = {
        "id": str(batch.id),
        "batch_no": batch.batch_no,
        "brand_key": batch.brand_key,
        "brand_label": BRAND_LABELS.get(batch.brand_key, batch.brand_key),
        "window_start": batch.window_start.isoformat(),
        "window_end": batch.window_end.isoformat(),
        "status": batch.status,
        "status_label": BATCH_STATUS_LABELS.get(batch.status, batch.status),
        "counts": {
            "pending": max(0, pending),
            "inserted": batch.inserted_count,
            "duplicate": batch.duplicate_count,
            "failed": batch.failed_count,
            "skipped": batch.skipped_count,
            "total": batch.total_candidates,
        },
        "sentiment_synced": bool(batch.sentiment_synced),
        "burst_synced": bool(batch.burst_synced),
        "burst_events": batch.burst_events,
        "run_count": batch.run_count,
        "last_error": batch.last_error,
        "created_by_email": batch.created_by_email,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "finished_at": batch.finished_at.isoformat() if batch.finished_at else None,
        "sources": [_serialize_source(row) for row in batch.sources],
    }
    if include_items:
        payload["items"] = [_serialize_item(row) for row in batch.items]
    return payload


def _serialize_source(row: CollectBatchSource) -> dict:
    pending = row.candidates - (row.inserted + row.duplicates + row.failed + row.skipped)
    return {
        "id": str(row.id),
        "source_code": row.source_code,
        "source_label": SOURCE_LABELS.get(row.source_code, row.source_code),
        "position": row.position,
        "status": row.status,
        "status_label": SOURCE_STATUS_LABELS.get(row.status, row.status),
        "counts": {
            "pending": max(0, pending),
            "inserted": row.inserted,
            "duplicate": row.duplicates,
            "failed": row.failed,
            "skipped": row.skipped,
            "total": row.candidates,
        },
        "cursor": row.cursor,
        "attempts": row.attempts,
        "error_message": row.error_message,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
    }


def _serialize_item(row: CollectBatchItem) -> dict:
    return {
        "id": str(row.id),
        "source_code": row.source_code,
        "source_label": SOURCE_LABELS.get(row.source_code, row.source_code),
        "position": row.position,
        "external_id": row.external_id,
        "group_code": row.group_code,
        "title": row.title,
        "published_at": row.published_at.isoformat(),
        "status": row.status,
        "status_label": {
            ITEM_PENDING: "待处理",
            ITEM_INSERTED: "已入库",
            ITEM_DUPLICATE: "重复",
            ITEM_FAILED: "失败",
            ITEM_SKIPPED: "不适用",
        }.get(row.status, row.status),
        "duplicate_reason": row.duplicate_reason,
        "mention_id": str(row.mention_id) if row.mention_id else None,
        "error_message": row.error_message,
    }
