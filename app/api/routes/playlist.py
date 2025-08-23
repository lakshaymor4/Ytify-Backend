
from fastapi import APIRouter, Header
import logging
from services import transfer_service
import jwt
from config import Config
from fastapi.responses import JSONResponse

router = APIRouter()

logging.basicConfig(level=logging.DEBUG)

@router.post('/get')
async def get_playlists(authorization: str = Header(None)):
    logging.debug(f"/playlist/get called. Authorization header: {authorization}")
    token = authorization
    try:
        if not isinstance(token, str):
            logging.error("Token is not a string or missing.")
            raise Exception("Token must be a string")
        jwt_decode = jwt.decode(token, Config.SECRET, algorithms=["HS256"])
        logging.debug(f"Decoded JWT: {jwt_decode}")
    except Exception as e:
        logging.error(f"JWT decode failed: {e}")
        return JSONResponse(
            status_code=400,
            content={"success": "False", "message": f"jwt failed: {str(e)}"}
        )

    try:
        logging.debug(f"Creating TransferManager with uuid: {jwt_decode.get('uuid')}")
        manager = transfer_service.TransferManager(jwt_decode.get("uuid"))
        playlists = manager.get_spotify_playlists()
        logging.debug(f"Retrieved {len(playlists)} playlists from Spotify.")

        formatted_playlists = []
        for playlist in playlists:
            formatted_playlists.append({
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist.get('description', ''),
                'tracks_count': playlist['tracks']['total'],
                'owner': playlist['owner']['display_name'],
                'public': playlist.get('public', False),
                'is_liked_songs': playlist['id'] == 'liked_songs'
            })

        logging.info(f"Returning {len(formatted_playlists)} formatted playlists.")
        return {"success": "True", "playlists": formatted_playlists}

    except Exception as e:
        logging.exception(f"Failed to load playlists: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": "False", "message": f"Failed to load playlists: {str(e)}"}
        )


