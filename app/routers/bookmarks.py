from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
from app.core.database import get_db
from app.core.security import decode_token
from app.routers.users import oauth2_scheme
from app.schemas.bookmark import BookmarkCreate, BookmarkUpdate, BookmarkResponse
from app.schemas.tag import TagCreate
from app.services.bookmark_service import (
    get_bookmark,
    get_bookmarks,
    create_bookmark,
    update_bookmark,
    delete_bookmark,
    add_tags_to_bookmark,
)
from app.services.user_service import get_user_by_email

router = APIRouter()

def get_current_user_id(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> uuid.UUID:
    email = decode_token(token)
    user = get_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user.id

@router.post("/bookmarks", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
def create_bookmark_endpoint(
    bookmark: BookmarkCreate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    db_bookmark = create_bookmark(db, bookmark, user_id)
    return db_bookmark

@router.get("/bookmarks", response_model=List[BookmarkResponse])
def list_bookmarks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    bookmarks = get_bookmarks(db, user_id, skip, limit)
    return bookmarks

@router.get("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
def get_bookmark_endpoint(
    bookmark_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    db_bookmark = get_bookmark(db, bookmark_id, user_id)
    if not db_bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    return db_bookmark

@router.patch("/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
def update_bookmark_endpoint(
    bookmark_id: uuid.UUID,
    bookmark_update: BookmarkUpdate,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    db_bookmark = update_bookmark(db, bookmark_id, user_id, bookmark_update)
    if not db_bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    return db_bookmark

@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark_endpoint(
    bookmark_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    success = delete_bookmark(db, bookmark_id, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    return None

@router.post("/bookmarks/{bookmark_id}/tags", response_model=BookmarkResponse)
def add_tags_to_bookmark_endpoint(
    bookmark_id: uuid.UUID,
    tags: List[TagCreate],
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    db_bookmark = get_bookmark(db, bookmark_id, user_id)
    if not db_bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    tag_names = [tag.name for tag in tags]
    add_tags_to_bookmark(db, db_bookmark, tag_names, user_id)
    return db_bookmark
