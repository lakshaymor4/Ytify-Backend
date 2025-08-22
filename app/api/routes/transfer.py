from fastapi import FastAPI, HTTPException
from services import transfer_service
from celery_config import celery  
from celery.result import AsyncResult

app = FastAPI()

@app.post("/api/transfer")
async def start_transfer(body: dict):
    playlist_ids = body.get("playlist_ids", [])
    options = body.get("options", {})

    if not playlist_ids:
        raise HTTPException(status_code=400, detail="No playlists selected")

    task = transfer_service.transfer_playlists_task.delay(playlist_ids, options)
    return {"success": True, "task_id": task.id}


@app.get("/api/transfer/status/{task_id}")
async def get_status(task_id: str):
    result = celery.AsyncResult(task_id)

    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending", "progress": 0}

    elif result.state == "PROGRESS":
        return {
            "task_id": task_id,
            "status": "in-progress",
            "progress": result.info.get("progress", 0),
            "current": result.info.get("current", 0),
            "total": result.info.get("total", 0),
            "current_playlist": result.info.get("current_playlist", None)
        }

    elif result.state == "SUCCESS":
        return {"task_id": task_id, "status": "completed", "result": result.result}

    elif result.state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "error": str(result.info)}

    else:
        return {"task_id": task_id, "status": result.state}
    
@app.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    result = AsyncResult(task_id, app=celery)
    result.revoke(terminate=True, signal="SIGTERM")
    return {"task_id": task_id, "status": "canceled"}
