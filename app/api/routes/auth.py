from fastapi import APIRouter, FastAPI
import logging
from services.setup_yt import setup
from services import transfer_service
import jwt
import uuid
from config import Config
import jsonify
from fastapi import Header, HTTPException, Depends, Request
from typing import Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
import os
router = APIRouter()
# Set up logging for debug
logging.basicConfig(level=logging.DEBUG)

from spotipy.oauth2 import SpotifyOAuth

@router.get("/spotify/login")
async def spotify_login(request: Request):
    try:
        token = request.query_params.get("token")
        
        logging.debug(f"/spotify/login called. Token: {token}")

        try:
            claims = jwt.decode(token, Config.SECRET, algorithms=["HS256"])
            print("claims:", claims)
            session_id = claims.get("uuid")
            logging.debug(f"Session ID: {session_id}")
        except Exception as e:
            logging.error(f"JWT decode failed: {e}")
            return JSONResponse(
                status_code=400,
                content={'success': "False", 'message': 'Invalid token'}
            )

        sp_oauth = SpotifyOAuth(
            client_id=Config.SPOTIFY_CLIENT_ID,
            client_secret=Config.SPOTIFY_CLIENT_SECRET,
            redirect_uri=Config.SPOTIFY_REDIRECT_URI, 
            scope="user-library-read playlist-read-private playlist-read-collaborative",
        )

        auth_url = sp_oauth.get_authorize_url(state=session_id)
        return RedirectResponse(auth_url, status_code=307)

    except Exception as e:
        logging.exception(f"Authentication error: {e}")
        return JSONResponse(
            status_code=500,
            content={'success': "False", 'message': f'Authentication error: {str(e)}'}
        )
@router.get("/gett")

async def sendjwt():
    try:
        muuid  = uuid.uuid4()
        payload = {
            "uuid": str(muuid)
        }
        jwt_token = jwt.encode(payload, Config.SECRET, algorithm="HS256")   
        return {"status": "success", "token": jwt_token}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/setyt", tags=["yt_header"])
async def setYT(
    resp: dict,
    authorization: Optional[str] = Header(None)
):
    try:
        header = resp.get("headers")
  
        
        token = authorization
        
        abc = resp.get("abc")
        
        if not authorization:
            raise HTTPException(status_code=401, detail="Token missing")
        
        
        
        if not all([header, token]):
            return {"status": "error", "message": "Missing required fields"}
        
        jwt_decode = jwt.decode(token, Config.SECRET, algorithms=["HS256"])
        
        setup_result = setup(jwt_decode["uuid"], header)
        
        if setup_result["success"]:
            return {"status": "success", "message": setup_result["message"]}
        else:
            return {"status": "error", "message": setup_result["message"]}
       
    except jwt.InvalidTokenError:
        return {"status": "error", "message": "Invalid token"}
    except KeyError:
        return {"status": "error", "message": "Invalid JWT payload - missing session_id"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class AuthRequest(BaseModel):
   authorization: Optional[str] = Header(None)

@router.post('/authenticate')
async def authenticate(authorization: str = Header(None)):
    try:
        token = authorization
        logging.debug(f"/authenticate called. Authorization header: {authorization}")
        if not token or not isinstance(token, str):
            logging.error("Missing or invalid token.")
            return JSONResponse(
                status_code=400,
                content={'success': "False", 'message': 'Missing or invalid token'}
            )
        jwt_decode = jwt.decode(token, Config.SECRET, algorithms=["HS256"])
        logging.debug(f"Decoded JWT: {jwt_decode}")
        uuid_val = jwt_decode.get("uuid")
        if not uuid_val:
            logging.error("Invalid JWT payload - missing uuid.")
            return JSONResponse(
                status_code=400,
                content={'success': "False", 'message': 'Invalid JWT payload - missing uuid'}
            )
        logging.debug(f"Calling transfer_service.authenticate_services with uuid: {uuid_val}")
        manager = transfer_service.TransferManager(uuid_val)
        success, message = manager.authenticate_services(uuid_val)
        logging.debug(f"Authentication result: success={success}, message={message}")
        if success:
            payload = {'uuid': uuid_val}
            tokens = jwt.encode(payload, Config.SECRET, algorithm="HS256")
            logging.info("Authentication successful. Returning new JWT.")
            return {
                'success': "True",
                'jwt': tokens,
                'message': message
            }
        else:
            logging.error(f"Authentication failed: {message}")
            return JSONResponse(
                status_code=400,
                content={'success': "False", 'message': message}
            )
    except jwt.InvalidTokenError:
        logging.error(f"Invalid token error: {e}")
        return JSONResponse(
            status_code=401,
            content={'success': "False", 'message': 'Invalid token'}
        )
    except Exception as e:
        logging.exception(f"Authentication error: {e}")
        return JSONResponse(
            status_code=500,
            content={'success': "False", 'message': f'Authentication error: {str(e)}'}
        )



