import time
import json
from datetime import datetime
from .spotify_service import SpotifyClient
from .youtube_service import YouTubeClient
from utils import log_message
from . import gai
import redis
from config import Config

class TransferManager:
    def __init__(self, session_id:str, progress_callback=None):
        self.spotify_client = SpotifyClient(session_id)
        self.youtube_client = YouTubeClient()
        self.progress_callback = progress_callback
        self.transfer_stats = {
            'total_tracks': 0,
            'successful_transfers': 0,
            'failed_transfers': 0,
            'skipped_tracks': 0,
            'transfer_log': [],
            'playlists': [],  
            'current_playlist_index': 0, 
            'processed_tracks': 0  
        }
    
    def authenticate_services(self , session_id:str):
        spotify_success, spotify_message = self.spotify_client.authenticate()
        if not spotify_success:
            return False, f"Spotify: {spotify_message}"
        
        youtube_success, youtube_message = self.youtube_client.authenticate(session_id)
        if not youtube_success:
            return False, f"YouTube Music: {youtube_message}"
        
        return True, "Successfully authenticated with both services"
    
    def get_spotify_playlists(self):
        return self.spotify_client.get_playlist()
    
    def transfer_playlists(self, session_id, selected_playlists, options=None):
        if options is None:
            options = {
                'create_new_playlists': True,
                'overwrite_existing': False,
                'privacy_status': 'PRIVATE'
            }
        
        # Reset counters
        self.transfer_stats = {
            'total_tracks': 0,
            'successful_transfers': 0,
            'failed_transfers': 0,
            'skipped_tracks': 0,
            'transfer_log': [],
            'playlists': selected_playlists,  
            'current_playlist_index': 0, 
            'processed_tracks': 0  
        }
        
        # Cache for created playlists to avoid duplicate creation
        self.created_playlists = {}
        
        # First pass: collect all tracks from all playlists
        all_tracks_data = []
        self._update_progress(session_id, "Collecting tracks from all playlists...")
        
        for playlist in selected_playlists:
            tracks = self.spotify_client.get_playlist_tracks(playlist['id'])
            if tracks:
                for track in tracks:
                    all_tracks_data.append({
                        'track': track,
                        'playlist': playlist,
                        'playlist_id': playlist['id']
                    })
        
        self.transfer_stats['total_tracks'] = len(all_tracks_data)
        self._update_progress(session_id, f"Found {len(all_tracks_data)} total tracks to transfer")
        
        # Second pass: transfer all tracks
        for track_data in all_tracks_data:
            try:
                self.transfer_stats['processed_tracks'] += 1
                track = track_data['track']
                playlist = track_data['playlist']
                
                self._update_progress(
                    session_id,
                    f"Processing track {self.transfer_stats['processed_tracks']}/{self.transfer_stats['total_tracks']}: {track['name']}"
                )
                
                # Handle liked songs differently
                if track_data['playlist_id'] == 'liked_songs':
                    self._transfer_single_liked_song(session_id, track)
                else:
                    self._transfer_single_track_to_playlist(session_id, track, playlist, options)
                
                time.sleep(0.1)
                
            except Exception as e:
                self.transfer_stats['failed_transfers'] += 1
                log_message(f"✗ Error processing {track['name']}: {str(e)}")

        self._update_progress(session_id, "Transfer complete!")
        return self._generate_transfer_report()
    
    def _transfer_single_liked_song(self, session_id, track):
        """Transfer a single track to liked songs"""
        try:
            youtube_track, similarity = self.youtube_client.search_song(
                session_id,
                track['name'], 
                ', '.join(track['artists']),
                track['album']
            )
            
            if youtube_track:
                if self.youtube_client.add_song_to_liked(session_id, youtube_track['videoId']):
                    self.transfer_stats['successful_transfers'] += 1
                    log_message(f"✓ Liked: {track['name']} by {', '.join(track['artists'])}")
                else:
                    self.transfer_stats['failed_transfers'] += 1
                    log_message(f"✗ Failed to like: {track['name']}")
            else:
                self.transfer_stats['failed_transfers'] += 1
                log_message(f"✗ Not found: {track['name']} by {', '.join(track['artists'])}")
                
        except Exception as e:
            self.transfer_stats['failed_transfers'] += 1
            log_message(f"✗ Error processing liked song {track['name']}: {str(e)}")

    def _transfer_single_track_to_playlist(self, session_id, track, playlist, options):
        """Transfer a single track to a specific playlist"""
        try:
            playlist_name = playlist['name']
            
            # Check if we already have this playlist ID cached
            if playlist_name not in self.created_playlists:
                youtube_playlist_id = self._get_or_create_youtube_playlist(session_id, playlist, options)
                if not youtube_playlist_id:
                    self.transfer_stats['failed_transfers'] += 1
                    return
                # Cache the playlist ID
                self.created_playlists[playlist_name] = youtube_playlist_id
            else:
                youtube_playlist_id = self.created_playlists[playlist_name]
            
            # Search for the track
            youtube_track, similarity = self.youtube_client.search_song(
                "reg",
                session_id,
                track['name'],
                ', '.join(track['artists']),
                track['album']
            )

            # Fallback to AI search if regular search fails
            if not youtube_track:
                log_message(f"Initial search failed, trying AI fallback for: {track['name']}")
                ai_song_title = gai.get_song(track['name'], ', '.join(track['artists']))
                
                if ai_song_title != "No result found":
                    youtube_track, similarity = self.youtube_client.search_song(
                        "ai",
                        session_id,
                        ai_song_title,
                        ', '.join(track['artists']),
                        track['album']
                    )

            # Add to playlist
            if youtube_track:
                if self.youtube_client.add_song_to_playlist(session_id, youtube_playlist_id, youtube_track['videoId']):
                    self.transfer_stats['successful_transfers'] += 1
                    log_message(f"Added: {track['name']} by {', '.join(track['artists'])}")
                else:
                    self.transfer_stats['failed_transfers'] += 1
                    log_message(f"Failed to add: {track['name']}")
            else:
                self.transfer_stats['failed_transfers'] += 1
                log_message(f"Not found: {track['name']} by {', '.join(track['artists'])}")
                
        except Exception as e:
            self.transfer_stats['failed_transfers'] += 1
            log_message(f"✗ Error processing track {track['name']}: {str(e)}")

    def _get_or_create_youtube_playlist(self, session_id, playlist, options):
        """Get existing or create new YouTube playlist"""
        playlist_name = playlist['name']
        
        # Check if playlist exists
        exists, existing_id = self.youtube_client.playlist_exists(session_id, playlist_name)
        
        if exists and not options.get('overwrite_existing', False):
            log_message(f"Playlist '{playlist_name}' already exists. Using existing.")
            return existing_id
        
        try:
            if exists and options.get('overwrite_existing', False):
                return existing_id
            else:
                return self.youtube_client.create_playlist(
                    session_id=session_id,
                    name=playlist_name,
                    description=playlist.get('description', ''),
                    privacy_status=options.get('privacy_status', 'PRIVATE')
                )
        except Exception as e:
            log_message(f"Failed to create playlist '{playlist_name}': {str(e)}")
            return None
    
    def _update_progress(self, session_id, message):
        print("update")
        r = redis.Redis.from_url(Config.REDIS)
    
        total_tracks = self.transfer_stats.get('total_tracks', 0)
        processed_tracks = self.transfer_stats.get('processed_tracks', 0)
        
        # Debug logging
        print(f"DEBUG: total_tracks={total_tracks}, processed_tracks={processed_tracks}")
        
        # Calculate progress
        if total_tracks > 0:
            # Simple calculation: processed tracks / total tracks * 100
            total_progress = (processed_tracks / total_tracks) * 100
        else:
            # If no total tracks yet, show 0% progress
            total_progress = 0.0
            
        total_progress = round(total_progress, 2)
        total_progress = min(total_progress, 100)
        
        # Debug logging
        print(f"DEBUG: Setting progress to {total_progress}% in Redis")
        
        # Always set progress in Redis
        r.set(session_id, total_progress)
        
        message = f"{message} (Overall Progress: {total_progress}%)"

        if self.progress_callback:
            self.progress_callback(message)
        else:
            print(f"Progress: {message}")
    
    def _generate_transfer_report(self):
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tracks': self.transfer_stats['total_tracks'],
                'successful_transfers': self.transfer_stats['successful_transfers'],
                'failed_transfers': self.transfer_stats['failed_transfers'],
                'success_rate': (self.transfer_stats['successful_transfers'] / 
                               max(self.transfer_stats['total_tracks'], 1)) * 100
            },
            'details': self.transfer_stats['transfer_log']
        }
        
        with open(f"transfer_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
