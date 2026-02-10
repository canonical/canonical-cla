"""
Create user role table

Revision ID: b254304ff9b9
Revises: 294c6329e132
Create Date: 2026-02-09 13:13:03.203079
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b254304ff9b9"
down_revision = "294c6329e132"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "community_manager",
                "legal_counsel",
                name="role",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_role_email"), "user_role", ["email"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_user_role_email"), table_name="user_role")
    op.drop_table("user_role")
