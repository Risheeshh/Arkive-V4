from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

class ChatRequest(BaseModel):
    question: str
    top_k: int = Field(10, ge=1, le=100)

class Citation(BaseModel):
    bookmark_id: uuid.UUID
    title: str
    url: str

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
