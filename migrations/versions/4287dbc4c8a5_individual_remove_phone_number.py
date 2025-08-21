"""
individual-remove-phone-number

Revision ID: 4287dbc4c8a5
Revises: 47c1575bd0b8
Create Date: 2025-08-21 14:48:36.916704
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4287dbc4c8a5"
down_revision = "47c1575bd0b8"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("specs")
    op.drop_column("individual", "phone_number")


def downgrade():
    op.add_column(
        "individual",
        sa.Column(
            "phone_number", sa.VARCHAR(length=20), autoincrement=False, nullable=False
        ),
    )
    op.create_table(
        "specs",
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("title", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("status", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "authors", postgresql.ARRAY(sa.TEXT()), autoincrement=False, nullable=True
        ),
        sa.Column("spec_type", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("team", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("google_doc_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("google_doc_name", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("google_doc_url", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "google_doc_created_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "google_doc_updated_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "synced_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="specs_pkey"),
    )
