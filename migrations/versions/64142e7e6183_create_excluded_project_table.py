"""
Create excluded project table

Revision ID: 64142e7e6183
Revises: 05d07809911e
Create Date: 2026-02-10 13:19:13.600740
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "64142e7e6183"
down_revision = "05d07809911e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "excluded_project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "platform",
            sa.Enum("github", "launchpad", name="projectplatform", native_enum=False),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_excluded_project_platform_full_name",
        "excluded_project",
        ["platform", "full_name"],
        unique=True,
    )


def downgrade():
    op.drop_table("excluded_project")
