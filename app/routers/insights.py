from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.bookmark import Bookmark, BookmarkStatus
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.insights import ActivityPoint, GenreCount, InsightsResponse
from app.services.bookmark_service import GENRES

router = APIRouter()


@router.get("/genres", response_model=list[str])
def genres() -> list[str]:
    return GENRES


@router.get("/insights", response_model=InsightsResponse)
def insights(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bookmarks = db.query(Bookmark).filter(Bookmark.user_id == current_user.id).all()
    genre_counts = Counter(genre for bookmark in bookmarks for genre in (bookmark.genres or []))
    today = datetime.utcnow().date()
    activity = [
        ActivityPoint(
            date=(today - timedelta(days=offset)).isoformat(),
            count=sum(bookmark.created_at.date() == today - timedelta(days=offset) for bookmark in bookmarks if bookmark.created_at),
        )
        for offset in range(13, -1, -1)
    ]
    used = set(genre_counts)
    recommendations = [genre for genre in GENRES if genre not in used][:4]
    return InsightsResponse(
        total=len(bookmarks),
        favorites=sum(bookmark.is_favorite for bookmark in bookmarks),
        ready=sum(bookmark.status == BookmarkStatus.READ for bookmark in bookmarks),
        unread=sum(bookmark.status == BookmarkStatus.UNREAD for bookmark in bookmarks),
        genres=[GenreCount(name=name, count=count) for name, count in genre_counts.most_common()],
        activity=activity,
        recommendations=recommendations,
    )
