"""add_site_profiles

Revision ID: 0007_add_site_profiles
Revises: 0006_add_chat_requests
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0007_add_site_profiles'
down_revision: Union[str, None] = 'c11c8ddca4bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'site_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('label', sa.String(128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=False, index=True),
        sa.Column('config', postgresql.JSONB(), nullable=False, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('site_profiles')
