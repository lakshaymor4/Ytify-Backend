from celery import Celery
from config import Config

celery = Celery(
    "playlist_transfer",
    broker=Config.REDIS_URL,  
    backend=Config.REDIS_URL
)

celery.conf.task_track_started = True
celery.conf.result_expires = 3600  
