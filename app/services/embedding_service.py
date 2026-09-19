"""Text chunking, embedding, and ChromaDB persistence."""
import logging
import uuid
from pathlib import Path
from threading import Lock

from app.core.config import settings
from app.models.bookmark import Bookmark
from app.models.content import Content

logger = logging.getLogger(__name__)

_model = None
_model_lock = Lock()
_chroma_client = None
_collection = None
_chroma_lock = Lock()


def _as_list(value):
    return value.tolist() if hasattr(value, "tolist") else value


def chunk_text(text: str, target_tokens: int = 500, max_tokens: int = 1000,
               overlap_tokens: int = 50) -> list[str]:
    """Split text on paragraph boundaries into bounded, slightly overlapping chunks.

    Whitespace tokens are used deliberately here: the embedding model's tokenizer is
    not needed to determine stable chunk boundaries.
    """
    if not text or not text.strip():
        return []
    if not 1 <= target_tokens <= max_tokens:
        raise ValueError("target_tokens must be between 1 and max_tokens")
    if not 0 <= overlap_tokens < target_tokens:
        raise ValueError("overlap_tokens must be non-negative and smaller than target_tokens")

    paragraphs = [paragraph.split() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            chunks.append(" ".join(current))
            current = current[-overlap_tokens:] if overlap_tokens else []

    for paragraph in paragraphs:
        while len(paragraph) > max_tokens:
            if current:
                flush()
            chunks.append(" ".join(paragraph[:max_tokens]))
            paragraph = paragraph[max_tokens - overlap_tokens:]

        if current and len(current) + len(paragraph) > max_tokens:
            flush()
        current.extend(paragraph)
        if len(current) >= target_tokens:
            flush()

    if current:
        chunks.append(" ".join(current))
    return chunks


def get_embedding_model():
    """Return the process-local model singleton."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def load_embedding_model() -> None:
    """Load the model eagerly for worker startup."""
    get_embedding_model()


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        with _chroma_lock:
            if _collection is None:
                import chromadb
                Path(settings.CHROMA_PERSIST_DIRECTORY).mkdir(parents=True, exist_ok=True)
                _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
                _collection = _chroma_client.get_or_create_collection(
                    name=settings.CHROMA_COLLECTION_NAME
                )
    return _collection


def chunk_and_embed_bookmark(bookmark_id: uuid.UUID) -> int:
    """Chunk one ingested bookmark and replace its vectors in the shared collection."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
        if bookmark is None or bookmark.content is None:
            raise ValueError(f"Bookmark {bookmark_id} has no content")
        content = bookmark.content
        text = content.raw_text or content.body or ""
        chunks = chunk_text(text)
        collection = _get_collection()
        prefix = f"{bookmark.id}:"
        existing = collection.get(where={"bookmark_id": str(bookmark.id)})
        if existing.get("ids"):
            collection.delete(ids=existing["ids"])
        if not chunks:
            return 0
        embeddings = _as_list(get_embedding_model().encode(chunks))
        collection.add(
            ids=[f"{prefix}{index}" for index in range(len(chunks))],
            embeddings=embeddings,
            documents=chunks,
            metadatas=[
                {"bookmark_id": str(bookmark.id), "user_id": str(bookmark.user_id)}
                for _ in chunks
            ],
        )
        return len(chunks)
    finally:
        db.close()


def search_bookmarks(query: str, user_id: uuid.UUID, top_k: int) -> list[dict]:
    if not query.strip():
        return []
    collection = _get_collection()
    query_embedding = _as_list(get_embedding_model().encode([query]))
    result = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"user_id": str(user_id)},
    )
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [
        {"chunk": document, "bookmark_id": metadata["bookmark_id"],
         "distance": distances[index] if index < len(distances) else None}
        for index, (document, metadata) in enumerate(zip(documents, metadatas))
    ]
