from celery_config import celery
import transfer_service

@celery.task(bind=True)
def transfer_playlists_task(self, selected_playlist_ids, options):
   
    manager = transfer_service.get_transfer_manager()
    all_playlists = manager.get_spotify_playlists()
    selected_playlists = [p for p in all_playlists if p['id'] in selected_playlist_ids]

    total = len(selected_playlists)
    report = []

    for i, playlist in enumerate(selected_playlists, start=1):
    
        result = manager.transfer_playlists([playlist], options)
        report.append(result)

        self.update_state(
            state="PROGRESS",
            meta={
                "current": i,
                "total": total,
                "progress": int(i / total * 100),
                "current_playlist": playlist["name"]
            }
        )

    return {"status": "completed", "report": report}
