"""add personalized academic qc job metadata

Revision ID: add_personalized_academic_qc_jobs
Revises: <HOST_WILL_FILL>
Create Date: 2026-09-16

这是迁移草稿。宿主接入时请替换 down_revision，并按现有 Alembic
命名、用户表和时区规范调整外键及时间字段。
"""

from alembic import op
import sqlalchemy as sa


revision = 'add_personalized_academic_qc_jobs'
down_revision = '<HOST_WILL_FILL>'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'personalized_academic_qc_jobs',
        sa.Column('id', sa.String(length=32), primary_key=True),
        sa.Column('business_type', sa.String(length=16), nullable=False),
        sa.Column('qc_month', sa.String(length=7), nullable=False),
        sa.Column('selected_department', sa.String(length=128), nullable=False),
        sa.Column('schedule_type', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('classinfo_mode', sa.String(length=32), nullable=False),
        sa.Column('output_uri', sa.String(length=512), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index(
        'ix_personalized_academic_qc_jobs_created_by',
        'personalized_academic_qc_jobs',
        ['created_by'],
    )
    op.create_index(
        'ix_personalized_academic_qc_jobs_status_created_at',
        'personalized_academic_qc_jobs',
        ['status', 'created_at'],
    )


def downgrade():
    op.drop_index(
        'ix_personalized_academic_qc_jobs_status_created_at',
        table_name='personalized_academic_qc_jobs',
    )
    op.drop_index(
        'ix_personalized_academic_qc_jobs_created_by',
        table_name='personalized_academic_qc_jobs',
    )
    op.drop_table('personalized_academic_qc_jobs')
