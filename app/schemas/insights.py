from pydantic import BaseModel


class GenreCount(BaseModel):
    name: str
    count: int


class ActivityPoint(BaseModel):
    date: str
    count: int


class InsightsResponse(BaseModel):
    total: int
    favorites: int
    ready: int
    unread: int
    genres: list[GenreCount]
    activity: list[ActivityPoint]
    recommendations: list[str]
