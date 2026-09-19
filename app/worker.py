import logging
import uuid
from rq import Worker, Queue, Connection
from app.core.queue import redis_conn
from app.core.database import SessionLocal
from app.services.bookmark_service import process_bookmark

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_bookmark_job(bookmark_id: str):
    db = SessionLocal()
    try:
        process_bookmark(db, uuid.UUID(bookmark_id))
    finally:
        db.close()

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker([Queue(connection=redis_conn)], connection=redis_conn)
        worker.work()
