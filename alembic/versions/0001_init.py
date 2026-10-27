"""init tables and seed tariffs

Revision ID: 0001
Revises:
Create Date: 2026-01-01

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=32), nullable=False, unique=True),
        sa.Column("price", sa.BigInteger(), nullable=False),
    )

    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("tariff_id", sa.Integer(), sa.ForeignKey("tariffs.id"), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("discount", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("installment_months", sa.Integer(), nullable=True),
        sa.Column("schedule", JSONB(), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # partial unique index: уникальность только для не-NULL ключей
    op.create_index(
        "ux_payments_idempotency_key",
        "payments",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index("ix_payments_email", "payments", ["email"])
    op.create_index("ix_payments_status", "payments", ["status"])

    # seed tariffs
    op.bulk_insert(
        sa.table(
            "tariffs",
            sa.column("id", sa.Integer),
            sa.column("title", sa.String),
            sa.column("price", sa.BigInteger),
        ),
        [
            {"id": 1, "title": "basic", "price": 990_000},
            {"id": 2, "title": "standard", "price": 1_990_000},
            {"id": 3, "title": "premium", "price": 2_990_000},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_email", table_name="payments")
    op.drop_index("ux_payments_idempotency_key", table_name="payments")
    op.drop_table("payments")
    op.drop_table("tariffs")