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
    
    r = redis.Redis.from_url(Config.REDIS)
    
    task_status = r.get(f"task_status_{session_id}")
    if task_status and task_status.decode('utf-8') == 'cancelled':
        return {"session_id": session_id, "status": "cancelled", "progress": 0}
    
    if task_status and task_status.decode('utf-8') == 'failed':
        return {"session_id": session_id, "status": "failed", "progress": 0}
    
    
    result = r.get(session_id)
    if result is None:
        return {"session_id": session_id, "status": "not_found", "progress": 0}

    try:
        progress = float(result.decode("utf-8"))
        
        if task_status and task_status.decode('utf-8') == 'completed':
            status = "completed"
        elif progress >= 100:
            status = "completed"
        elif task_status and task_status.decode('utf-8') == 'running':
            status = "in_progress"
        else:
            status = "in_progress"
            
        return {"session_id": session_id, "status": status, "progress": progress}
    except (ValueError, AttributeError):
        return {"session_id": session_id, "status": "invalid_value", "progress": result}


@router.post("/cancel")
async def cancel_transfer(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        decoded = jwt.decode(authorization, Config.SECRET, algorithms=["HS256"])
        session_id = decoded.get('uuid')
        
        if not session_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        r = redis.Redis.from_url(Config.REDIS)
        r.set(f"cancel_{session_id}", "true", ex=300)  
        
        return {"message": "Cancellation requested", "session_id": session_id}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/cancel/{token}")
async def cancel_transfer_by_token(token: str):
    try:
        decoded = jwt.decode(token, Config.SECRET, algorithms=["HS256"])
        session_id = decoded.get("uuid")
        
        if not session_id:
            raise HTTPException(status_code=401, detail="Invalid token: session_id missing")
        
        r = redis.Redis.from_url(Config.REDIS)
        r.set(f"cancel_{session_id}", "true", ex=300) 

        return {"message": "Cancellation done", "session_id": session_id, "success": "True"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
