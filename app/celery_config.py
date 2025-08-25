import ssl
from celery import Celery
from config import Config

celery = Celery(
    "playlist_transfer",
    broker=Config.REDIS_URL,
    backend=Config.REDIS_URL,
    include=["services.celery_task"] 
)

celery.conf.update(
    task_track_started=True,
    result_expires=3600,
    broker_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE},
    redis_backend_use_ssl={"ssl_cert_reqs": ssl.CERT_NONE}
)
