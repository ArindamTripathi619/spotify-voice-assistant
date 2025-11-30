import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
import os
import stat
import json
import time
from functools import wraps
from typing import Optional
from .launch_spotify import launch_spotify

# Import error handling types
try:
    from .error_handling import ErrorHandler
except ImportError:
    ErrorHandler = None


class AuthenticationError(Exception):
    """Raised when Spotify authentication fails."""
    pass


class ConnectionError(Exception):
    """Raised when Spotify connection fails."""
    pass


class SecureTokenStorage:
    """Encrypted token storage for Spotify OAuth tokens."""
    
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, mode=0o700, exist_ok=True)  # Owner-only permissions
        self.key_file = os.path.join(cache_dir, '.key')
        self.token_file = os.path.join(cache_dir, '.spotify_tokens.enc')
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Set up encryption using cryptography.fernet."""
        try:
            from cryptography.fernet import Fernet
            
            if os.path.exists(self.key_file):
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                os.chmod(self.key_file, 0o600)  # Owner read/write only
            
            self.cipher = Fernet(key)
        except ImportError:
            logging.warning("cryptography not available, falling back to basic protection")
            self.cipher = None
    
    def get_cached_token(self):
        """Retrieve and decrypt cached token (spotipy interface)."""
        if not os.path.exists(self.token_file):
            return None
        
        try:
            with open(self.token_file, 'rb') as f:
                encrypted_data = f.read()
            
            if self.cipher:
                decrypted_data = self.cipher.decrypt(encrypted_data)
                return json.loads(decrypted_data.decode('utf-8'))
            else:
                # Fallback for when cryptography is not available
                return json.loads(encrypted_data.decode('utf-8'))
                
        except Exception as e:
            logging.warning(f"Failed to read cached token: {e}")
            return None
    
    def save_token_to_cache(self, token_info):
        """Encrypt and save token to cache (spotipy interface)."""
        try:
            token_data = json.dumps(token_info).encode('utf-8')
            
            if self.cipher:
                encrypted_data = self.cipher.encrypt(token_data)
            else:
                # Fallback for when cryptography is not available
                encrypted_data = token_data
                logging.warning("Saving token without encryption - install cryptography package for security")
            
            with open(self.token_file, 'wb') as f:
                f.write(encrypted_data)
            os.chmod(self.token_file, 0o600)  # Owner read/write only
            
        except Exception as e:
            logging.error(f"Failed to save token: {e}")


class SpotifyRateLimiter:
    """Rate limiter for Spotify API calls."""
    
    def __init__(self, calls_per_second=8):  # Conservative limit
        self.calls_per_second = calls_per_second
        self.last_call_time = 0
        self.min_interval = 1.0 / calls_per_second
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            time_since_last = now - self.last_call_time
            
            if time_since_last < self.min_interval:
                time.sleep(self.min_interval - time_since_last)
                
            self.last_call_time = time.time()
            try:
                return func(*args, **kwargs)
            except spotipy.SpotifyException as e:
                if e.http_status == 429:  # Rate limited
                    retry_after = int(e.headers.get('Retry-After', 60))
                    logging.warning(f"Spotify rate limit hit, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    return func(*args, **kwargs)
                raise
        return wrapper

class SpotifyController:
    def __init__(self, client_id, client_secret, redirect_uri, cache_path, notifier=None):
        scope = "user-modify-playback-state,user-read-playback-state,user-read-currently-playing"
        
        # Initialize components
        self.notifier = notifier
        self.error_handler = None  # Will be assigned by VoiceAssistant
        
        # Use secure token storage with encryption
        cache_dir = os.path.dirname(cache_path)
        self.secure_token_storage = SecureTokenStorage(cache_dir)
        
        # Create custom SpotifyOAuth that uses our secure storage
        self.spotify_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_handler=self.secure_token_storage
        )
        
        # Rate limiter for API calls
        self.rate_limiter = SpotifyRateLimiter(calls_per_second=8)
        
        self.spotify = spotipy.Spotify(auth_manager=self.spotify_oauth)
        
        # Verify credentials with error handling
        try:
            user_info = self.spotify.current_user()
            logging.info(f"Spotify connected successfully for user: {user_info.get('display_name', 'Unknown')}")
        except spotipy.SpotifyException as e:
            error_msg = f"Spotify authentication failed: {e}"
            logging.error(error_msg)
            if notifier:
                notifier.send_notification("🚫 Spotify Auth Error", error_msg, "dialog-error", "critical", 0)
            raise AuthenticationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during Spotify connection: {e}"
            logging.error(error_msg)
            if notifier:
                notifier.send_notification("💥 Spotify Connection Error", error_msg, "dialog-error", "critical", 0)
            raise ConnectionError(error_msg) from e
        
        self.notifier = notifier

    @SpotifyRateLimiter(calls_per_second=6)
    def play_song(self, song_name):
        try:
            results = self.spotify.search(q=song_name, type='track', limit=3)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                try:
                    self.spotify.start_playback(uris=[track['uri']])
                except spotipy.SpotifyException as e:
                    if 'No active device' in str(e):
                        device_id = self._handle_no_active_device("song playback")
                        if device_id:
                            try:
                                self.spotify.start_playback(uris=[track['uri']], device_id=device_id)
                            except Exception as e2:
                                if self.notifier:
                                    self.notifier.send_notification(
                                        "❌ Playback Error",
                                        f"Failed to play after launching and transferring: {song_name}",
                                        "dialog-error"
                                    )
                                return
                        else:
                            return
                    else:
                        if self.notifier:
                            self.notifier.send_notification(
                                "❌ Playback Error",
                                f"Failed to play: {song_name}",
                                "dialog-error"
                            )
                        return
                if self.notifier:
                    self.notifier.send_notification(
                        "🎵 Now Playing (Enhanced)",
                        f"🎤 Search: '{song_name}'\n🎵 Found: {track['name']}\n👨‍🎤 Artist: {track['artists'][0]['name']}",
                        "audio-volume-high",
                        "normal",
                        6000
                    )
            else:
                if self.notifier:
                    self.notifier.send_notification(
                        "❌ Song Not Found",
                        f"No results for: '{song_name}'\nTry being more specific or check spelling",
                        "dialog-warning",
                        "normal",
                        5000
                    )
        except Exception as e:
            if self.notifier:
                self.notifier.send_notification(
                    "❌ Playback Error",
                    f"Failed to play: {song_name}",
                    "dialog-error"
                )

    @SpotifyRateLimiter(calls_per_second=6)
    def resume_playback(self):
        try:
            try:
                self.spotify.start_playback()
            except spotipy.SpotifyException as e:
                if 'No active device' in str(e):
                    device_id = self._handle_no_active_device("resume playback")
                    if device_id:
                        try:
                            self.spotify.start_playback(device_id=device_id)
                        except Exception as e2:
                            if self.notifier:
                                self.notifier.send_notification(
                                    "❌ Playback Error",
                                    "Failed to resume after launching and transferring.",
                                    "dialog-error"
                                )
                            return
                    else:
                        return
                else:
                    if self.notifier:
                        self.notifier.send_notification(
                            "❌ Playback Error",
                            "Failed to resume playback.",
                            "dialog-error"
                        )
                    return
            if self.notifier:
                self.notifier.send_notification(
                    "▶️ Playback Resumed",
                    "Spotify playback resumed.",
                    "audio-x-generic",
                    "normal",
                    3000
                )
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ No Active Device", "Please start Spotify first", "dialog-warning")

    @SpotifyRateLimiter(calls_per_second=6)
    def pause_playback(self):
        try:
            self.spotify.pause_playback()
            if self.notifier:
                self.notifier.send_notification(
                    "⏸️ Playback Paused",
                    "Spotify playback paused.",
                    "audio-x-generic",
                    "normal",
                    3000
                )
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ Pause Failed", "Couldn't pause", "dialog-error")

    @SpotifyRateLimiter(calls_per_second=6)
    def next_track(self):
        try:
            self.spotify.next_track()
            # After skipping, fetch and notify the new track info
            current = self.spotify.current_playback()
            if current and current['is_playing']:
                track = current['item']
                name = track['name']
                artist = track['artists'][0]['name']
                album = track['album']['name']
                if self.notifier:
                    self.notifier.send_notification(
                        "⏭️ Next Track",
                        f"{name}\nby {artist}\nAlbum: {album}",
                        "audio-x-generic",
                        "normal",
                        6000
                    )
        except Exception as e:
            msg = str(e)
            if self.notifier:
                if 'Restriction violated' in msg:
                    self.notifier.send_notification(
                        "❌ Skip Failed",
                        "Spotify cannot skip track on this device. Try using the official Spotify app.",
                        "dialog-error"
                    )
                else:
                    self.notifier.send_notification("❌ Skip Failed", msg, "dialog-error")

    @SpotifyRateLimiter(calls_per_second=6)
    def previous_track(self):
        try:
            self.spotify.previous_track()
            # After going to previous, fetch and notify the new track info
            current = self.spotify.current_playback()
            if current and current['is_playing']:
                track = current['item']
                name = track['name']
                artist = track['artists'][0]['name']
                album = track['album']['name']
                if self.notifier:
                    self.notifier.send_notification(
                        "⏮️ Previous Track",
                        f"{name}\nby {artist}\nAlbum: {album}",
                        "audio-x-generic",
                        "normal",
                        6000
                    )
        except Exception as e:
            msg = str(e)
            if self.notifier:
                if 'Restriction violated' in msg:
                    self.notifier.send_notification(
                        "❌ Previous Failed",
                        "Spotify cannot go to previous track on this device. Try using the official Spotify app.",
                        "dialog-error"
                    )
                else:
                    self.notifier.send_notification("❌ Previous Failed", msg, "dialog-error")

    @SpotifyRateLimiter(calls_per_second=6)
    def adjust_volume(self, change):
        try:
            current = self.spotify.current_playback()
            if current and current['device']:
                volume = max(0, min(100, current['device']['volume_percent'] + change))
                self.spotify.volume(volume)
        except Exception as e:
            msg = str(e)
            if self.notifier:
                if 'Cannot control device volume' in msg:
                    self.notifier.send_notification(
                        "❌ Volume Error",
                        "Cannot control volume on this device. Try using the official Spotify app.",
                        "dialog-error"
                    )
                else:
                    self.notifier.send_notification("❌ Volume Error", msg, "dialog-error")

    @SpotifyRateLimiter(calls_per_second=6)
    def get_current_track(self):
        try:
            current = self.spotify.current_playback()
            if current and current['is_playing']:
                track = current['item']
                name = track['name']
                artist = track['artists'][0]['name']
                album = track['album']['name']
                if self.notifier:
                    self.notifier.send_notification(
                        "🎵 Now Playing",
                        f"{name}\nby {artist}\nAlbum: {album}",
                        "audio-x-generic",
                        "normal",
                        6000
                    )
                else:
                    print(f"Now playing: {name} by {artist} (Album: {album})")
            else:
                if self.notifier:
                    self.notifier.send_notification(
                        "⏸️ Not Playing",
                        "No track is currently playing.",
                        "audio-x-generic",
                        "normal",
                        4000
                    )
                else:
                    print("No track is currently playing.")
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ Info Error", "Couldn't get info", "dialog-error")
            else:
                print("Couldn't get current track info.")

    def _find_active_device(self):
        """Find an active Spotify device or suitable computer device."""
        devices = self.spotify.devices()
        for device in devices.get('devices', []):
            if device.get('is_active') or device.get('type') == 'Computer':
                return device['id']
        return None
    
    def _launch_and_setup_device(self):
        """Launch Spotify and set up device for playback."""
        if not launch_spotify():
            if self.notifier:
                self.notifier.send_notification(
                    "❌ Spotify Launch Failed",
                    "Could not launch Spotify desktop app. Please start it manually.",
                    "dialog-error"
                )
            return None
        
        import time
        # Poll for device readiness (up to 3 seconds, check every 0.3s)
        device_id = None
        for _ in range(10):
            device_id = self._find_active_device()
            if device_id:
                break
            time.sleep(0.3)
        
        if device_id:
            try:
                self.spotify.transfer_playback(device_id, force_play=True)
                time.sleep(0.5)  # Wait for transfer
                return device_id
            except Exception as e:
                if self.notifier:
                    self.notifier.send_notification(
                        "❌ Transfer Error",
                        "Failed to transfer playback to device.",
                        "dialog-error"
                    )
                return None
        else:
            if self.notifier:
                self.notifier.send_notification(
                    "❌ Device Not Found",
                    "Could not find a Spotify device to transfer playback.",
                    "dialog-error"
                )
            return None
    
    def _handle_no_active_device(self, action_name="playback"):
        """Handle the common case of no active device with launch and setup."""
        if self.notifier:
            self.notifier.send_notification(
                "❌ Spotify Not Running",
                "Spotify is not running on any device. Launching Spotify on this device...",
                "dialog-warning",
                "normal",
                5000
            )
        
        device_id = self._launch_and_setup_device()
        if not device_id:
            if self.notifier:
                self.notifier.send_notification(
                    "❌ Setup Failed",
                    f"Failed to set up device for {action_name}.",
                    "dialog-error"
                )
        return device_id
    
    def cleanup(self):
        """Cleanup resources and perform shutdown operations."""
        try:
            # Clear any cached tokens
            if hasattr(self.spotify_oauth, 'cache_path') and os.path.exists(self.spotify_oauth.cache_path):
                os.remove(self.spotify_oauth.cache_path)
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, "Failed to cleanup Spotify cache")
    
    # All Spotify control methods will be moved here from EnhancedVoiceAssistant
    # e.g. play_song, resume_playback, pause_playback, next_track, previous_track, adjust_volume, get_current_track
