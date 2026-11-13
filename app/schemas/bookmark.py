import uuid
from pydantic import BaseModel, HttpUrl, field_validator
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
    genres: Optional[List[str]] = None
    is_favorite: Optional[bool] = None

    @field_validator("genres")
    @classmethod
    def validate_genres(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return value
        from app.services.bookmark_service import GENRES
        invalid = sorted(set(value) - set(GENRES))
        if invalid:
            raise ValueError(f"Unsupported genres: {', '.join(invalid)}")
        return list(dict.fromkeys(value))

class BookmarkResponse(BookmarkBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    content: Optional[ContentResponse] = None
    tags: List[TagResponse] = []
    site_name: Optional[str] = None
    logo_url: Optional[str] = None
    image_url: Optional[str] = None
    excerpt: Optional[str] = None
    genres: List[str] = []
    is_favorite: bool = False

    class Config:
        from_attributes = True
