"""
ind_remove_phone_number

Revision ID: 68bfaf39538c
Revises: 47c1575bd0b8
Create Date: 2025-08-22 11:35:17.704461
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '68bfaf39538c'
down_revision = '47c1575bd0b8'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('individual', 'phone_number')


def downgrade():
    op.add_column('individual', sa.Column('phone_number', sa.VARCHAR(
        length=20), autoincrement=False, nullable=False))
