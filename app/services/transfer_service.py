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
        
        self.transfer_stats['playlists'] = selected_playlists
        self.transfer_stats['current_playlist_index'] = 0
        self.transfer_stats['transfer_log'] = []
        
        for i, playlist in enumerate(selected_playlists):
            try:
                self.transfer_stats['current_playlist_index'] = i
                self.transfer_stats['processed_tracks'] = 0
                self._update_progress(session_id,f"Starting playlist: {playlist['name']}")
                
                success = self._transfer_single_playlist(session_id, playlist, options)
                
                if success:
                    log_message(f"Successfully transferred playlist: {playlist['name']}")
                else:
                    log_message(f"Failed to transfer playlist: {playlist['name']}")
                
            except Exception as e:
                log_message(f"Error transferring playlist {playlist['name']}: {str(e)}")
                continue

        self._update_progress(session_id,"Transfer complete!")
        return self._generate_transfer_report()
    
    def _transfer_single_playlist(self,session_id, playlist, options):
        playlist_name = playlist['name']
        playlist_id = playlist['id']
        
        self._update_progress(session_id,f"Fetching tracks from {playlist_name}...")
        tracks = self.spotify_client.get_playlist_tracks(playlist_id)
        
        if not tracks:
            log_message(f"No tracks found in playlist: {playlist_name}")
            return False
        
        self.transfer_stats['total_tracks'] += len(tracks)
        
        if playlist_id == 'liked_songs':
            return self._transfer_liked_songs(session_id,tracks)
        
        exists, existing_id = self.youtube_client.playlist_exists(session_id,playlist_name)
        
        if exists and not options.get('overwrite_existing', False):
            log_message(f"Playlist '{playlist_name}' already exists. Skipping.")
            return False
        
        try:
            if exists and options.get('overwrite_existing', False):
                youtube_playlist_id = existing_id
                log_message(f"Using existing playlist: {playlist_name}")
            else:
                youtube_playlist_id = self.youtube_client.create_playlist(
                    session_id=session_id,
                    name=playlist_name,
                    description=playlist.get('description', ''),
                    privacy_status=options.get('privacy_status', 'PRIVATE')
                )
                log_message(f"Created playlist: {playlist_name}")
            
        except Exception as e:
            log_message(f"Failed to create playlist '{playlist_name}': {str(e)}")
            return False
        
        return self._transfer_tracks_to_playlist(session_id,tracks, youtube_playlist_id, playlist_name)
    
    def _transfer_liked_songs(self,session_id, tracks):
        self._update_progress(session_id,"Transferring liked songs...")
        
        successful = 0
        failed = 0
        
        for i, track in enumerate(tracks):
            try:
                self._update_progress(
                    session_id,
                    f"Processing liked song {i+1}/{len(tracks)}: {track['name']}"
                )
                
                youtube_track, similarity = self.youtube_client.search_song(
                    session_id,
                    track['name'], 
                    ', '.join(track['artists']),
                    track['album']
                )
                
                if youtube_track:
                    if self.youtube_client.add_song_to_liked(session_id,youtube_track['videoId']):
                        successful += 1
                        self.transfer_stats['successful_transfers'] += 1
                        log_message(f"✓ Liked: {track['name']} by {', '.join(track['artists'])}")
                    else:
                        failed += 1
                        self.transfer_stats['failed_transfers'] += 1
                        log_message(f"✗ Failed to like: {track['name']}")
                else:
                    failed += 1
                    self.transfer_stats['failed_transfers'] += 1
                    log_message(f"✗ Not found: {track['name']} by {', '.join(track['artists'])}")
                
                time.sleep(0.1)
                
            except Exception as e:
                failed += 1
                self.transfer_stats['failed_transfers'] += 1
                log_message(f"✗ Error processing {track['name']}: {str(e)}")
        
        log_message(f"Liked Songs transfer complete: {successful} successful, {failed} failed")
        return successful > 0
    
    def _transfer_tracks_to_playlist(self, session_id, tracks, youtube_playlist_id, playlist_name):
        successful = 0
        failed = 0

        for i, track in enumerate(tracks):
            try:
                self._update_progress(

                    session_id,
                    f"Processing track {i+1}/{len(tracks)}: {track['name']}"
                )

                youtube_track, similarity = self.youtube_client.search_song(
                    "reg",
                    session_id,
                    track['name'],
                    ', '.join(track['artists']),
                    track['album']
                )

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
                        print(youtube_track , " " , similarity)

                if youtube_track:
                    if self.youtube_client.add_song_to_playlist(session_id, youtube_playlist_id, youtube_track['videoId']):
                        successful += 1
                        self.transfer_stats['successful_transfers'] += 1
                        log_message(f"Added: {track['name']} by {', '.join(track['artists'])}")
                    else:
                        failed += 1
                        self.transfer_stats['failed_transfers'] += 1
                        log_message(f"Failed to add: {track['name']}")
                else:
                    failed += 1
                    self.transfer_stats['failed_transfers'] += 1
                    log_message(f"Not found: {track['name']} by {', '.join(track['artists'])}")

                time.sleep(0.1)

            except Exception as e:
                failed += 1
                self.transfer_stats['failed_transfers'] += 1
                log_message(f"✗ Error processing {track['name']}: {str(e)}")

        log_message(f"Playlist '{playlist_name}' transfer complete: {successful} successful, {failed} failed")

        return {
            'successful': successful,
            'failed': failed
        }

    
    def _update_progress(self, session_id, message):
        print("update")
        r = redis.Redis.from_url(Config.REDIS)
    
        total_playlists = len(self.transfer_stats.get('playlists', []))
        current_playlist_index = self.transfer_stats.get('current_playlist_index', 0)
        total_tracks = self.transfer_stats.get('total_tracks', 0)
        processed_tracks = self.transfer_stats.get('processed_tracks', 0)
            
        if total_playlists > 0:
            playlist_weight = 1.0 / total_playlists
            playlist_progress = (processed_tracks / total_tracks) if total_tracks > 0 else 0
            total_progress = ((current_playlist_index * playlist_weight) + 
                            (playlist_progress * playlist_weight)) * 100
            
            total_progress = round(total_progress, 2)
            total_progress = min(total_progress, 100)
            
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
