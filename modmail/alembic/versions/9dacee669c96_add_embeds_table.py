"""Add embeds table

Revision ID: 9dacee669c96
Revises: 500f4263ffe9
Create Date: 2021-08-28 17:02:06.180093

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "9dacee669c96"
down_revision = "500f4263ffe9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "embeds",
        sa.Column("internal_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("json_content", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
        ),
        sa.PrimaryKeyConstraint("internal_id"),
    )


def downgrade():
    op.drop_table("embeds")
