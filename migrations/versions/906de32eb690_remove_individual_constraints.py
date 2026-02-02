"""
Remove unique constraints on individual table

Revision ID: 906de32eb690
Revises: 9523669572c8
Create Date: 2024-09-23 12:40:22.723260
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "906de32eb690"
down_revision = "9523669572c8"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("individual_github_account_id_key", "individual", type_="unique")
    op.drop_constraint(
        "individual_launchpad_account_id_key", "individual", type_="unique"
    )


def downgrade():
    op.create_unique_constraint(
        "individual_launchpad_account_id_key", "individual", ["launchpad_account_id"]
    )
    op.create_unique_constraint(
        "individual_github_account_id_key", "individual", ["github_account_id"]
    )
