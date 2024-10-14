"""
Add autdit log ip address

Revision ID: ead9f37787a3
Revises: 906de32eb690
Create Date: 2024-10-14 19:31:15.624272
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ead9f37787a3"
down_revision = "906de32eb690"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "audit_log", sa.Column("ip_address", sa.String(length=50), nullable=False)
    )


def downgrade():
    op.drop_column("audit_log", "ip_address")
