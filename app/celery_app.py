from celery import Celery
from celery.signals import worker_init
from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery("summarizer",
                    broker=CELERY_BROKER_URL,
                    backend=CELERY_RESULT_BACKEND,
                    include=["app.tasks"])

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

@worker_init.connect
def _init_db(**_):
    from app.database import init_db
    init_db()
