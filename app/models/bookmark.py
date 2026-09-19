import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class BookmarkStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"
    FAILED = "failed"

class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String, index=True, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(
            BookmarkStatus,
            values_callable=lambda enum_type: [status.value for status in enum_type],
        ),
        default=BookmarkStatus.UNREAD,
        nullable=False,
    )
    error_message = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="bookmarks")
    content = relationship("Content", back_populates="bookmark", uselist=False, cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="bookmark_tags", back_populates="bookmarks")
