"""
Add audit_log table

Revision ID: 9523669572c8
Revises: 5b6373e08cac
Create Date: 2024-08-16 06:24:03.376164
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9523669572c8"
down_revision = "5b6373e08cac"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("SIGN", "REVOKE", "UPDATE", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "entity_type",
            sa.Enum("INDIVIDUAL", "ORGANIZATION", native_enum=False),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("audit_log")
