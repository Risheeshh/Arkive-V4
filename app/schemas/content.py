import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ContentBase(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    raw_text: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None

class ContentCreate(ContentBase):
    pass

class ContentUpdate(ContentBase):
    pass

class ContentResponse(ContentBase):
    id: uuid.UUID
    bookmark_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
