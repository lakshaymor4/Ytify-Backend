from ytmusicapi import YTMusic
import json
import os
from fuzzywuzzy import fuzz
from config import Config

class YouTubeClient:
    def __init__(self ):
        self.ytmusic = None
    
    def authenticate(self, session_id):
        try:
            paths = Config.YOUTUBE_MUSIC_HEADERS_FILE + session_id + ".json"
            if not os.path.exists(paths):
                return False, f"Headers file not found."
            
            self.ytmusic = YTMusic(paths)
            
            try:
                playlists = self.ytmusic.get_library_playlists(limit=1)
                if playlists is None:
                    return False, "Authentication successful but no playlists returned. Your account may not have any playlists or cookies may be expired."
                return True, "Successfully authenticated with YouTube Music"
            except Exception as playlist_error:
                return False, f"Failed to fetch playlists: {str(playlist_error)}. Your authentication cookies may be expired."
            
        except Exception as e:
            return False, f"YouTube Music authentication failed: {str(e)}"
    
    def create_playlist(self, name, description="", privacy_status="PRIVATE"):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            playlist_id = self.ytmusic.create_playlist(
                title=name,
                description=description,
                privacy_status=privacy_status
            )
            return playlist_id
        except Exception as e:
            raise Exception(f"Failed to create playlist: {str(e)}")
    
    def search_song(self, track_name, artist_name, album_name=None):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        query = f"{track_name} {artist_name}"
        if album_name:
            query += f" {album_name}"
        
        try:
            search_results = self.ytmusic.search(query, filter="songs", limit=Config.MAX_SEARCH_RESULTS)
            
            best_match = None
            best_score = 0
            
            for result in search_results:
                if result.get('videoId'):
                    score = self._calculate_similarity(
                        track_name, artist_name,
                        result.get('title', ''),
                        result.get('artists', [{}])[0].get('name', '') if result.get('artists') else ''
                    )
                    
                    if score > best_score and score >= Config.SIMILARITY_THRESHOLD:
                        best_score = score
                        best_match = result
            
            return best_match, best_score
            
        except Exception as e:
            print(f"Search error for '{query}': {str(e)}")
            return None, 0
    
    def add_song_to_playlist(self, playlist_id, video_id):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            self.ytmusic.add_playlist_items(playlist_id, [video_id])
            return True
        except Exception as e:
            print(f"Failed to add song to playlist: {str(e)}")
            return False
    
    def add_song_to_liked(self, video_id):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            self.ytmusic.rate_song(video_id, 'LIKE')
            return True
        except Exception as e:
            print(f"Failed to like song: {str(e)}")
            return False
    
    def get_library_playlists(self):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            playlists = self.ytmusic.get_library_playlists(limit=None)
            return playlists
        except Exception as e:
            print(f"Failed to get playlists: {str(e)}")
            return []
    
    def _calculate_similarity(self, spotify_title, spotify_artist, youtube_title, youtube_artist):
        
        spotify_title = spotify_title.lower().strip()
        spotify_artist = spotify_artist.lower().strip()
        youtube_title = youtube_title.lower().strip()
        youtube_artist = youtube_artist.lower().strip()
        
        title_similarity = fuzz.ratio(spotify_title, youtube_title) / 100.0
        artist_similarity = fuzz.ratio(spotify_artist, youtube_artist) / 100.0
        
        combined_similarity = (title_similarity * 0.7) + (artist_similarity * 0.3)
        
        return combined_similarity
    
    def playlist_exists(self, playlist_name):
        playlists = self.get_library_playlists()
        
        for playlist in playlists:
            if playlist.get('title', '').lower() == playlist_name.lower():
                return True, playlist.get('playlistId')
        
        return False, None
    
    def get_playlist_tracks_count(self, playlist_id):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            playlist = self.ytmusic.get_playlist(playlist_id, limit=None)
            return len(playlist.get('tracks', []))
        except Exception as e:
            print(f"Failed to get playlist track count: {str(e)}")
            return 0
    
    def delete_playlist(self, playlist_id):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            self.ytmusic.delete_playlist(playlist_id)
            return True
        except Exception as e:
            print(f"Failed to delete playlist: {str(e)}")
            return False
    
    def remove_song_from_playlist(self, playlist_id, video_id, set_video_id=None):
  
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            self.ytmusic.remove_playlist_items(playlist_id, [{'videoId': video_id, 'setVideoId': set_video_id}])
            return True
        except Exception as e:
            print(f"Failed to remove song from playlist: {str(e)}")
            return False
    
    def unlike_song(self, video_id):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            self.ytmusic.rate_song(video_id, 'INDIFFERENT')  # This removes the like
            return True
        except Exception as e:
            print(f"Failed to unlike song: {str(e)}")
            return False
    
    def get_liked_songs(self, limit=None):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        try:
            liked_songs = self.ytmusic.get_liked_songs(limit=limit)
            return liked_songs.get('tracks', [])
        except Exception as e:
            print(f"Failed to get liked songs: {str(e)}")
            return []
    
    def search_multiple_queries(self, queries, filter_type="songs"):
        if not self.ytmusic:
            raise Exception("Not authenticated with YouTube Music")
        
        results = []
        for query in queries:
            try:
                search_results = self.ytmusic.search(query, filter=filter_type, limit=3)
                if search_results:
                    results.extend(search_results)
            except Exception as e:
                print(f"Search error for '{query}': {str(e)}")
                continue
        
        return results
