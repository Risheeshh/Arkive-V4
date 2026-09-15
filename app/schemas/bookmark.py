from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class BookmarkBase(BaseModel):
    title: str
    url: HttpUrl
    description: Optional[str] = None

class BookmarkCreate(BookmarkBase):
    pass

class BookmarkResponse(BookmarkBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
