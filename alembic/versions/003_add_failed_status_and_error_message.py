"""add failed status and error_message to bookmarks

Revision ID: 003
Revises: 002
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add 'failed' to the bookmarkstatus enum
    op.execute("ALTER TYPE bookmarkstatus ADD VALUE 'failed'")
    
    # Add error_message column to bookmarks table
    op.add_column('bookmarks', sa.Column('error_message', sa.Text(), nullable=True))

def downgrade() -> None:
    # Remove error_message column
    op.drop_column('bookmarks', 'error_message')
    
    # Remove 'failed' from the enum (requires recreating the enum without 'failed')
    # This is a bit tricky because we cannot directly remove an enum value in PostgreSQL.
    # We'll create a new enum, migrate data, and drop the old one.
    op.execute("ALTER TABLE bookmarks ALTER COLUMN status DROP DEFAULT")
    op.execute("UPDATE bookmarks SET status = 'unread' WHERE status = 'failed'")
    op.execute("CREATE TYPE bookmarkstatus_new AS ENUM ('unread', 'read', 'archived')")
    op.execute("ALTER TABLE bookmarks ALTER COLUMN status TYPE bookmarkstatus_new USING status::text::bookmarkstatus_new")
    op.execute("ALTER TABLE bookmarks ALTER COLUMN status SET DEFAULT 'unread'::bookmarkstatus_new")
    op.execute("DROP TYPE bookmarkstatus")
    op.execute("ALTER TYPE bookmarkstatus_new RENAME TO bookmarkstatus")
