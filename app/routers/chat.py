from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.embedding_service import search_bookmarks
from app.services.gemini_service import generate_chat_response, build_prompt
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.routers.users import get_current_user
from app.models.user import User
from app.models.bookmark import Bookmark
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Chat endpoint that uses RAG to answer questions based on the user's bookmarks.
    """
    user_id = current_user.id

    # Retrieve top-k chunks (search_bookmarks embeds the question internally)
    try:
        chunks = search_bookmarks(request.question, user_id, request.top_k)
    except Exception as e:
        logger.error(f"Error searching bookmarks: {e}")
        raise HTTPException(status_code=500, detail="Failed to search bookmarks")

    # If no chunks found, return a friendly message without calling LLM
    if not chunks:
        return ChatResponse(
            answer="I don't have any relevant bookmarks saved yet to answer that question.",
            citations=[]
        )

    # Enrich chunks with bookmark title and URL from PostgreSQL if missing
    bookmark_ids = []
    for chunk in chunks:
        bid = chunk.get('bookmark_id')
        if bid and ('bookmark_title' not in chunk or 'url' not in chunk):
            bookmark_ids.append(bid)

    if bookmark_ids:
        # Convert to UUID if they are strings
        uuid_ids = []
        for bid in bookmark_ids:
            if isinstance(bid, str):
                uuid_ids.append(uuid.UUID(bid))
            else:
                uuid_ids.append(bid)
        bookmarks = db.query(Bookmark).filter(Bookmark.id.in_(uuid_ids)).all()
        bookmark_map = {str(b.id): b for b in bookmarks}
        for chunk in chunks:
            bid = chunk.get('bookmark_id')
            if bid:
                bid_str = str(bid)
                if bid_str in bookmark_map:
                    bm = bookmark_map[bid_str]
                    if 'bookmark_title' not in chunk:
                        chunk['bookmark_title'] = bm.title
                    if 'url' not in chunk:
                        chunk['url'] = bm.url

    # Build prompt and call Gemini
    prompt = build_prompt(request.question, chunks)
    try:
        answer = generate_chat_response(prompt)
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate answer from LLM")

    # Build citations from the actual retrieved chunks
    citations = []
    for chunk in chunks:
        # Each chunk should have bookmark_id, title, url
        bookmark_id = chunk.get('bookmark_id')
        title = chunk.get('bookmark_title', 'Unknown Title')
        url = chunk.get('url', '')
        if bookmark_id:
            citations.append(Citation(bookmark_id=bookmark_id, title=title, url=url))

    return ChatResponse(answer=answer, citations=citations)
