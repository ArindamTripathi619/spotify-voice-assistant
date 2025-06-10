#!/usr/bin/env python3
"""
Enhanced Spotify Voice Assistant
Optimized for capturing complete song names and longer phrases
"""

import os
import time
import subprocess
import speech_recognition as sr
import pyttsx3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from colorama import init, Fore, Style
import threading
import queue
import json
from datetime import datetime, timedelta

init(autoreset=True)

class EnhancedVoiceAssistant:
    def __init__(self):
        load_dotenv()
        self.calibration_file = ".voice_calibration.json"
        
        # Send startup notification immediately
        self.setup_notifications()
        self.send_notification(
            "🚀 Enhanced Spotify Assistant Starting", 
            "Initializing enhanced voice recognition...\nBackground mode ready!",
            "application-x-executable",
            "normal",
            5000
        )
        
        self.setup_spotify()
        self.setup_enhanced_audio()
        self.is_running = True
        self.success_count = 0
        self.attempt_count = 0
        self.wake_word = "jarvis"  # Default wake word
        self.is_awake = False  # Start in sleep mode
        self.wake_word_timeout = 30  # Listen for wake word for 30 seconds
        
        print(f"{Fore.GREEN}🎵 Enhanced Voice Assistant Ready!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📢 Optimized for complete song name capture{Style.RESET_ALL}")
        
        # Send final ready notification
        self.send_notification(
            "✅ Enhanced Spotify Assistant Ready", 
            "All systems initialized!\nPress Enter for voice commands or run in background.",
            "audio-volume-high",
            "normal",
            6000
        )
    
    def setup_spotify(self):
        """Initialize Spotify API"""
        try:
            client_id = os.getenv('SPOTIFY_CLIENT_ID')
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
            redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:8080/callback')
            
            scope = "user-modify-playback-state,user-read-playback-state,user-read-currently-playing"
            
            self.spotify_oauth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
                cache_path=".spotify_cache"
            )
            
            self.spotify = spotipy.Spotify(auth_manager=self.spotify_oauth)
            self.spotify.current_user()
            print(f"{Fore.GREEN}✅ Spotify connected{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Spotify setup failed: {e}{Style.RESET_ALL}")
            self.send_notification(
                "❌ Spotify Error", 
                f"Failed to connect to Spotify: {str(e)[:50]}...",
                "dialog-error"
            )
            raise
    
    def setup_enhanced_audio(self):
        """Setup audio with maximum optimization for long phrases"""
        try:
            self.recognizer = sr.Recognizer()
            
            # Find best microphone
            self.select_best_microphone()
            
            # ENHANCED settings specifically for longer phrases
            self.recognizer.energy_threshold = 200  # Lower threshold for sensitivity
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.dynamic_energy_adjustment_damping = 0.1  # More responsive
            self.recognizer.dynamic_energy_ratio = 1.2  # Less aggressive
            
            # CRITICAL: Extended pause threshold for complete phrases
            self.recognizer.pause_threshold = 1.0  # Wait 1 second for pauses
            self.recognizer.phrase_threshold = 0.2  # More sensitive to start of speech
            self.recognizer.non_speaking_duration = 0.5  # Less aggressive silence detection
            self.recognizer.operation_timeout = None
            
            # Initialize TTS
            self.tts = pyttsx3.init()
            self.tts.setProperty('rate', 160)
            self.tts.setProperty('volume', 0.9)
            
            # Enhanced calibration with persistence
            self.smart_calibration()
            
            print(f"{Fore.GREEN}✅ Enhanced audio setup for long phrases complete{Style.RESET_ALL}")
            print(f"{Fore.CYAN}🎛️ Pause threshold: {self.recognizer.pause_threshold}s{Style.RESET_ALL}")
            print(f"{Fore.CYAN}🎚️ Energy threshold: {self.recognizer.energy_threshold}{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ Audio setup failed: {e}{Style.RESET_ALL}")
            self.send_notification(
                "❌ Audio Error", 
                f"Failed to setup audio: {str(e)[:50]}...",
                "dialog-error"
            )
            raise
    
    def select_best_microphone(self):
        """Find and select the best available microphone"""
        print(f"{Fore.YELLOW}🎤 Scanning for microphones...{Style.RESET_ALL}")
        
        # List all microphones
        mic_list = sr.Microphone.list_microphone_names()
        print(f"{Fore.CYAN}📱 Available microphones:{Style.RESET_ALL}")
        for i, name in enumerate(mic_list):
            print(f"  {i}: {name}")
        
        # Try to select the default microphone first
        try:
            self.microphone = sr.Microphone()
            print(f"{Fore.GREEN}✅ Using default microphone{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Default microphone failed: {e}{Style.RESET_ALL}")
            # Try the first available microphone
            if mic_list:
                try:
                    self.microphone = sr.Microphone(device_index=0)
                    print(f"{Fore.GREEN}✅ Using microphone: {mic_list[0]}{Style.RESET_ALL}")
                except Exception as e2:
                    print(f"{Fore.RED}❌ All microphones failed: {e2}{Style.RESET_ALL}")
                    raise
    
    def load_calibration_data(self):
        """Load previously saved calibration data"""
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                
                # Check if calibration is recent (within 7 days)
                calibration_date = datetime.fromisoformat(data.get('date', '2000-01-01'))
                if datetime.now() - calibration_date < timedelta(days=7):
                    print(f"{Fore.GREEN}✅ Loading saved voice calibration from {calibration_date.strftime('%Y-%m-%d')}{Style.RESET_ALL}")
                    
                    # Load saved wake word if available
                    if 'wake_word' in data:
                        self.wake_word = data['wake_word']
                        print(f"{Fore.CYAN}✅ Loaded saved wake word: '{self.wake_word}'{Style.RESET_ALL}")
                    
                    return data
                else:
                    print(f"{Fore.YELLOW}⚠️ Calibration data is old ({calibration_date.strftime('%Y-%m-%d')}), will recalibrate{Style.RESET_ALL}")
            
            return None
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Failed to load calibration data: {e}{Style.RESET_ALL}")
            return None
    
    def save_calibration_data(self, energy_threshold, pause_threshold, success_rate=1.0):
        """Save calibration data for future use"""
        try:
            data = {
                'date': datetime.now().isoformat(),
                'energy_threshold': energy_threshold,
                'pause_threshold': pause_threshold,
                'success_rate': success_rate,
                'microphone_count': len(sr.Microphone.list_microphone_names()),
                'wake_word': self.wake_word,
                'version': '1.0'
            }
            
            with open(self.calibration_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"{Fore.GREEN}✅ Voice calibration saved for future sessions{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Failed to save calibration data: {e}{Style.RESET_ALL}")
            return False
    
    def smart_calibration(self):
        """Smart calibration that uses saved data when available"""
        print(f"{Fore.YELLOW}📊 Smart calibration starting...{Style.RESET_ALL}")
        
        # Send calibration start notification
        self.send_notification(
            "🔧 Voice Calibration Starting", 
            "Checking voice settings and ambient noise...",
            "preferences-desktop-sound",
            "low",
            4000
        )
        
        # Try to load existing calibration
        saved_data = self.load_calibration_data()
        
        if saved_data:
            # Use saved calibration
            self.recognizer.energy_threshold = saved_data['energy_threshold']
            self.recognizer.pause_threshold = saved_data['pause_threshold']
            
            print(f"{Fore.GREEN}🎯 Using saved calibration:{Style.RESET_ALL}")
            print(f"  Energy threshold: {self.recognizer.energy_threshold:.0f}")
            print(f"  Pause threshold: {self.recognizer.pause_threshold}s")
            
            # Send quick calibration notification
            self.send_notification(
                "⚡ Quick Calibration", 
                f"Using saved settings from previous session\nEnergy: {self.recognizer.energy_threshold:.0f} | Pause: {self.recognizer.pause_threshold}s",
                "dialog-information",
                "low",
                3000
            )
            
            # Still do ambient noise adjustment
            print(f"{Fore.YELLOW}🔇 Quick ambient noise check (2 seconds)...{Style.RESET_ALL}")
            try:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=2)
                print(f"{Fore.GREEN}✅ Ambient noise adjusted{Style.RESET_ALL}")
                
                # Send calibration complete notification
                self.send_notification(
                    "✅ Voice Calibration Complete", 
                    "Background mode ready for voice commands!\nAmbient noise adjusted.",
                    "audio-input-microphone",
                    "normal",
                    4000
                )
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Ambient adjustment failed: {e}{Style.RESET_ALL}")
                self.send_notification(
                    "⚠️ Calibration Warning", 
                    "Ambient noise adjustment failed but proceeding with saved settings",
                    "dialog-warning",
                    "normal",
                    4000
                )
        else:
            # Perform full calibration for first time or when data is stale
            self.send_notification(
                "🎤 First-Time Voice Setup", 
                "No saved settings found. Starting full calibration...",
                "preferences-desktop-sound",
                "normal",
                5000
            )
            self.enhanced_calibration()
    
    def enhanced_calibration(self):
        """Enhanced calibration optimized for longer phrases"""
        print(f"{Fore.YELLOW}📊 Enhanced calibration for long phrases...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🔇 Please be quiet for 4 seconds{Style.RESET_ALL}")
        
        # Send ambient noise calibration notification
        self.send_notification(
            "🔇 Ambient Noise Calibration", 
            "Please be quiet for 4 seconds...\nMeasuring background noise levels.",
            "audio-input-microphone",
            "normal",
            6000
        )
        
        try:
            with self.microphone as source:
                # Extended calibration for better ambient noise detection
                self.recognizer.adjust_for_ambient_noise(source, duration=4)
                
            initial_threshold = self.recognizer.energy_threshold
            print(f"{Fore.CYAN}🎚️ Initial threshold: {initial_threshold:.0f}{Style.RESET_ALL}")
            
            # Test with a longer phrase
            print(f"{Fore.YELLOW}🧪 Testing with longer phrase...{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Say: 'play Hotel California by Eagles' now{Style.RESET_ALL}")
            
            # Send voice test notification
            self.send_notification(
                "🎤 Voice Test Required", 
                "Please say: 'play Hotel California by Eagles'\nThis helps optimize recognition for your voice.",
                "audio-input-microphone",
                "critical",
                8000
            )
            
            with self.microphone as source:
                try:
                    # Test with longer timeout and phrase limit
                    audio = self.recognizer.listen(source, timeout=8, phrase_time_limit=15)
                    test_result = self.recognizer.recognize_google(audio, language='en-US')
                    print(f"{Fore.GREEN}✅ Long phrase test successful! Heard: '{test_result}'{Style.RESET_ALL}")
                    
                    # Optimize threshold based on test
                    if len(test_result.split()) >= 3:  # If we got multiple words
                        print(f"{Fore.GREEN}🎯 Multi-word recognition confirmed!{Style.RESET_ALL}")
                    else:
                        # Adjust for better sensitivity
                        self.recognizer.energy_threshold = max(150, self.recognizer.energy_threshold * 0.8)
                        print(f"{Fore.CYAN}🔧 Adjusted threshold for better sensitivity: {self.recognizer.energy_threshold:.0f}{Style.RESET_ALL}")
                        
                except Exception as e:
                    print(f"{Fore.YELLOW}⚠️ Long phrase test failed: {e}{Style.RESET_ALL}")
                    # Set conservative settings for difficult environments
                    self.recognizer.energy_threshold = 250
                    self.recognizer.pause_threshold = 3.5  # Even longer pause threshold
                    print(f"{Fore.CYAN}🔧 Using conservative settings for difficult environment{Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}🎤 Final settings:{Style.RESET_ALL}")
            print(f"  Energy threshold: {self.recognizer.energy_threshold:.0f}")
            print(f"  Pause threshold: {self.recognizer.pause_threshold}s")
            
            # Save calibration for future use
            self.save_calibration_data(
                self.recognizer.energy_threshold,
                self.recognizer.pause_threshold,
                success_rate=1.0 if len(test_result.split()) >= 3 else 0.5
            )
            
            # Send calibration success notification
            self.send_notification(
                "✅ Voice Calibration Complete", 
                f"Voice recognition optimized!\nEnergy: {self.recognizer.energy_threshold:.0f} | Pause: {self.recognizer.pause_threshold}s\nBackground mode ready!",
                "audio-input-microphone",
                "normal",
                6000
            )
            
        except Exception as e:
            print(f"{Fore.RED}❌ Calibration failed: {e}{Style.RESET_ALL}")
            # Ultra-conservative fallback
            self.recognizer.energy_threshold = 300
            self.recognizer.pause_threshold = 4.0
            print(f"{Fore.YELLOW}🔄 Using ultra-conservative fallback settings{Style.RESET_ALL}")
            
            # Save fallback calibration
            self.save_calibration_data(
                self.recognizer.energy_threshold,
                self.recognizer.pause_threshold,
                success_rate=0.3
            )
    
    def speak(self, text, wait=False):
        """Text to speech with optional synchronous mode"""
        print(f"{Fore.MAGENTA}🤖 Assistant: {text}{Style.RESET_ALL}")
        
        def speak_thread():
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as e:
                print(f"{Fore.RED}TTS Error: {e}{Style.RESET_ALL}")
        
        if wait:
            # Synchronous - wait for speech to complete
            speak_thread()
            return None
        else:
            # Asynchronous - return thread
            thread = threading.Thread(target=speak_thread, daemon=True)
            thread.start()
            return thread
    
    def setup_notifications(self):
        """Setup desktop notification system"""
        try:
            result = subprocess.run(['which', 'notify-send'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.notifications_enabled = True
                print(f"{Fore.GREEN}✅ Desktop notifications enabled{Style.RESET_ALL}")
            else:
                self.notifications_enabled = False
                print(f"{Fore.YELLOW}⚠️ notify-send not found, notifications disabled{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}   Install with: sudo pacman -S libnotify{Style.RESET_ALL}")
        except Exception as e:
            self.notifications_enabled = False
            print(f"{Fore.YELLOW}⚠️ Notification setup failed: {e}{Style.RESET_ALL}")
    
    def send_notification(self, title, message, icon="audio-headphones", urgency="normal", timeout=5000):
        """Send desktop notification using notify-send"""
        if not self.notifications_enabled:
            return
        
        try:
            cmd = [
                'notify-send',
                '--app-name=Enhanced Spotify Assistant',
                f'--icon={icon}',
                f'--urgency={urgency}',
                f'--expire-time={timeout}',
                '--category=music',
                title,
                message
            ]
            
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Notification failed: {e}{Style.RESET_ALL}")
    
    def listen_for_command(self, timeout=3):
        """ENHANCED listening specifically for complete song names"""
        try:
            print(f"\n{Fore.CYAN}🎤 ENHANCED LISTENING MODE{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}📢 Say your COMPLETE command in ONE sentence{Style.RESET_ALL}")
            print(f"{Fore.GREEN}💡 Example: 'play Hotel California by Eagles'{Style.RESET_ALL}")
            print(f"{Fore.CYAN}⏱️ You have {timeout} seconds, I'll wait {self.recognizer.pause_threshold} seconds for pauses{Style.RESET_ALL}")
            
            # Send enhanced listening notification
            self.send_notification(
                "🎤 Enhanced Listening Mode", 
                f"Waiting for your COMPLETE command...\nPause detection: {self.recognizer.pause_threshold}s",
                "audio-input-microphone",
                "low",
                timeout * 1000
            )
            
            print(f"{Fore.GREEN}🟢 LISTENING NOW - Speak your full command!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💬 I'll wait for natural pauses in your speech...{Style.RESET_ALL}")
            
            with self.microphone as source:
                # Quick ambient adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                
                # Listen with MAXIMUM settings for complete phrases
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=7  # Allow up to 7 seconds for complete command
                )
            
            print(f"{Fore.BLUE}🔄 Processing your complete command...{Style.RESET_ALL}")
            
            # Try multiple recognition approaches
            command = None
            
            # Method 1: Standard Google (US)
            try:
                command = self.recognizer.recognize_google(audio, language='en-US').lower()
                print(f"{Fore.GREEN}✅ Google (US) recognized: '{command}'{Style.RESET_ALL}")
                self.send_notification(
                    "✅ Full Command Recognized", 
                    f"Captured: '{command}'",
                    "dialog-information",
                    "low",
                    4000
                )
                self.success_count += 1
                return command
            except sr.UnknownValueError:
                print(f"{Fore.YELLOW}⚠️ Google (US) couldn't understand{Style.RESET_ALL}")
            except sr.RequestError as e:
                print(f"{Fore.YELLOW}⚠️ Google (US) service error: {e}{Style.RESET_ALL}")
            
            # Method 2: Google with different language
            try:
                command = self.recognizer.recognize_google(audio, language='en-GB').lower()
                print(f"{Fore.GREEN}✅ Google (UK) recognized: '{command}'{Style.RESET_ALL}")
                self.send_notification(
                    "✅ Full Command Recognized", 
                    f"Captured: '{command}'",
                    "dialog-information",
                    "low",
                    4000
                )
                self.success_count += 1
                return command
            except:
                pass
            
            # Method 3: Try with show_all for partial results
            try:
                results = self.recognizer.recognize_google(audio, language='en-US', show_all=True)
                if results and 'alternative' in results:
                    alternatives = results['alternative']
                    if alternatives:
                        command = alternatives[0]['transcript'].lower()
                        confidence = alternatives[0].get('confidence', 0)
                        print(f"{Fore.GREEN}✅ Google (alternatives) recognized: '{command}' (confidence: {confidence:.2f}){Style.RESET_ALL}")
                        if confidence > 0.3:  # Accept lower confidence for longer phrases
                            self.send_notification(
                                "✅ Command Recognized (Alt)", 
                                f"Captured: '{command}'\nConfidence: {confidence:.2f}",
                                "dialog-information",
                                "low",
                                4000
                            )
                            self.success_count += 1
                            return command
            except:
                pass
            
            print(f"{Fore.YELLOW}❌ Could not understand the complete command{Style.RESET_ALL}")
            print(f"{Fore.CYAN}💡 Will switch to text mode for this command{Style.RESET_ALL}")
            
            # Send voice failure notification
            self.send_notification(
                "❌ Voice Recognition Failed", 
                "Could not understand command.\nSwitching to text mode temporarily.",
                "dialog-warning",
                "normal",
                4000
            )
            
            # Speak the failure message
            self.speak("Sorry, I couldn't understand that. Going back to sleep.")
            
            self.adjust_sensitivity()
            return None
                
        except sr.WaitTimeoutError:
            print(f"{Fore.YELLOW}⏰ No speech detected within {timeout} seconds{Style.RESET_ALL}")
            print(f"{Fore.CYAN}💡 Switching to text mode for this command{Style.RESET_ALL}")
            
            # Send timeout notification
            self.send_notification(
                "⏰ Voice Timeout", 
                "No speech detected within timeout.\nSwitching to text mode.",
                "dialog-warning",
                "normal",
                4000
            )
            
            # Speak the timeout message
            self.speak("No speech detected. Switching to text mode.")
            
            return None
        except Exception as e:
            print(f"{Fore.RED}❌ Enhanced listening error: {e}{Style.RESET_ALL}")
            return None
        finally:
            self.attempt_count += 1
    
    def listen_for_wake_word(self):
        """Listen specifically for the wake word"""
        try:
            print(f"{Fore.CYAN}👂 Listening for wake word: '{self.wake_word}'...{Style.RESET_ALL}")
            
            with self.microphone as source:
                # Quick ambient adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                
                # Listen for wake word with longer timeout
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.wake_word_timeout,
                    phrase_time_limit=5  # Wake word should be short
                )
            
            # Try to recognize the wake word
            try:
                recognized_text = self.recognizer.recognize_google(audio, language='en-US').lower()
                print(f"{Fore.CYAN}👂 Heard: '{recognized_text}'{Style.RESET_ALL}")
                
                # Check if wake word is in the recognized text
                if self.wake_word.lower() in recognized_text:
                    print(f"{Fore.GREEN}✅ Wake word '{self.wake_word}' detected!{Style.RESET_ALL}")
                    
                    # Speak "yes sir" and wait for it to complete before returning
                    print(f"{Fore.CYAN}🤖 Acknowledging wake word...{Style.RESET_ALL}")
                    self.speak("yes sir", wait=True)  # Synchronous - wait for completion
                    print(f"{Fore.GREEN}✅ Ready for command after acknowledgment{Style.RESET_ALL}")
                    
                    return True
                else:
                    print(f"{Fore.YELLOW}🔇 No wake word detected in: '{recognized_text}'{Style.RESET_ALL}")
                    return False
                    
            except sr.UnknownValueError:
                print(f"{Fore.YELLOW}🔇 Could not understand audio (waiting for wake word){Style.RESET_ALL}")
                return False
            except sr.RequestError as e:
                print(f"{Fore.YELLOW}⚠️ Recognition service error: {e}{Style.RESET_ALL}")
                return False
                
        except sr.WaitTimeoutError:
            print(f"{Fore.BLUE}😴 No wake word heard in {self.wake_word_timeout} seconds, continuing to sleep...{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}❌ Wake word listening error: {e}{Style.RESET_ALL}")
            return False
    
    def adjust_sensitivity(self):
        """Smart sensitivity adjustment for better long phrase recognition"""
        if self.attempt_count > 2:
            success_rate = self.success_count / self.attempt_count
            
            if success_rate < 0.3:  # Less than 30% success
                # Make it more sensitive
                old_threshold = self.recognizer.energy_threshold
                old_pause = self.recognizer.pause_threshold
                
                self.recognizer.energy_threshold = max(100, self.recognizer.energy_threshold * 0.7)
                self.recognizer.pause_threshold = min(5.0, self.recognizer.pause_threshold * 1.2)
                
                print(f"{Fore.YELLOW}🔧 Enhanced sensitivity adjustment:{Style.RESET_ALL}")
                print(f"   Energy: {old_threshold:.0f} → {self.recognizer.energy_threshold:.0f}")
                print(f"   Pause: {old_pause:.1f}s → {self.recognizer.pause_threshold:.1f}s")
                
                self.send_notification(
                    "🔧 Sensitivity Adjusted", 
                    "Made recognition more sensitive for better phrase capture",
                    "dialog-information",
                    "low",
                    3000
                )
    
    def process_command(self, command):
        """Enhanced command processing with better song name extraction"""
        command = command.lower().strip()
        print(f"{Fore.MAGENTA}🔄 Processing complete command: '{command}'{Style.RESET_ALL}")
        
        try:
            # Enhanced song name extraction
            if 'play' in command and len(command.split()) > 1:
                # Extract everything after 'play'
                song_name = command.split('play', 1)[1].strip()
                
                # Clean up common words but preserve artist info
                song_name = song_name.replace('the song', '').strip()
                song_name = song_name.replace('song called', '').strip()
                song_name = song_name.replace('track', '').strip()
                
                if song_name:
                    print(f"{Fore.CYAN}🎵 Extracted song: '{song_name}'{Style.RESET_ALL}")
                    self.play_song(song_name)
                    return
            
            # Other commands
            if any(word in command for word in ['play', 'start', 'resume', 'go']):
                self.resume_playback()
            elif any(word in command for word in ['pause', 'stop', 'halt']):
                self.pause_playback()
            elif any(word in command for word in ['next', 'skip', 'forward']):
                self.next_track()
            elif any(word in command for word in ['previous', 'back', 'last']):
                self.previous_track()
            elif 'volume up' in command or 'louder' in command or 'turn up' in command:
                self.adjust_volume(15)
            elif 'volume down' in command or 'quieter' in command or 'turn down' in command:
                self.adjust_volume(-15)
            elif any(word in command for word in ['what', 'playing', 'current', 'now']):
                self.get_current_track()
            elif any(word in command for word in ['quit', 'exit', 'bye', 'goodbye']):
                self.speak("Goodbye!")
                self.send_notification(
                    "👋 Enhanced Assistant Stopping", 
                    "Enhanced Spotify Voice Assistant is shutting down",
                    "application-exit",
                    "low",
                    3000
                )
                self.is_running = False
            else:
                self.speak(f"I heard '{command}' but didn't understand the command. Try 'play [full song name]' or other basic commands.")
                
        except Exception as e:
            print(f"{Fore.RED}Command processing error: {e}{Style.RESET_ALL}")
            self.speak("Sorry, I had trouble processing that command.")
    
    # Spotify control methods (same as before but with enhanced notifications)
    def play_song(self, song_name):
        try:
            print(f"{Fore.CYAN}🔍 Searching for: '{song_name}'{Style.RESET_ALL}")
            results = self.spotify.search(q=song_name, type='track', limit=3)  # Get more results
            
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                self.spotify.start_playback(uris=[track['uri']])
                message = f"Playing {track['name']} by {track['artists'][0]['name']}"
                self.speak(message)
                
                # Enhanced now playing notification
                self.send_notification(
                    "🎵 Now Playing (Enhanced)", 
                    f"🎤 Search: '{song_name}'\n🎵 Found: {track['name']}\n👨‍🎤 Artist: {track['artists'][0]['name']}",
                    "audio-volume-high",
                    "normal",
                    6000
                )
                
                # Show alternatives if available
                if len(results['tracks']['items']) > 1:
                    alternatives = [f"{t['name']} by {t['artists'][0]['name']}" for t in results['tracks']['items'][1:3]]
                    print(f"{Fore.YELLOW}🔄 Other matches found: {', '.join(alternatives)}{Style.RESET_ALL}")
            else:
                self.speak(f"Couldn't find {song_name}")
                self.send_notification(
                    "❌ Song Not Found", 
                    f"No results for: '{song_name}'\nTry being more specific or check spelling",
                    "dialog-warning",
                    "normal",
                    5000
                )
        except Exception as e:
            self.speak("Sorry, couldn't play that song.")
            self.send_notification(
                "❌ Playback Error", 
                f"Failed to play: {song_name}",
                "dialog-error"
            )
    
    # (Include all other Spotify methods from previous version)
    def resume_playback(self):
        try:
            self.spotify.start_playback()
            self.speak("Resuming playback")
            self.send_notification("▶️ Playback Resumed", "Music playback resumed", "media-playback-start", "low", 2000)
        except Exception:
            self.speak("No active device found. Start Spotify first.")
            self.send_notification("❌ No Active Device", "Please start Spotify first", "dialog-warning")
    
    def pause_playback(self):
        try:
            self.spotify.pause_playback()
            self.speak("Pausing")
            self.send_notification("⏸️ Playback Paused", "Music paused", "media-playback-pause", "low", 2000)
        except Exception:
            self.speak("Couldn't pause playback.")
            self.send_notification("❌ Pause Failed", "Couldn't pause", "dialog-error")
    
    def next_track(self):
        try:
            self.spotify.next_track()
            self.speak("Next track")
            self.send_notification("⏭️ Next Track", "Skipped to next", "media-skip-forward", "low", 2000)
        except Exception:
            self.speak("Couldn't skip track.")
            self.send_notification("❌ Skip Failed", "Couldn't skip", "dialog-error")
    
    def previous_track(self):
        try:
            self.spotify.previous_track()
            self.speak("Previous track")
            self.send_notification("⏮️ Previous Track", "Went to previous", "media-skip-backward", "low", 2000)
        except Exception:
            self.speak("Couldn't go back.")
            self.send_notification("❌ Previous Failed", "Couldn't go back", "dialog-error")
    
    def adjust_volume(self, change):
        try:
            current = self.spotify.current_playback()
            if current and current['device']:
                volume = max(0, min(100, current['device']['volume_percent'] + change))
                self.spotify.volume(volume)
                self.speak(f"Volume {volume} percent")
                icon = "audio-volume-high" if volume > 66 else "audio-volume-medium" if volume > 33 else "audio-volume-low"
                self.send_notification(f"🔊 Volume: {volume}%", f"Adjusted to {volume}%", icon, "low", 2000)
        except Exception:
            self.speak("Couldn't adjust volume.")
            self.send_notification("❌ Volume Error", "Couldn't adjust", "dialog-error")
    
    def get_current_track(self):
        try:
            current = self.spotify.current_playback()
            if current and current['is_playing']:
                track = current['item']
                message = f"Playing {track['name']} by {track['artists'][0]['name']}"
                self.speak(message)
                self.send_notification("🎵 Current Track", f"{track['name']}\nby {track['artists'][0]['name']}", "audio-volume-high", "normal", 4000)
            else:
                self.speak("Nothing is playing")
                self.send_notification("⏸️ No Music Playing", "No track playing", "audio-volume-muted")
        except Exception:
            self.speak("Couldn't get track info.")
            self.send_notification("❌ Info Error", "Couldn't get info", "dialog-error")
    
    def offer_text_fallback(self):
        """Offer text input when voice recognition fails"""
        print(f"\n{Fore.YELLOW}🔄 Voice recognition failed. Switching to text mode temporarily.{Style.RESET_ALL}")
        
        # Send notification about fallback
        self.send_notification(
            "⌨️ Text Mode Fallback", 
            "Voice recognition failed.\nTemporarily switching to text input.",
            "input-keyboard",
            "normal",
            5000
        )
        
        # Speak the fallback message
        self.speak("Voice recognition failed. Please type your command.")
        
        print(f"{Fore.CYAN}📝 Type your command (or 'voice' to retry voice mode, 'quit' to exit):{Style.RESET_ALL}")
        
        try:
            user_input = input(f"{Fore.BLUE}text> {Style.RESET_ALL}").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                self.speak("Goodbye!")
                self.send_notification("👋 Enhanced Assistant Stopping", "Shutting down", "application-exit", "low", 3000)
                self.is_running = False
            elif user_input.lower() == 'voice':
                print(f"{Fore.GREEN}🎤 Returning to voice mode...{Style.RESET_ALL}")
                self.send_notification(
                    "🎤 Voice Mode Restored", 
                    "Returning to voice-first mode",
                    "audio-input-microphone",
                    "low",
                    3000
                )
                return  # Return to voice loop
            elif user_input.lower() == 'help':
                self.show_enhanced_tips()
                return self.offer_text_fallback()  # Ask again after showing tips
            elif user_input.lower() == 'wake':
                self.change_wake_word()
                return self.offer_text_fallback()  # Ask again after changing wake word
            elif user_input.lower() == 'recalibrate':
                print(f"{Fore.YELLOW}🔄 Forcing voice recalibration...{Style.RESET_ALL}")
                self.enhanced_calibration()
                return  # Return to voice loop after recalibration
            elif user_input:
                print(f"{Fore.BLUE}📝 Processing text command: {user_input}{Style.RESET_ALL}")
                self.process_command(user_input)
                
                # Ask if user wants to continue with text or return to voice
                print(f"\n{Fore.CYAN}Continue with text mode? (y/n, default: return to voice): {Style.RESET_ALL}", end="")
                continue_text = input().strip().lower()
                
                if continue_text == 'y' or continue_text == 'yes':
                    print(f"{Fore.BLUE}📝 Staying in text mode{Style.RESET_ALL}")
                    return self.text_mode_loop()  # Switch to persistent text mode
                else:
                    print(f"{Fore.GREEN}🎤 Returning to voice mode...{Style.RESET_ALL}")
                    self.send_notification(
                        "🎤 Voice Mode Restored", 
                        "Returning to voice-first mode",
                        "audio-input-microphone",
                        "low",
                        3000
                    )
            else:
                print(f"{Fore.YELLOW}💡 Empty input, returning to voice mode{Style.RESET_ALL}")
                
        except KeyboardInterrupt:
            print(f"\n{Fore.GREEN}🎤 Returning to voice mode...{Style.RESET_ALL}")
    
    def text_mode_loop(self):
        """Persistent text mode with option to return to voice"""
        print(f"\n{Fore.BLUE}📝 TEXT MODE: Type commands or 'voice' to return to voice mode{Style.RESET_ALL}")
        
        self.send_notification(
            "⌨️ Text Mode Active", 
            "Type commands manually.\nType 'voice' to return to voice mode.",
            "input-keyboard",
            "normal",
            5000
        )
        
        try:
            while self.is_running:
                print(f"\n{Fore.YELLOW}{'='*50}{Style.RESET_ALL}")
                print(f"{Fore.BLUE}📝 Text mode - Type your command:{Style.RESET_ALL}")
                
                user_input = input(f"{Fore.BLUE}text> {Style.RESET_ALL}").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.speak("Goodbye!")
                    self.send_notification("👋 Enhanced Assistant Stopping", "Shutting down", "application-exit", "low", 3000)
                    self.is_running = False
                    break
                elif user_input.lower() == 'voice':
                    print(f"{Fore.GREEN}🎤 Returning to voice-first mode...{Style.RESET_ALL}")
                    self.send_notification(
                        "🎤 Voice Mode Restored", 
                        "Returning to voice-first mode",
                        "audio-input-microphone",
                        "normal",
                        4000
                    )
                    break  # Exit text loop, return to voice mode
                elif user_input.lower() == 'help':
                    self.show_enhanced_tips()
                elif user_input.lower() == 'wake':
                    self.change_wake_word()
                elif user_input.lower() == 'recalibrate':
                    print(f"{Fore.YELLOW}🔄 Forcing voice recalibration...{Style.RESET_ALL}")
                    self.enhanced_calibration()
                    print(f"{Fore.GREEN}🎤 Returning to voice mode after calibration...{Style.RESET_ALL}")
                    break  # Return to voice mode after recalibration
                elif user_input:
                    print(f"{Fore.BLUE}📝 Processing text command: {user_input}{Style.RESET_ALL}")
                    self.process_command(user_input)
                else:
                    print(f"{Fore.YELLOW}💡 Empty input. Type 'help' for commands or 'voice' to switch modes{Style.RESET_ALL}")
                    
        except KeyboardInterrupt:
            print(f"\n{Fore.GREEN}🎤 Returning to voice mode...{Style.RESET_ALL}")
    
    def change_wake_word(self):
        """Allow user to change the wake word"""
        print(f"\n{Fore.CYAN}Current wake word: '{self.wake_word}'{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Enter new wake word (or press Enter to keep current):{Style.RESET_ALL}")
        
        new_wake_word = input(f"{Fore.BLUE}wake word> {Style.RESET_ALL}").strip()
        
        if new_wake_word:
            self.wake_word = new_wake_word.lower()
            print(f"{Fore.GREEN}✅ Wake word changed to: '{self.wake_word}'{Style.RESET_ALL}")
            
            self.send_notification(
                "🔄 Wake Word Changed", 
                f"New wake word: '{self.wake_word}'\nSay this to wake the assistant.",
                "dialog-information",
                "normal",
                5000
            )
            
            # Save to calibration file
            try:
                if os.path.exists(self.calibration_file):
                    with open(self.calibration_file, 'r') as f:
                        data = json.load(f)
                    data['wake_word'] = self.wake_word
                    with open(self.calibration_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"{Fore.GREEN}✅ Wake word saved to calibration file{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️ Could not save wake word: {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}Keeping current wake word: '{self.wake_word}'{Style.RESET_ALL}")
    
    def show_enhanced_tips(self):
        """Show tips for wake word mode and voice commands"""
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
        
        print(f"\n{Fore.CYAN}💡 Enhanced Voice Recognition Tips:{Style.RESET_ALL}")
        for tip in tips:
            print(f"  {tip}")
    
    def run(self):
        """Enhanced main loop - Voice-first with text fallback"""
        # Removed onboarding voice message to prevent timing conflicts with voice listening
        # Notifications provide sufficient user feedback
        
        print(f"\n{Fore.CYAN}📋 Enhanced Voice Commands:{Style.RESET_ALL}")
        print(f"  • 'play [complete song name]' - Play specific song")
        print(f"  • 'play [song] by [artist]' - Best format")
        print(f"  • Standard controls: play, pause, next, previous")
        print(f"  • Volume: 'volume up' or 'volume down'")
        print(f"  • Info: 'what's playing'")
        print(f"  • Special: 'recalibrate' to redo voice setup")
        print(f"  • Wake word: '{self.wake_word}' (type 'wake' to change)")
        print(f"  • Exit: 'quit' or 'exit'")
        
        # Send ready notification for wake word mode
        self.send_notification(
            "😴 Wake Word Mode Active", 
            f"Say '{self.wake_word}' to wake me up!\nI'll sleep between commands to save resources.",
            "audio-input-microphone",
            "normal",
            8000
        )
        
        print(f"\n{Fore.GREEN}😴 WAKE WORD MODE: Say '{self.wake_word}' to start!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}💡 I'll sleep between commands to let you enjoy your music{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⌨️ Press Ctrl+C anytime to enter text mode{Style.RESET_ALL}")
        
        try:
            while self.is_running:
                print(f"\n{Fore.YELLOW}{'='*70}{Style.RESET_ALL}")
                
                # Enhanced success rate display
                if self.attempt_count > 0:
                    success_rate = (self.success_count / self.attempt_count) * 100
                    print(f"{Fore.CYAN}📊 Enhanced Recognition Rate: {success_rate:.1f}% ({self.success_count}/{self.attempt_count}){Style.RESET_ALL}")
                
                if not self.is_awake:
                    # Sleep mode - listen for wake word
                    print(f"{Fore.BLUE}😴 Sleeping... Say '{self.wake_word}' to wake me up{Style.RESET_ALL}")
                    if self.listen_for_wake_word():
                        self.is_awake = True
                        print(f"{Fore.GREEN}👂 Wake word detected! I'm listening...{Style.RESET_ALL}")
                        
                        # Send wake notification
                        self.send_notification(
                            "👂 Assistant Awakened", 
                            "Wake word detected! Said 'yes sir' - ready for command.",
                            "audio-input-microphone",
                            "normal",
                            4000
                        )
                        
                        # Now listen for the actual command ("yes sir" has completed)
                        print(f"{Fore.YELLOW}🎤 Now listening for your command...{Style.RESET_ALL}")
                        command = self.listen_for_command()
                        
                        if command:
                            # Voice command successful
                            self.process_command(command)
                            # Go back to sleep after processing command
                            self.is_awake = False
                            print(f"{Fore.BLUE}😴 Going back to sleep... Say '{self.wake_word}' when you need me{Style.RESET_ALL}")
                            
                            self.send_notification(
                                "😴 Assistant Sleeping", 
                                f"Command executed! Say '{self.wake_word}' to wake me again.",
                                "audio-input-microphone",
                                "low",
                                4000
                            )
                        else:
                            # Voice command failed, go back to sleep
                            print(f"{Fore.YELLOW}😴 Command failed, going back to sleep...{Style.RESET_ALL}")
                            self.is_awake = False
                    else:
                        # No wake word detected, continue sleeping
                        continue
                else:
                    # Should not reach here in new wake word system
                    self.is_awake = False
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⌨️ Switching to text mode...{Style.RESET_ALL}")
            self.text_mode_loop()
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        finally:
            if self.attempt_count > 0:
                success_rate = (self.success_count / self.attempt_count) * 100
                print(f"{Fore.CYAN}📊 Final Enhanced Recognition Rate: {success_rate:.1f}%{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Enhanced Assistant Goodbye!{Style.RESET_ALL}")

def main():
    try:
        assistant = EnhancedVoiceAssistant()
        assistant.run()
    except Exception as e:
        print(f"{Fore.RED}Failed to start enhanced assistant: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()

