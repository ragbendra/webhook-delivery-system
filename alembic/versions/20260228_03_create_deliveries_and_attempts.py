"""create deliveries and delivery attempts tables

Revision ID: 20260228_03
Revises: 20260228_02
Create Date: 2026-02-28 23:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260228_03"
down_revision: Union[str, None] = "20260228_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("webhook_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "success", "permanently_failed", name="delivery_status"),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deliveries_webhook_id"), "deliveries", ["webhook_id"], unique=False)
    op.create_index(op.f("ix_deliveries_event_type"), "deliveries", ["event_type"], unique=False)

    op.create_table(
        "delivery_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("delivery_id", sa.String(length=36), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.String(length=500), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["delivery_id"], ["deliveries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_delivery_attempts_delivery_id"),
        "delivery_attempts",
        ["delivery_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_delivery_attempts_delivery_id"), table_name="delivery_attempts")
    op.drop_table("delivery_attempts")

    op.drop_index(op.f("ix_deliveries_event_type"), table_name="deliveries")
    op.drop_index(op.f("ix_deliveries_webhook_id"), table_name="deliveries")
    op.drop_table("deliveries")
