"""
org-drop-docusign-field

Revision ID: 96981c2665a1
Revises: ead9f37787a3
Create Date: 2024-12-18 15:53:37.175418
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "96981c2665a1"
down_revision = "ead9f37787a3"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("organization", "docusign_url")


def downgrade():
    op.add_column(
        "organization",
        sa.Column(
            "docusign_url", sa.VARCHAR(length=255), autoincrement=False, nullable=True
        ),
    )
