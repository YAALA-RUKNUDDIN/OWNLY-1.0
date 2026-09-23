"""RQ worker for async tasks (OCR processing etc.). Run with:
    python -m app.workers.rq_worker
"""
from redis import Redis
from rq import Worker

from app.core.config import settings


def main():
    redis = Redis.from_url(settings.REDIS_URL)
    Worker(["ownly"], connection=redis).work()


if __name__ == "__main__":
    main()