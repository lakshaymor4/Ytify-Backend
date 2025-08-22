from celery import Celery
import config

celery = Celery(
    "playlist_transfer",
    broker=config.REDIS_URL,  
    backend=config.REDIS_URL
)

celery.conf.task_track_started = True
celery.conf.result_expires = 3600  
