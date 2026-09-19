import uuid
from pydantic import BaseModel


class SearchResult(BaseModel):
    bookmark_id: uuid.UUID
    title: str
    url: str
    chunk: str
    distance: float | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
