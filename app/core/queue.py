import redis
from rq import Queue
from app.core.config import settings

# Create Redis connection
redis_conn = redis.from_url(settings.REDIS_URL)

# Create RQ queue
queue = Queue(connection=redis_conn)
