from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import transfer, auth, playlist 
from fastapi import APIRouter, Request
from spotipy.oauth2 import SpotifyOAuth
from config import Config
import os
app = FastAPI(title="Spotify to YouTube Music Migrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

@router.get("/callback")
async def spotify_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")  
    if not code:
        return {"success": False, "message": "No code in callback"}

    session_id = state  

    cache_path = os.path.join(Config.SPOTIFY_CACHE_DIR, f"spotify_cache_{session_id}.json")

    sp_oauth = SpotifyOAuth(
        client_id=Config.SPOTIFY_CLIENT_ID,
        client_secret=Config.SPOTIFY_CLIENT_SECRET,
        redirect_uri=Config.SPOTIFY_REDIRECT_URI,
        scope="user-library-read playlist-read-private playlist-read-collaborative",
        cache_path=cache_path
    )

    token_info = sp_oauth.get_access_token(code)
    if token_info:
        return {"success": True, "message": "Spotify authentication complete. You can close this window."}
    else:
        return {"success": False, "message": "Failed to get token from Spotify."}

app.include_router(transfer.router, prefix="/transfer", tags=["Transfer"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(playlist.router, prefix="/playlist", tags=["Playlist"])
