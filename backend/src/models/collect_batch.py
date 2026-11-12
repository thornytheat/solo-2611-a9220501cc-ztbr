"""CollectBatch：可跟踪的补采批次（实体 5）。

一个批次 = 品牌 × 来源集合 × 发布时间段。批次内按来源逐个处理，
每个来源一行 checkpoint（CollectBatchSource），中断后凭状态断点续跑。

批次状态机：
    pending → running → completed（全部来源成功）
                         └→ partial（至少一个来源失败，可重试失败来源）
    重试只处理 failed 来源；全部来源终态（success/failed）后批次封口。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.settings import settings
from src.models.base import Base, TimestampMixin, new_uuid, utcnow

# 批次级状态
BATCH_PENDING = "pending"
BATCH_RUNNING = "running"
BATCH_COMPLETED = "completed"
BATCH_PARTIAL = "partial"

BATCH_STATUSES: tuple[str, ...] = (BATCH_PENDING, BATCH_RUNNING, BATCH_COMPLETED, BATCH_PARTIAL)
BATCH_FINAL_STATUSES: tuple[str, ...] = (BATCH_COMPLETED, BATCH_PARTIAL)

# 来源行状态（断点）
SOURCE_PENDING = "pending"
SOURCE_RUNNING = "running"
SOURCE_SUCCESS = "success"
SOURCE_FAILED = "failed"

SOURCE_STATUSES: tuple[str, ...] = (SOURCE_PENDING, SOURCE_RUNNING, SOURCE_SUCCESS, SOURCE_FAILED)
# 只有 success 是不可重放的终态；failed 是可重试断点，必须留在续跑选择集内
SOURCE_FINAL_STATUSES: tuple[str, ...] = (SOURCE_SUCCESS,)

# 条目处理结果
ITEM_PENDING = "pending"
ITEM_INSERTED = "inserted"
ITEM_DUPLICATE = "duplicate"
ITEM_FAILED = "failed"
ITEM_SKIPPED = "skipped"

BATCH_STATUS_LABELS: dict[str, str] = {
    BATCH_PENDING: "待处理",
    BATCH_RUNNING: "处理中",
    BATCH_COMPLETED: "已完成",
    BATCH_PARTIAL: "部分失败",
}

SOURCE_STATUS_LABELS: dict[str, str] = {
    SOURCE_PENDING: "待处理",
    SOURCE_RUNNING: "处理中",
    SOURCE_SUCCESS: "已完成",
    SOURCE_FAILED: "失败",
}

ITEM_STATUS_LABELS: dict[str, str] = {
    ITEM_PENDING: "待处理",
    ITEM_INSERTED: "已入库",
    ITEM_DUPLICATE: "重复",
    ITEM_FAILED: "失败",
    ITEM_SKIPPED: "不适用",
}


class CollectBatch(Base, TimestampMixin):
    __tablename__ = "collect_batches"
    __table_args__ = {"schema": settings.db_schema}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    batch_no: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    brand_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=BATCH_PENDING, index=True)
    # 候选口径（创建时快照），页面「待处理」初始值来源
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 本批次新提及是否已同步情感打分 / 爆发统计
    sentiment_synced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    burst_synced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    burst_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sources: Mapped[list["CollectBatchSource"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="CollectBatchSource.position",
        lazy="selectin",
    )
    items: Mapped[list["CollectBatchItem"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="CollectBatchItem.position",
        lazy="selectin",
    )


class CollectBatchSource(Base):
    __tablename__ = "collect_batch_sources"
    __table_args__ = (
        # 同批次内来源唯一：重试时复用同一行，天然幂等
        UniqueConstraint("batch_id", "source_code", name="uq_batch_source"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.collect_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_code: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=SOURCE_PENDING, index=True)
    candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 断点：已处理到的候选下标（不含），续跑从 cursor 开始
    cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    batch: Mapped[CollectBatch] = relationship(back_populates="sources")


class CollectBatchItem(Base):
    """逐候选台账：页面数字与入库明细对账的依据（一条候选一行，幂等键唯一）。"""

    __tablename__ = "collect_batch_items"
    __table_args__ = (
        UniqueConstraint("batch_id", "external_id", name="uq_batch_item_external"),
        {"schema": settings.db_schema},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.db_schema}.collect_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_code: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_id: Mapped[str] = mapped_column(String(96), nullable=False)
    group_code: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=ITEM_PENDING, index=True)
    duplicate_reason: Mapped[str] = mapped_column(String(24), nullable=False, default="")
    mention_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    batch: Mapped[CollectBatch] = relationship(back_populates="items")
