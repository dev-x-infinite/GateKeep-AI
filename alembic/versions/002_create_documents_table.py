"""create documents table

Revision ID: 002_create_documents
Revises: 001_create_users
Create Date: 2026-11-25 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_create_documents'
down_revision: Union[str, None] = '001_create_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='processing', nullable=False),
        sa.Column('chunk_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_table('documents')
