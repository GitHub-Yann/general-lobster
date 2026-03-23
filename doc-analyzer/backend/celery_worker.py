"""
Celery 配置和 Worker
"""
from celery import Celery

# Redis 作为 broker 和 backend
celery_app = Celery(
    "doc_analyzer",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.core.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,  # 公平调度
)

if __name__ == "__main__":
    celery_app.start()
