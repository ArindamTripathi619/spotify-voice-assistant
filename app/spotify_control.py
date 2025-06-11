import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging

class SpotifyController:
    def __init__(self, client_id, client_secret, redirect_uri, cache_path, notifier=None):
        scope = "user-modify-playback-state,user-read-playback-state,user-read-currently-playing"
        self.spotify_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=cache_path
        )
        self.spotify = spotipy.Spotify(auth_manager=self.spotify_oauth)
        self.spotify.current_user()
        logging.info("Spotify connected successfully.")
        self.notifier = notifier

    def play_song(self, song_name):
        try:
            results = self.spotify.search(q=song_name, type='track', limit=3)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                self.spotify.start_playback(uris=[track['uri']])
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

    def resume_playback(self):
        try:
            self.spotify.start_playback()
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ No Active Device", "Please start Spotify first", "dialog-warning")

    def pause_playback(self):
        try:
            self.spotify.pause_playback()
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ Pause Failed", "Couldn't pause", "dialog-error")

    def next_track(self):
        try:
            self.spotify.next_track()
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ Skip Failed", "Couldn't skip", "dialog-error")

    def previous_track(self):
        try:
            self.spotify.previous_track()
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ Previous Failed", "Couldn't go back", "dialog-error")

    def adjust_volume(self, change):
        try:
            current = self.spotify.current_playback()
            if current and current['device']:
                volume = max(0, min(100, current['device']['volume_percent'] + change))
                self.spotify.volume(volume)
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ Volume Error", "Couldn't adjust", "dialog-error")

    def get_current_track(self):
        try:
            current = self.spotify.current_playback()
            if current and current['is_playing']:
                track = current['item']
                # Optionally notify or return track info
                pass
        except Exception:
            if self.notifier:
                self.notifier.send_notification("❌ Info Error", "Couldn't get info", "dialog-error")

    # All Spotify control methods will be moved here from EnhancedVoiceAssistant
    # e.g. play_song, resume_playback, pause_playback, next_track, previous_track, adjust_volume, get_current_track
