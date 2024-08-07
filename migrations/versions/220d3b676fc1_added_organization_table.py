"""Added Organization table

Revision ID: 220d3b676fc1
Revises: b74c5276fc63
Create Date: 2024-08-05 14:32:44.146025

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "220d3b676fc1"
down_revision = "b74c5276fc63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("email_hostname", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("contact_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("phone_number", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("address", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("country", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("salesforce_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("organization")
