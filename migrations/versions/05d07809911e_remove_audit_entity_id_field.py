"""
Remove audit entity id field

Revision ID: 05d07809911e
Revises: b254304ff9b9
Create Date: 2026-02-09 17:31:17.139272
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "05d07809911e"
down_revision = "b254304ff9b9"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("audit_log", "entity_id")


def downgrade():
    op.add_column(
        "audit_log",
        sa.Column("entity_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )
