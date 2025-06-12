import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
from .launch_spotify import launch_spotify

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
                try:
                    self.spotify.start_playback(uris=[track['uri']])
                except spotipy.SpotifyException as e:
                    if 'No active device' in str(e):
                        if self.notifier:
                            self.notifier.send_notification(
                                "❌ Spotify Not Running",
                                "Spotify is not running on any device. Launching Spotify on this device...",
                                "dialog-warning",
                                "normal",
                                5000
                            )
                        if launch_spotify():
                            import time
                            # Poll for device readiness (up to 3 seconds, check every 0.3s)
                            device_id = None
                            for _ in range(10):
                                devices = self.spotify.devices()
                                for d in devices.get('devices', []):
                                    if d.get('is_active') or d.get('type') == 'Computer':
                                        device_id = d['id']
                                        break
                                if device_id:
                                    break
                                time.sleep(0.3)
                            if device_id:
                                try:
                                    self.spotify.transfer_playback(device_id, force_play=True)
                                    # Wait briefly for transfer, then play requested song
                                    time.sleep(0.5)
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
                                if self.notifier:
                                    self.notifier.send_notification(
                                        "❌ Device Not Found",
                                        "Could not find a Spotify device to transfer playback.",
                                        "dialog-error"
                                    )
                                return
                        else:
                            if self.notifier:
                                self.notifier.send_notification(
                                    "❌ Spotify Launch Failed",
                                    "Could not launch Spotify desktop app. Please start it manually.",
                                    "dialog-error"
                                )
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

    def resume_playback(self):
        try:
            try:
                self.spotify.start_playback()
            except spotipy.SpotifyException as e:
                if 'No active device' in str(e):
                    if self.notifier:
                        self.notifier.send_notification(
                            "❌ Spotify Not Running",
                            "Spotify is not running on any device. Launching Spotify on this device...",
                            "dialog-warning",
                            "normal",
                            5000
                        )
                    if launch_spotify():
                        import time
                        device_id = None
                        for _ in range(10):
                            devices = self.spotify.devices()
                            for d in devices.get('devices', []):
                                if d.get('is_active') or d.get('type') == 'Computer':
                                    device_id = d['id']
                                    break
                            if device_id:
                                break
                            time.sleep(0.3)
                        if device_id:
                            try:
                                self.spotify.transfer_playback(device_id, force_play=True)
                                time.sleep(0.5)
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
                            if self.notifier:
                                self.notifier.send_notification(
                                    "❌ Device Not Found",
                                    "Could not find a Spotify device to transfer playback.",
                                    "dialog-error"
                                )
                            return
                    else:
                        if self.notifier:
                            self.notifier.send_notification(
                                "❌ Spotify Launch Failed",
                                "Could not launch Spotify desktop app. Please start it manually.",
                                "dialog-error"
                            )
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

    # All Spotify control methods will be moved here from EnhancedVoiceAssistant
    # e.g. play_song, resume_playback, pause_playback, next_track, previous_track, adjust_volume, get_current_track
