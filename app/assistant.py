import os
import logging
from logging.handlers import RotatingFileHandler
from .spotify_control import SpotifyController
from .audio import AudioManager
from .notifications import NotificationManager
from .utils import load_environment

# Set up rotating log handler (1MB per file, keep 5 backups)
log_dir = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'voice_assistant.log')
handler = RotatingFileHandler(log_file, maxBytes=1_048_576, backupCount=5)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])

class EnhancedVoiceAssistant:

    def __init__(self):
        load_environment()
        self.notifier = NotificationManager()
        self.calibration_file = os.path.join(os.path.dirname(__file__), '../calibration/.voice_calibration.json')
        self.wake_word = os.getenv('WAKE_WORD', 'jarvis')
        self.audio_manager = AudioManager(
            calibration_file=self.calibration_file,
            notifier=self.notifier,
            wake_word=self.wake_word
        )
        self.spotify_controller = SpotifyController(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
            redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8080/callback'),
            cache_path=os.path.join(os.path.dirname(__file__), '../cache/.spotify_cache'),
            notifier=self.notifier
        )
        self.is_running = True
        self.is_awake = False
        self.switch_to_text_mode = False  # Flag for switching to text mode
        logging.info("EnhancedVoiceAssistant initialized.")

    def run(self):
        import signal
        self.audio_manager.setup_enhanced_audio()
        self.notifier.send_notification(
            "😴 Wake Word Mode Active",
            f"Say '{self.wake_word}' to wake me up! I'll sleep between commands to save resources.",
            "audio-input-microphone",
            "normal",
            8000
        )
        def handle_sigterm(signum, frame):
            logging.info(f"Received shutdown signal ({signum}). Shutting down gracefully.")
            self.is_running = False
        def handle_sigint(signum, frame):
            logging.info("SIGINT received: switching to text mode.")
            self.switch_to_text_mode = True
        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigint)
        try:
            while self.is_running:
                if self.switch_to_text_mode:
                    self.switch_to_text_mode = False
                    self.text_mode_loop()
                    self.notifier.send_notification(
                        "😴 Wake Word Mode Active",
                        f"Say '{self.wake_word}' to wake me up! I'll sleep between commands to save resources.",
                        "audio-input-microphone",
                        "normal",
                        8000
                    )
                    continue
                if not self.is_awake:
                    if self.audio_manager.listen_for_wake_word():
                        self.is_awake = True
                        self.notifier.send_notification(
                            "👂 Assistant Awakened",
                            "Wake word detected! Ready for command.",
                            "audio-input-microphone",
                            "normal",
                            4000
                        )
                        command = self.audio_manager.listen_for_command()
                        if command:
                            self.process_command(command)
                            self.is_awake = False
                        else:
                            self.is_awake = False
                else:
                    self.is_awake = False
        except Exception as e:
            logging.error(f"Error in main loop: {e}")

    def text_mode_loop(self):
        print("\n📝 TEXT MODE: Type commands or 'voice' to return to voice mode")
        try:
            while self.is_running:
                user_input = input("text> ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.notifier.send_notification("👋 Enhanced Assistant Stopping", "Shutting down", "application-exit", "low", 3000)
                    self.is_running = False
                    break
                elif user_input.lower() == 'voice':
                    print("🎤 Returning to voice mode...")
                    break
                elif user_input.lower() == 'help':
                    self.show_enhanced_tips()
                elif user_input.lower() == 'wake':
                    self.change_wake_word()
                elif user_input.lower() == 'recalibrate':
                    print("🔄 Forcing voice recalibration...")
                    self.audio_manager.enhanced_calibration()
                    print("🎤 Returning to voice mode after calibration...")
                    break
                elif user_input:
                    self.process_command(user_input)
                else:
                    print("💡 Empty input. Type 'help' for commands or 'voice' to switch modes")
        except KeyboardInterrupt:
            print("\n🎤 Returning to voice mode...")

    def change_wake_word(self):
        print(f"\nCurrent wake word: '{self.wake_word}'")
        print("Enter new wake word (or press Enter to keep current):")
        new_wake_word = input("wake word> ").strip()
        if new_wake_word:
            self.wake_word = new_wake_word.lower()
            self.audio_manager.wake_word = self.wake_word
            print(f"✅ Wake word changed to: '{self.wake_word}'")
            self.notifier.send_notification(
                "🔄 Wake Word Changed",
                f"New wake word: '{self.wake_word}'\nSay this to wake the assistant.",
                "dialog-information",
                "normal",
                5000
            )
            # Save to calibration file
            try:
                import json
                if os.path.exists(self.calibration_file):
                    with open(self.calibration_file, 'r') as f:
                        data = json.load(f)
                    data['wake_word'] = self.wake_word
                    with open(self.calibration_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"✅ Wake word saved to calibration file")
            except Exception as e:
                print(f"⚠️ Could not save wake word: {e}")
        else:
            print(f"Keeping current wake word: '{self.wake_word}'")

    def show_enhanced_tips(self):
        tips = [
            f"😴 WAKE WORD MODE: Say '{self.wake_word}' to wake me up",
            "👂 I sleep between commands to let you enjoy music",
            "🎤 After wake word, speak your FULL command in ONE sentence",
            "⏱️ Extended pause detection for complete phrases",
            f"🎵 Example: '{self.wake_word}' → 'play Hotel California by Eagles'",
            f"🎵 Example: '{self.wake_word}' → 'play Bohemian Rhapsody by Queen'",
            f"🎵 Example: '{self.wake_word}' → 'pause' or 'next track'",
            "📏 Speak at normal pace, don't rush",
            "🎚️ I'll automatically adjust sensitivity",
            "⌨️ Press Ctrl+C anytime for text mode",
            "🔄 Type 'wake' to change wake word"
        ]
        print("\n💡 Enhanced Voice Recognition Tips:")
        for tip in tips:
            print(f"  {tip}")

    def process_command(self, command):
        command = command.lower().strip()
        if 'play' in command and len(command.split()) > 1:
            song_name = command.split('play', 1)[1].strip()
            song_name = song_name.replace('the song', '').strip()
            song_name = song_name.replace('song called', '').strip()
            song_name = song_name.replace('track', '').strip()
            if song_name:
                self.spotify_controller.play_song(song_name)
                return
        if any(word in command for word in ['play', 'start', 'resume', 'go']):
            self.spotify_controller.resume_playback()
        elif any(word in command for word in ['pause', 'stop', 'halt']):
            self.spotify_controller.pause_playback()
        elif any(word in command for word in ['next', 'skip', 'forward']):
            self.spotify_controller.next_track()
        elif any(word in command for word in ['previous', 'back', 'last']):
            self.spotify_controller.previous_track()
        elif 'volume up' in command or 'louder' in command or 'turn up' in command:
            self.spotify_controller.adjust_volume(15)
        elif 'volume down' in command or 'quieter' in command or 'turn down' in command:
            self.spotify_controller.adjust_volume(-15)
        elif any(word in command for word in ['what', 'playing', 'current', 'now']):
            self.spotify_controller.get_current_track()
        elif any(word in command for word in ['quit', 'exit', 'bye', 'goodbye']):
            self.notifier.send_notification(
                "👋 Enhanced Assistant Stopping",
                "Enhanced Spotify Voice Assistant is shutting down",
                "application-exit",
                "low",
                3000
            )
            self.is_running = False
