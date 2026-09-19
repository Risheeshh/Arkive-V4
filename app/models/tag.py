import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Table, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

# Association table for many-to-many between Bookmark and Tag
bookmark_tags = Table(
    "bookmark_tags",
    Base.metadata,
    Column("bookmark_id", UUID(as_uuid=True), ForeignKey("bookmarks.id"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="tags")
    bookmarks = relationship("Bookmark", secondary=bookmark_tags, back_populates="tags")
