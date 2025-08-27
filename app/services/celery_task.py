from celery_config import celery
from services import transfer_service
from services.transfer_service import TaskCancelledException
import logging
from celery.utils.log import get_task_logger
import redis
from config import Config

logger = get_task_logger(__name__)

@celery.task(bind=True)
def transfer_playlists_task(self, session_id, selected_playlist_ids, options=None):
    try:
        r = redis.Redis.from_url(Config.REDIS)
        r.set(f"task_status_{session_id}", "running", ex=3600)  
        
        manager = transfer_service.TransferManager(session_id)
        
        auth_success, auth_message = manager.authenticate_services(session_id)
        if not auth_success:
            r.set(f"task_status_{session_id}", "failed")
            return {"status": "failed", "message": auth_message}
        
        all_playlists = manager.get_spotify_playlists()
        selected_playlists = [p for p in all_playlists if p['id'] in selected_playlist_ids]
        logger.debug(f"Selected {len(selected_playlists)} playlists out of {len(all_playlists)}")

        try:
            report = manager.transfer_playlists(session_id, selected_playlists, options, task=self)
            
            r.set(f"task_status_{session_id}", "completed")
            return {"status": "completed", "report": report}
            
        except TaskCancelledException:
            r.set(f"task_status_{session_id}", "cancelled")
            r.set(session_id, 0) 
            logger.info(f"Transfer task cancelled for session {session_id}")
            return {"status": "cancelled", "message": "Transfer was cancelled by user"}
            
        except Exception as e:
            logger.error(f"Error occurred while transferring playlists: {e}")
            r.set(f"task_status_{session_id}", "failed")
            self.update_state(state="FAILURE", meta={"error": str(e)})
            return {"status": "failed", "error": str(e)}

    except Exception as e:
        logger.exception(f"Transfer task failed: {e}")
        r = redis.Redis.from_url(Config.REDIS)
        r.set(f"task_status_{session_id}", "failed")
        return {"status": "failed", "error": str(e)}