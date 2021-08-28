"""Add configurations table

Revision ID: 72459556f7b9
Revises: 7b384834cca4
Create Date: 2021-08-28 17:02:36.726948

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "72459556f7b9"
down_revision = "7b384834cca4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "configurations",
        sa.Column("server_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=True),
        sa.Column("config_key", sa.String(), nullable=False),
        sa.Column("config_value", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("server_id"),
    )


def downgrade():
    op.drop_table("configurations")
