# -*- coding: utf-8 -*-
"""Add login status columns to users table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20230825_01_add_user_login_columns"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('is_online', sa.Boolean(), nullable=False, server_default=sa.text('0')))

def downgrade() -> None:
    op.drop_column('users', 'is_online')
    op.drop_column('users', 'last_login')
