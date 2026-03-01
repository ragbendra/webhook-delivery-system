"""add next_attempt_at to deliveries

Revision ID: 20260301_04
Revises: 20260228_03
Create Date: 2026-03-01 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260301_04"
down_revision: Union[str, None] = "20260228_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deliveries", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_deliveries_next_attempt_at"), "deliveries", ["next_attempt_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_deliveries_next_attempt_at"), table_name="deliveries")
    op.drop_column("deliveries", "next_attempt_at")
