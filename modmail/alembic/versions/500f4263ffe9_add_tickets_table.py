"""Add tickets table

Revision ID: 500f4263ffe9
Revises: e6b20ed26bc2
Create Date: 2021-08-28 17:01:39.611060

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "500f4263ffe9"
down_revision = "e6b20ed26bc2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("server_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("creater_id", sa.BigInteger(), nullable=False),
        sa.Column("creating_message_id", sa.BigInteger(), nullable=False),
        sa.Column("creating_channel_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("tickets")
