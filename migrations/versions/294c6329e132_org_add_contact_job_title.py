"""
org_add_contact_job_title

Revision ID: 294c6329e132
Revises: 68bfaf39538c
Create Date: 2025-08-29 06:02:49.980040
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "294c6329e132"
down_revision = "68bfaf39538c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "organization",
        sa.Column("contact_job_title", sa.String(length=100), nullable=True),
    )
    op.execute("UPDATE organization SET contact_job_title = 'N/A'")
    op.alter_column("organization", "contact_job_title", nullable=False)


def downgrade():
    op.drop_column("organization", "contact_job_title")
