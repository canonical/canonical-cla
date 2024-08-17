"""
Add organization table

Revision ID: 5b6373e08cac
Revises: 74ccff3608b6
Create Date: 2024-08-16 06:23:43.260420
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5b6373e08cac"
down_revision = "74ccff3608b6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organization",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email_domain", sa.String(length=100), nullable=False),
        sa.Column("contact_name", sa.String(length=100), nullable=False),
        sa.Column("contact_email", sa.String(length=100), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=400), nullable=True),
        sa.Column("country", sa.String(length=50), nullable=False),
        sa.Column("salesforce_url", sa.String(length=255), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_domain"),
    )


def downgrade():
    op.drop_table("organization")
