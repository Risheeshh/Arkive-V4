from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.bookmark import Bookmark
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.search import SearchResponse, SearchResult
from app.services.embedding_service import search_bookmarks

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
def search(
    query: str = Query(..., alias="q", min_length=1),
    top_k: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    matches = search_bookmarks(query, current_user.id, top_k)
    bookmark_ids = [match["bookmark_id"] for match in matches]
    bookmarks = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == current_user.id, Bookmark.id.in_(bookmark_ids))
        .all()
    )
    by_id = {str(bookmark.id): bookmark for bookmark in bookmarks}
    results = []
    for match in matches:
        bookmark = by_id.get(match["bookmark_id"])
        if bookmark:
            results.append(
                SearchResult(
                    bookmark_id=bookmark.id,
                    title=bookmark.title,
                    url=bookmark.url,
                    chunk=match["chunk"],
                    distance=match["distance"],
                )
            )
    return SearchResponse(results=results)
