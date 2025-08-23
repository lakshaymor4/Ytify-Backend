import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config import Config
import os

class SpotifyClient:
    def __init__(self, session_id=None):
        self.scope = "user-library-read playlist-read-private playlist-read-collaborative"
        self.sp = None
        self.user_id = None
        self.session_id = session_id
        try:
            if self.session_id:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                cache_path = os.path.join(Config.SPOTIFY_CACHE_DIR, f"spotify_cache_{session_id}.json")
            else:
                cache_path = Config.SPOTIFY_CACHE_FILE

            auth_manager = SpotifyOAuth(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIFY_REDIRECT_URI,
                scope=self.scope,
                cache_path=cache_path
            )

            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            user_info = self.sp.current_user()
            self.user_id = user_info['id']
            self.authenticated = True
        except Exception as e:
            self.authenticated = False
            self.auth_error = str(e)

    def authenticate(self):
        try:
            if self.session_id:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                cache_path = os.path.join(Config.SPOTIFY_CACHE_DIR, f"spotify_cache_{session_id}.json")
            else:
                cache_path = Config.SPOTIFY_CACHE_FILE

            auth_manager = SpotifyOAuth(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIFY_REDIRECT_URI,
                scope=self.scope,
                cache_path=cache_path
            )

            self.sp = spotipy.Spotify(auth_manager=auth_manager)

            user_info = self.sp.current_user()
            self.user_id = user_info['id']

            return True, f"Successfully authenticated as {user_info['display_name']}"

        except Exception as e:
            return False, f"Authentication failed: {str(e)}"
    def get_playlist(self):
        if not self.sp :
            raise Exception("Not Authenticated yet")
        playlists = []

        total_liked = self.sp.current_user_saved_tracks_add(limit=1)
        playlists.append({
            'id': 'liked_songs',
            'name': 'Liked Songs',
            'description': 'Your liked songs from Spotify',
            'tracks': {'total': total_liked},
            'public': False,
            'owner': {'display_name': 'Spotify'}
        })

        offset = 0
        limit = 50
        
        while True:
            results = self.sp.current_user_playlists(limit=limit, offset=offset)
            
            for playlist in results['items']:
                if playlist['owner']['id'] == self.user_id:  
                    playlists.append({
                        'id': playlist['id'],
                        'name': playlist['name'],
                        'description': playlist['description'] or '',
                        'tracks': playlist['tracks'],
                        'public': playlist['public'],
                        'owner': playlist['owner']
                    })
            
            if len(results['items']) < limit:
                break
            offset += limit
        
        return playlists
    
    def get_liked_songs_count(self):
        try:
            results = self.sp.current_user_saved_tracks(limit=1)
            return results['total']
        except:
            return 0
        
    def get_playlist_tracks(self, playlist_id):
        if not self.sp:
            raise Exception("Not authenticated with Spotify")
        
        tracks = []
        
        if playlist_id == 'liked_songs':
            offset = 0
            limit = 50
            
            while True:
                results = self.sp.current_user_saved_tracks(limit=limit, offset=offset)
                
                for item in results['items']:
                    track = item['track']
                    if track and track['name']: 
                        tracks.append(self._format_track(track))
                
                if len(results['items']) < limit:
                    break
                offset += limit
        
        else:
           
            offset = 0
            limit = 100
            
            while True:
                results = self.sp.playlist_tracks(playlist_id, limit=limit, offset=offset)
                
                for item in results['items']:
                    track = item['track']
                    if track and track['name']:  
                        tracks.append(self._format_track(track))
                
                if len(results['items']) < limit:
                    break
                offset += limit
        
        return tracks
    
    def _format_track(self, track):
        artists = [artist['name'] for artist in track['artists']]
        
        return {
            'name': track['name'],
            'artists': artists,
            'album': track['album']['name'],
            'duration_ms': track['duration_ms'],
            'spotify_id': track['id'],
            'external_urls': track['external_urls'],
            'preview_url': track['preview_url']
        }
    
    def get_user_info(self):
        if not self.sp:
            return None
        
        return self.sp.current_user()



