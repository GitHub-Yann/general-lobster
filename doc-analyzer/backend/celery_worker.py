"""
Celery 配置和 Worker
"""
from celery import Celery
from app.config import REDIS_URL

celery_app = Celery(
    "doc_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.core.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)

if __name__ == "__main__":
    celery_app.start()
