"""Add brand planner fields to content_plans

Revision ID: b5e9f2a1c3d4
Revises: 4a0e3b03ab4c
Create Date: 2026-02-05 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5e9f2a1c3d4'
down_revision: Union[str, Sequence[str], None] = '4a0e3b03ab4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Brand Planner fields to content_plans table."""
    # Add new columns for Brand Planner (Phase 4)
    op.add_column('content_plans', sa.Column('game', sa.String(length=30), nullable=True))
    op.add_column('content_plans', sa.Column('hook_type', sa.String(length=30), nullable=True))
    op.add_column('content_plans', sa.Column('core_insight', sa.Text(), nullable=True))
    op.add_column('content_plans', sa.Column('context_summary', sa.Text(), nullable=True))
    op.add_column('content_plans', sa.Column('structure_preview', sa.Text(), nullable=True))
    op.add_column('content_plans', sa.Column('rationale', sa.Text(), nullable=True))
    op.add_column('content_plans', sa.Column('source_theme', sa.String(length=255), nullable=True))
    op.add_column('content_plans', sa.Column('audience_value', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Remove Brand Planner fields from content_plans table."""
    op.drop_column('content_plans', 'audience_value')
    op.drop_column('content_plans', 'source_theme')
    op.drop_column('content_plans', 'rationale')
    op.drop_column('content_plans', 'structure_preview')
    op.drop_column('content_plans', 'context_summary')
    op.drop_column('content_plans', 'core_insight')
    op.drop_column('content_plans', 'hook_type')
    op.drop_column('content_plans', 'game')
