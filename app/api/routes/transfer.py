from fastapi import FastAPI, HTTPException, Depends, Header
from services import transfer_service
from celery_config import celery  
from celery.result import AsyncResult
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi import APIRouter
from services.celery_task import transfer_playlists_task
from typing import Optional
import jwt
from config import Config
router = APIRouter()
app = FastAPI()

class TransferBody(BaseModel):
    playlist_ids: List[str]
    options: Optional[Dict[str, Any]] = {}

@router.post("/start")
async def start_transfer( body: TransferBody,  authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    if not body.playlist_ids:
        raise HTTPException(status_code=400, detail="No playlists selected")

    try:
        decoded_token = jwt.decode(authorization, Config.SECRET, algorithms=["HS256"])
        session_i = decoded_token.get("uuid")
        if not session_i:
            raise HTTPException(status_code=401, detail="Invalid token: session_id missing")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Trigger Celery task
    try:
        task = transfer_playlists_task.delay(
            session_id=session_i,
            selected_playlist_ids=body.playlist_ids,
            options=body.options
        )
        return {"success": "True", "task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start transfer: {str(e)}")

@router.get("/status/{task_id}")
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
    
@router.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    result = AsyncResult(task_id, app=celery)
    result.revoke(terminate=True, signal="SIGTERM")
    return {"task_id": task_id, "status": "canceled"}
