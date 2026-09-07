"""add funding_programs table

Revision ID: f8a1b2c3d4e5
Revises: e5f6a7b8c9d0
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "funding_programs",
        sa.Column("program_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("stage", sa.String(length=80), nullable=True),
        sa.Column("eligibility_json", sa.JSON(), nullable=True),
        sa.Column("open_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("max_amount", sa.Integer(), nullable=True),
        sa.Column("support_amount_text", sa.String(length=160), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("program_id"),
    )
    op.create_index("ix_funding_programs_deadline", "funding_programs", ["deadline"])
    op.create_index("ix_funding_programs_region", "funding_programs", ["region"])
    op.create_index("ix_funding_programs_stage", "funding_programs", ["stage"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_funding_programs_stage", table_name="funding_programs")
    op.drop_index("ix_funding_programs_region", table_name="funding_programs")
    op.drop_index("ix_funding_programs_deadline", table_name="funding_programs")
    op.drop_table("funding_programs")
