"""补采批次：collect_batches / collect_batch_sources / collect_batch_items + mentions.collect_batch_id

Revision ID: 0002_collect_batch
Revises: 0001_initial
Create Date: 2026-11-12

幂等说明：0001_initial 用 Base.metadata.create_all 建表，新库执行到本迁移时
新表可能已随 metadata 建好；因此每步都先查 information_schema / pg_indexes，
存在则跳过，使 `alembic upgrade head` 与 bootstrap_db.py 的 create_all 两种路径
最终结构一致、互不冲突。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.config.settings import settings

revision = "0002_collect_batch"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

SCHEMA = settings.db_schema


def _table_exists(bind, name: str) -> bool:
    row = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = :schema AND table_name = :table"
        ),
        {"schema": SCHEMA, "table": name},
    ).first()
    return row is not None


def _column_exists(bind, table: str, column: str) -> bool:
    row = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table AND column_name = :column"
        ),
        {"schema": SCHEMA, "table": table, "column": column},
    ).first()
    return row is not None


def _index_exists(bind, name: str) -> bool:
    row = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE schemaname = :schema AND indexname = :name"),
        {"schema": SCHEMA, "name": name},
    ).first()
    return row is not None


def _create_index(bind, name: str, table: str, columns: list[str]) -> None:
    if _index_exists(bind, name):
        return
    op.create_index(name, table, columns, schema=SCHEMA)


def upgrade() -> None:
    bind = op.get_bind()

    # mentions.collect_batch_id
    if not _column_exists(bind, "mentions", "collect_batch_id"):
        op.add_column(
            "mentions",
            sa.Column("collect_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
            schema=SCHEMA,
        )
    _create_index(bind, "ix_mentions_collect_batch_id", "mentions", ["collect_batch_id"])

    if _table_exists(bind, "collect_batches"):
        # 新库已由 create_all 建出三张批次表，补齐可能缺失的索引后即可
        _create_index(bind, "ix_collect_batches_batch_no", "collect_batches", ["batch_no"])
        _create_index(bind, "ix_collect_batches_brand_key", "collect_batches", ["brand_key"])
        _create_index(bind, "ix_collect_batches_status", "collect_batches", ["status"])
        _create_index(bind, "ix_collect_batch_sources_batch_id", "collect_batch_sources", ["batch_id"])
        _create_index(bind, "ix_collect_batch_sources_source_code", "collect_batch_sources", ["source_code"])
        _create_index(bind, "ix_collect_batch_sources_status", "collect_batch_sources", ["status"])
        _create_index(bind, "ix_collect_batch_items_batch_id", "collect_batch_items", ["batch_id"])
        _create_index(bind, "ix_collect_batch_items_source_code", "collect_batch_items", ["source_code"])
        _create_index(bind, "ix_collect_batch_items_status", "collect_batch_items", ["status"])
        return

    op.create_table(
        "collect_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_no", sa.String(length=24), nullable=False),
        sa.Column("brand_key", sa.String(length=32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("total_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sentiment_synced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("burst_synced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("burst_events", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_email", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_no", name="uq_collect_batches_batch_no"),
        schema=SCHEMA,
    )
    _create_index(bind, "ix_collect_batches_batch_no", "collect_batches", ["batch_no"])
    _create_index(bind, "ix_collect_batches_brand_key", "collect_batches", ["brand_key"])
    _create_index(bind, "ix_collect_batches_status", "collect_batches", ["status"])

    op.create_table(
        "collect_batch_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.collect_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_code", sa.String(length=24), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cursor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_id", "source_code", name="uq_batch_source"),
        schema=SCHEMA,
    )
    _create_index(bind, "ix_collect_batch_sources_batch_id", "collect_batch_sources", ["batch_id"])
    _create_index(bind, "ix_collect_batch_sources_source_code", "collect_batch_sources", ["source_code"])
    _create_index(bind, "ix_collect_batch_sources_status", "collect_batch_sources", ["status"])

    op.create_table(
        "collect_batch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.collect_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_code", sa.String(length=24), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_id", sa.String(length=96), nullable=False),
        sa.Column("group_code", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("duplicate_reason", sa.String(length=24), nullable=False, server_default=""),
        sa.Column("mention_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_id", "external_id", name="uq_batch_item_external"),
        schema=SCHEMA,
    )
    _create_index(bind, "ix_collect_batch_items_batch_id", "collect_batch_items", ["batch_id"])
    _create_index(bind, "ix_collect_batch_items_source_code", "collect_batch_items", ["source_code"])
    _create_index(bind, "ix_collect_batch_items_status", "collect_batch_items", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("collect_batch_items", "collect_batch_sources", "collect_batches"):
        if _table_exists(bind, table):
            op.drop_table(table, schema=SCHEMA)
    if _index_exists(bind, "ix_mentions_collect_batch_id"):
        op.drop_index("ix_mentions_collect_batch_id", table_name="mentions", schema=SCHEMA)
    if _column_exists(bind, "mentions", "collect_batch_id"):
        op.drop_column("mentions", "collect_batch_id", schema=SCHEMA)
