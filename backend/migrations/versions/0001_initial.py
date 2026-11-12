"""initial schema（users / keyword_groups / mentions / sentiment_scores / burst_alerts / audit_logs）

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-12

演示环境由 `scripts/bootstrap_db.py` 用同一份 metadata 建表；本迁移供正式环境执行
`alembic upgrade head`，两者建出的表结构一致（同一 Base.metadata）。
"""
from __future__ import annotations

from alembic import op

from src.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
