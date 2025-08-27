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
import redis
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

@router.get("/status/{token}")
async def get_status(token: str):
    jwt_decode = jwt.decode(token, Config.SECRET, algorithms=["HS256"])
    session_id = jwt_decode.get("uuid")
    result = redis.Redis.from_url(Config.REDIS).get(session_id)

    if result is None:
        return {"session_id": session_id, "status": "not found"}

    # decode and convert to float
    try:
        progress = float(result.decode("utf-8"))
    except (ValueError, AttributeError):
        return {"session_id": session_id, "status": "invalid value", "progress": result}

    if progress < 100:
        return {"session_id": session_id, "status": "in progress", "progress": progress}
    return {"session_id": session_id, "status": "completed", "progress": progress}


@router.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    result = AsyncResult(task_id, app=celery)
    result.revoke(terminate=True, signal="SIGTERM")
    return {"task_id": task_id, "status": "canceled"}
