from ytmusicapi import YTMusic
import os
from fuzzywuzzy import fuzz
from config import Config

class YouTubeClient:
    def __init__(self):
        self.ytmusic = None
        self.session_id = None
    
    def authenticate(self, session_id):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            paths = os.path.join(base_dir, f"header{session_id}.json")
            
            if not os.path.exists(paths):
                return False, "Headers file not found."
            
            self.ytmusic = YTMusic(paths)
            self.session_id = session_id
            
            # Quick test to ensure cookies are valid
            playlists = self.ytmusic.get_library_playlists(limit=1)
            if playlists is None:
                return False, "Authentication successful but no playlists returned. Your cookies may be expired."
            
            return True, "Successfully authenticated with YouTube Music"
        except Exception as e:
            return False, f"YouTube Music authentication failed: {str(e)}"
    
    def _ensure_authenticated(self, session_id):
        """Internal helper to always check authentication."""
        if not self.ytmusic or self.session_id != session_id:
            success, msg = self.authenticate(session_id)
            if not success:
                raise Exception(msg)

    def create_playlist(self, session_id, name, description="", privacy_status="PRIVATE"):
        self._ensure_authenticated(session_id)
        try:
            return self.ytmusic.create_playlist(
                title=name,
                description=description,
                privacy_status=privacy_status
            )
        except Exception as e:
            raise Exception(f"Failed to create playlist: {str(e)}")

    def search_song(self, mode , session_id, track_name, artist_name, album_name=None):
        self._ensure_authenticated(session_id)
        query = f"{track_name} {artist_name}"
        if album_name:
            query += f" {album_name}"
        
        try:
            threshold = 0
            if(mode=="ai"): 
                threshold = Config.SIMILARITY_AI
            else:
                threshold = Config.SIMILARITY_THRESHOLD
            search_results = self.ytmusic.search(query, filter="songs", limit=Config.MAX_SEARCH_RESULTS)
            best_match, best_score = None, 0
            for result in search_results:
                if result.get('videoId'):
                    score = self._calculate_similarity(
                        track_name, artist_name,
                        result.get('title', ''),
                        result.get('artists', [{}])[0].get('name', '') if result.get('artists') else ''
                    )
                    if score > best_score and score >= threshold:
                        best_score, best_match = score, result
            return best_match, best_score
        except Exception as e:
            print(f"Search error for '{query}': {str(e)}")
            return None, 0

    def add_song_to_playlist(self, session_id, playlist_id, video_id):
        self._ensure_authenticated(session_id)
        try:
            self.ytmusic.add_playlist_items(playlist_id, [video_id])
            return True
        except Exception as e:
            print(f"Failed to add song: {str(e)}")
            return False

    def add_song_to_liked(self, session_id, video_id):
        self._ensure_authenticated(session_id)
        try:
            self.ytmusic.rate_song(video_id, 'LIKE')
            return True
        except Exception as e:
            print(f"Failed to like song: {str(e)}")
            return False

    def get_library_playlists(self, session_id):
        self._ensure_authenticated(session_id)
        try:
            return self.ytmusic.get_library_playlists(limit=None)
        except Exception as e:
            print(f"Failed to get playlists: {str(e)}")
            return []

    def playlist_exists(self, session_id, playlist_name):
        playlists = self.get_library_playlists(session_id)
        for playlist in playlists:
            if playlist.get('title', '').lower() == playlist_name.lower():
                return True, playlist.get('playlistId')
        return False, None

    def get_playlist_tracks_count(self, session_id, playlist_id):
        self._ensure_authenticated(session_id)
        try:
            playlist = self.ytmusic.get_playlist(playlist_id, limit=None)
            return len(playlist.get('tracks', []))
        except Exception as e:
            print(f"Failed to get playlist track count: {str(e)}")
            return 0

    def delete_playlist(self, session_id, playlist_id):
        self._ensure_authenticated(session_id)
        try:
            self.ytmusic.delete_playlist(playlist_id)
            return True
        except Exception as e:
            print(f"Failed to delete playlist: {str(e)}")
            return False

    def remove_song_from_playlist(self, session_id, playlist_id, video_id, set_video_id=None):
        self._ensure_authenticated(session_id)
        try:
            self.ytmusic.remove_playlist_items(playlist_id, [{'videoId': video_id, 'setVideoId': set_video_id}])
            return True
        except Exception as e:
            print(f"Failed to remove song: {str(e)}")
            return False

    def unlike_song(self, session_id, video_id):
        self._ensure_authenticated(session_id)
        try:
            self.ytmusic.rate_song(video_id, 'INDIFFERENT')
            return True
        except Exception as e:
            print(f"Failed to unlike song: {str(e)}")
            return False

    def get_liked_songs(self, session_id, limit=None):
        self._ensure_authenticated(session_id)
        try:
            liked_songs = self.ytmusic.get_liked_songs(limit=limit)
            return liked_songs.get('tracks', [])
        except Exception as e:
            print(f"Failed to get liked songs: {str(e)}")
            return []

    def search_multiple_queries(self, session_id, queries, filter_type="songs"):
        self._ensure_authenticated(session_id)
        results = []
        for query in queries:
            try:
                search_results = self.ytmusic.search(query, filter=filter_type, limit=3)
                if search_results:
                    results.extend(search_results)
            except Exception as e:
                print(f"Search error for '{query}': {str(e)}")
        return results

    def _calculate_similarity(self, spotify_title, spotify_artist, youtube_title, youtube_artist):
        spotify_title, spotify_artist = spotify_title.lower().strip(), spotify_artist.lower().strip()
        youtube_title, youtube_artist = youtube_title.lower().strip(), youtube_artist.lower().strip()
        
        title_similarity = fuzz.ratio(spotify_title, youtube_title) / 100.0
        artist_similarity = fuzz.ratio(spotify_artist, youtube_artist) / 100.0
        return (title_similarity * 0.7) + (artist_similarity * 0.3)
