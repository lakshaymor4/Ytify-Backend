from fastapi import APIRouter, FastAPI
from services import setup_yt
from services import transfer_service
import jwt
import uuid
import config
import jsonify
router = APIRouter()

@router.post('playlists')
async def get_playlists(req : dict):
    token = req.get("token")
    try:
        jwt.decode(token, config.SECRET, algorithms=["HS256"])
    except:
        return jsonify({
            "message":"jwt failed"
        })
    
    
    
    try:
        manager = transfer_service.get_transfer_manager()
        playlists = manager.get_spotify_playlists()
        
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
        
        return jsonify({
            'success': True,
            'playlists': formatted_playlists
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to load playlists: {str(e)}'
        }), 500
    

