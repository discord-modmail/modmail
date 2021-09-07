"""Add attachments table

Revision ID: 8d52443a026e
Revises: 9dacee669c96
Create Date: 2021-08-28 17:02:15.788101

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "8d52443a026e"
down_revision = "9dacee669c96"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attachments",
        sa.Column("internal_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("link", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
        ),
        sa.PrimaryKeyConstraint("internal_id"),
    )


def downgrade():
    op.drop_table("attachments")
