"""add proposal_field_definitions and proposal_template_field_map tables

Revision ID: b1e9a4c7f052
Revises: e5f6a7b8c9d0
Create Date: 2026-09-07 00:00:00.000000

제안서 자동 작성 기능(이슈 #102, docs/제안서_자동작성_API_명세서.md §3)의 고정 참조
테이블 2종. data_difficulty/collection_difficulty와 동일하게 오프라인에서 시딩하고
런타임(app/api/proposals.py)이 조회만 한다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1e9a4c7f052'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'proposal_field_definitions',
        sa.Column('field_key', sa.String(length=80), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('field_type', sa.String(length=20), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('field_key'),
    )
    op.create_table(
        'proposal_template_field_map',
        sa.Column('template_type', sa.String(length=20), nullable=False),
        sa.Column('field_key', sa.String(length=80), nullable=False),
        sa.Column('requirement', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['field_key'], ['proposal_field_definitions.field_key'], ),
        sa.PrimaryKeyConstraint('template_type', 'field_key'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('proposal_template_field_map')
    op.drop_table('proposal_field_definitions')
