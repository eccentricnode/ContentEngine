"""Add job_queue table for SQLite-based job scheduling

Revision ID: c7f8a9b0d1e2
Revises: b5e9f2a1c3d4
Create Date: 2026-02-05 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f8a9b0d1e2'
down_revision: Union[str, Sequence[str], None] = 'b5e9f2a1c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create job_queue table."""
    op.create_table(
        'job_queue',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_type', sa.Enum('POST_TO_LINKEDIN', 'POST_TO_TWITTER', 'POST_TO_BLOG', name='jobtype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', name='jobstatus'), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True, default=0),
        sa.Column('attempts', sa.Integer(), nullable=True, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=True, default=3),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('source_file', sa.String(length=512), nullable=True),
        sa.Column('source_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    op.create_index('ix_job_queue_status', 'job_queue', ['status'], unique=False)
    op.create_index('ix_job_queue_scheduled_at', 'job_queue', ['scheduled_at'], unique=False)
    op.create_index('ix_job_queue_source_file', 'job_queue', ['source_file'], unique=False)


def downgrade() -> None:
    """Drop job_queue table."""
    op.drop_index('ix_job_queue_source_file', table_name='job_queue')
    op.drop_index('ix_job_queue_scheduled_at', table_name='job_queue')
    op.drop_index('ix_job_queue_status', table_name='job_queue')
    op.drop_table('job_queue')
