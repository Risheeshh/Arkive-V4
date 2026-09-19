import logging
import uuid
from rq import Worker, Queue, Connection
from app.core.queue import redis_conn
from app.core.database import SessionLocal
from app.services.bookmark_service import process_bookmark
from app.core.queue import queue
from app.services.embedding_service import chunk_and_embed_bookmark, load_embedding_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_bookmark_job(bookmark_id: str):
    db = SessionLocal()
    try:
        process_bookmark(db, uuid.UUID(bookmark_id))
        queue.enqueue("app.worker.chunk_and_embed_bookmark_job", bookmark_id)
    finally:
        db.close()

def chunk_and_embed_bookmark_job(bookmark_id: str):
    return chunk_and_embed_bookmark(uuid.UUID(bookmark_id))

if __name__ == "__main__":
    load_embedding_model()
    with Connection(redis_conn):
        worker = Worker([Queue(connection=redis_conn)], connection=redis_conn)
        worker.work()
