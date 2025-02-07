"""
ind-remove-unique-email

Revision ID: 47c1575bd0b8
Revises: 96981c2665a1
Create Date: 2025-02-07 16:54:17.342229
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "47c1575bd0b8"
down_revision = "96981c2665a1"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("individual_github_email_key", "individual", type_="unique")
    op.drop_constraint("individual_launchpad_email_key", "individual", type_="unique")


def downgrade():
    op.create_unique_constraint(
        "individual_launchpad_email_key", "individual", ["launchpad_email"]
    )
    op.create_unique_constraint(
        "individual_github_email_key", "individual", ["github_email"]
    )
