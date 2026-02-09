"""
Create excluded project table

Revision ID: 8086b895ce22
Revises: 05d07809911e
Create Date: 2026-02-09 18:14:19.030288
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8086b895ce22"
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
    op.alter_column(
        "audit_log",
        "entity_type",
        existing_type=sa.VARCHAR(length=12),
        type_=sa.Enum(
            "INDIVIDUAL",
            "ORGANIZATION",
            "USER_ROLE",
            "EXCLUDED_PROJECT",
            native_enum=False,
        ),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "audit_log",
        "entity_type",
        existing_type=sa.Enum(
            "INDIVIDUAL",
            "ORGANIZATION",
            "USER_ROLE",
            "EXCLUDED_PROJECT",
            native_enum=False,
        ),
        type_=sa.VARCHAR(length=12),
        existing_nullable=False,
    )
    op.drop_table("excluded_project")
