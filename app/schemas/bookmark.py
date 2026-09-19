import uuid
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List
from app.models.bookmark import BookmarkStatus
from app.schemas.content import ContentResponse
from app.schemas.tag import TagResponse

class BookmarkBase(BaseModel):
    title: str
    url: HttpUrl
    description: Optional[str] = None

class BookmarkCreate(BookmarkBase):
    pass

class BookmarkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    status: Optional[BookmarkStatus] = None

class BookmarkResponse(BookmarkBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    content: Optional[ContentResponse] = None
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True
