"""Added Individual table

Revision ID: b74c5276fc63
Revises: 
Create Date: 2024-08-05 02:58:21.446586

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "b74c5276fc63"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "individual",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("last_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("phone_number", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("address", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("country", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("github_username", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("github_account_id", sa.Integer(), nullable=False),
        sa.Column("github_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "launchpad_username", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "launchpad_account_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("launchpad_email", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_email"),
        sa.UniqueConstraint("github_username"),
        sa.UniqueConstraint("launchpad_email"),
        sa.UniqueConstraint("launchpad_username"),
    )


def downgrade() -> None:
    op.drop_table("individual")
