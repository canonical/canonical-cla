"""
Update audit logs to be flexible

Revision ID: c5036babd7c2
Revises: 64142e7e6183
Create Date: 2026-02-10 13:21:04.426338
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c5036babd7c2"
down_revision = "64142e7e6183"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "audit_log",
        "entity_type",
        existing_type=sa.VARCHAR(length=12),
        type_=sa.Enum(
            "INDIVIDUAL",
            "ORGANIZATION",
            "USER_ROLE",
            "EXCLUDED_PROJECT",
            name="auditentitytype",
            native_enum=False,
        ),
        existing_nullable=False,
    )

    op.alter_column(
        "audit_log",
        "action",
        existing_type=sa.VARCHAR(length=6),
        type_=sa.String(length=100),
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
            name="auditentitytype",
            native_enum=False,
        ),
        type_=sa.VARCHAR(length=24),
        existing_nullable=False,
    )
    op.alter_column(
        "audit_log",
        "action",
        existing_type=sa.String(length=100),
        type_=sa.VARCHAR(length=6),
        existing_nullable=False,
    )
