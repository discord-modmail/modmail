"""Add messages table

Revision ID: e6b20ed26bc2
Revises:
Create Date: 2021-08-28 17:01:24.449928

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e6b20ed26bc2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("mirrored_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("messages")
