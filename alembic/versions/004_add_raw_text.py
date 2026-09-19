"""store the original extracted text for semantic chunking

Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contents", sa.Column("raw_text", sa.Text(), nullable=True))
    op.execute("UPDATE contents SET raw_text = body WHERE raw_text IS NULL")


def downgrade() -> None:
    op.drop_column("contents", "raw_text")
