"""add visual metadata, genres, and favourites to bookmarks"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bookmarks", sa.Column("site_name", sa.String(), nullable=True))
    op.add_column("bookmarks", sa.Column("logo_url", sa.String(), nullable=True))
    op.add_column("bookmarks", sa.Column("image_url", sa.String(), nullable=True))
    op.add_column("bookmarks", sa.Column("excerpt", sa.Text(), nullable=True))
    op.add_column("bookmarks", sa.Column("genres", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("bookmarks", sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    for column in ("is_favorite", "genres", "excerpt", "image_url", "logo_url", "site_name"):
        op.drop_column("bookmarks", column)
