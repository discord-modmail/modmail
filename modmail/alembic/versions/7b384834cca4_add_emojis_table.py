"""Add emojis table

Revision ID: 7b384834cca4
Revises: 8d52443a026e
Create Date: 2021-08-28 17:02:30.226745

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7b384834cca4"
down_revision = "8d52443a026e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "emojis",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("animated", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("emojis")
