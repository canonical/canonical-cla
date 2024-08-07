"""Added Revocation table

Revision ID: bb95a72f0238
Revises: 220d3b676fc1
Create Date: 2024-08-05 14:35:23.247066

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bb95a72f0238"
down_revision = "220d3b676fc1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revocation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("individual_id", sa.Integer(), nullable=False),
        sa.Column("date_revoked", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["individual_id"],
            ["individual.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("revocation")
