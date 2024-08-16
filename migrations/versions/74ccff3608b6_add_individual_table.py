"""
Add individual table

Revision ID: 74ccff3608b6
Revises: 
Create Date: 2024-08-15 23:00:50.452540
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "74ccff3608b6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "individual",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=50), nullable=False),
        sa.Column("last_name", sa.String(length=50), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("address", sa.String(length=400), nullable=False),
        sa.Column("country", sa.String(length=50), nullable=False),
        sa.Column("github_username", sa.String(length=100), nullable=True),
        sa.Column("github_account_id", sa.Integer(), nullable=True),
        sa.Column("github_email", sa.String(length=100), nullable=True),
        sa.Column("launchpad_username", sa.String(length=100), nullable=True),
        sa.Column("launchpad_account_id", sa.String(length=100), nullable=True),
        sa.Column("launchpad_email", sa.String(length=100), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_account_id"),
        sa.UniqueConstraint("github_email"),
        sa.UniqueConstraint("launchpad_account_id"),
        sa.UniqueConstraint("launchpad_email"),
    )


def downgrade():
    op.drop_table("individual")
