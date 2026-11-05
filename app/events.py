import json, time, redis
from app.config import CELERY_BROKER_URL

CHANNEL = "factory_events"
_client = None

def _get_client():
    global _client
    if _client is None:
        _client = redis.from_url(CELERY_BROKER_URL, decode_responses=False)
    return _client

def publish(event_type: str, **payload):
    event = {"type": event_type, "ts": time.time(), **payload}
    try:
        _get_client().publish(CHANNEL, json.dumps(event))
    except Exception:
        pass  # never break the pipeline

