from celery_config import celery
from services import transfer_service
import logging
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
@celery.task(bind=True)
def transfer_playlists_task(self, session_id , selected_playlist_ids, options=None):
   try:
        manager = transfer_service.TransferManager(session_id)
        all_playlists = manager.get_spotify_playlists()
        selected_playlists = [p for p in all_playlists if p['id'] in selected_playlist_ids]
        logger.debug(f"Selected {len(selected_playlists)} playlists out of {len(all_playlists)}")

        total = len(selected_playlists)
        report = []
        try:
             report = manager.transfer_playlists(session_id,selected_playlists, options)
             return {"status": "completed", "report": report}
        except Exception as e:
            logger.error(f"Error occurred while transferring playlists: {e}")
            self.update_state(state="FAILURE", meta={"error": str(e)})
            return {"status": "failed", "error": str(e)}

        # for i, playlist in enumerate(selected_playlists, start=1):
        #     tracks = manager.spotify_client.get_playlist_tracks(playlist['id'])
        #     for j, track in enumerate(tracks, start=1):
        #         # Transfer each track
        #         self.update_state(
        #             state="PROGRESS",
        #             meta={
        #                 "playlist": playlist["name"],
        #                 "current_track": j,
        #                 "total_tracks": len(tracks),
        #                 "overall_progress": int((i-1)/total*100 + j/len(tracks)*(100/total))
        #             }
        #     )

   except Exception as e:
       logging.exception(f"Transfer task failed: {e}")