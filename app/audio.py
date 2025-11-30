import speech_recognition as sr
import pyttsx3
import logging
import os
from typing import Optional

# Import error handling types
try:
    from .error_handling import ErrorHandler
except ImportError:
    ErrorHandler = None

class AudioManager:
    def __init__(self, calibration_file, notifier=None, wake_word='jarvis'):
        self.recognizer = sr.Recognizer()
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 160)
        self.tts.setProperty('volume', 0.9)
        self.microphone = None
        self.calibration_file = calibration_file
        self.notifier = notifier
        self.wake_word = wake_word
        self.is_awake = False
        self.error_handler = None  # Will be assigned by VoiceAssistant
        self.success_count = 0
        self.attempt_count = 0
        # Thread safety for microphone access
        import threading
        self._microphone_lock = threading.Lock()
        self._shared_microphone = None
        logging.info("AudioManager initialized.")

    def cleanup(self):
        """Clean up audio resources."""
        try:
            with self._microphone_lock:
                self._shared_microphone = None
            if hasattr(self.tts, 'stop'):
                self.tts.stop()
            logging.info("AudioManager resources cleaned up")
        except Exception as e:
            logging.warning(f"Error during AudioManager cleanup: {e}")


    def setup_enhanced_audio(self):
        try:
            # Find best microphone
            self.select_best_microphone()
            # ENHANCED settings specifically for longer phrases
            self.recognizer.energy_threshold = 200
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.dynamic_energy_adjustment_damping = 0.1
            self.recognizer.dynamic_energy_ratio = 1.2
            self.recognizer.pause_threshold = 1.0
            self.recognizer.phrase_threshold = 0.2
            self.recognizer.non_speaking_duration = 0.5
            self.recognizer.operation_timeout = None
            self.smart_calibration()
            logging.info("Audio setup for long phrases complete.")
        except Exception as e:
            logging.exception(f"Audio setup failed in setup_enhanced_audio (calibration_file={self.calibration_file}, wake_word={self.wake_word}):")
            if self.notifier:
                self.notifier.send_notification(
                    "❌ Audio Error",
                    f"Failed to setup audio: {str(e)[:50]}...",
                    "dialog-error"
                )
            raise

    def select_best_microphone(self):
        """Get shared microphone instance to prevent device locking."""
        with self._microphone_lock:
            if self._shared_microphone is None:
                mic_list = sr.Microphone.list_microphone_names()
                sample_rate = 44100  # Match typical output device sample rate
                try:
                    self._shared_microphone = sr.Microphone(sample_rate=sample_rate)
                except Exception as e:
                    logging.warning(f"Failed to create microphone with sample rate {sample_rate}: {e}")
                    self._shared_microphone = sr.Microphone()  # Use default
            return self._shared_microphone

    def _validate_calibration_path(self):
        """Validate and secure the calibration file path."""
        try:
            # Normalize the path and ensure it's within expected directory
            normalized_path = os.path.normpath(os.path.abspath(self.calibration_file))
            
            # Ensure the file is within the project's calibration directory
            project_root = os.path.dirname(os.path.dirname(__file__))
            calibration_dir = os.path.join(project_root, 'calibration')
            
            if not normalized_path.startswith(os.path.normpath(calibration_dir)):
                raise ValueError("Calibration file path outside allowed directory")
            
            # Create directory with secure permissions if it doesn't exist
            os.makedirs(os.path.dirname(normalized_path), mode=0o700, exist_ok=True)
            
            return normalized_path
        except Exception as e:
            logging.error(f"Calibration path validation failed: {e}")
            raise

    def load_calibration_data(self):
        import json
        from datetime import datetime, timedelta
        try:
            validated_path = self._validate_calibration_path()
            
            if os.path.exists(validated_path):
                # Check file permissions for security
                file_stat = os.stat(validated_path)
                if file_stat.st_mode & 0o077:  # Check if others have access
                    logging.warning("Calibration file has unsafe permissions, fixing...")
                    os.chmod(validated_path, 0o600)
                
                with open(validated_path, 'r') as f:
                    data = json.load(f)
                
                # Validate data structure
                required_fields = ['date', 'energy_threshold', 'pause_threshold']
                if not all(field in data for field in required_fields):
                    logging.warning("Calibration file missing required fields")
                    return None
                
                calibration_date = datetime.fromisoformat(data.get('date', '2000-01-01'))
                if datetime.now() - calibration_date < timedelta(days=7):
                    if 'wake_word' in data and isinstance(data['wake_word'], str):
                        # Sanitize wake word input
                        wake_word = data['wake_word'].strip()[:50]  # Limit length
                        if wake_word.isalnum():
                            self.wake_word = wake_word
                    return data
            return None
        except Exception as e:
            logging.warning(f"Failed to load calibration data: {e}", exc_info=True)
            return None

    def save_calibration_data(self, energy_threshold, pause_threshold, success_rate=1.0):
        import json
        import tempfile
        from datetime import datetime
        try:
            validated_path = self._validate_calibration_path()
            
            # Validate input parameters
            if not (isinstance(energy_threshold, (int, float)) and energy_threshold > 0):
                raise ValueError("Invalid energy_threshold value")
            if not (isinstance(pause_threshold, (int, float)) and pause_threshold > 0):
                raise ValueError("Invalid pause_threshold value")
            if not (isinstance(success_rate, (int, float)) and 0 <= success_rate <= 1):
                raise ValueError("Invalid success_rate value")
            
            data = {
                'date': datetime.now().isoformat(),
                'energy_threshold': float(energy_threshold),
                'pause_threshold': float(pause_threshold),
                'success_rate': float(success_rate),
                'microphone_count': len(sr.Microphone.list_microphone_names()),
                'wake_word': str(self.wake_word)[:50],  # Sanitize and limit
                'version': '1.0'
            }
            
            # Atomic write using temporary file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                dir=os.path.dirname(validated_path),
                delete=False,
                prefix='.tmp_calibration_',
                suffix='.json'
            ) as tmp_file:
                json.dump(data, tmp_file, indent=2)
                tmp_file_path = tmp_file.name
            
            # Set secure permissions before moving
            os.chmod(tmp_file_path, 0o600)
            
            # Atomically replace the file
            os.replace(tmp_file_path, validated_path)
            
            logging.info("Calibration data saved successfully")
            return True
        except Exception as e:
            logging.warning(f"Failed to save calibration data: {e}", exc_info=True)
            # Clean up temp file if it exists
            if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
            return False

    def smart_calibration(self):
        saved_data = self.load_calibration_data()
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        mic = self.select_best_microphone()
        if saved_data:
            recognizer.energy_threshold = saved_data['energy_threshold']
            recognizer.pause_threshold = saved_data['pause_threshold']
            try:
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source, duration=2)
            except Exception as e:
                logging.warning(f"Ambient adjustment failed: {e}", exc_info=True)
        else:
            self.enhanced_calibration()

    def enhanced_calibration(self):
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        mic = self.select_best_microphone()
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=4)
            initial_threshold = recognizer.energy_threshold
            try:
                with mic as source:
                    audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)
                    test_result = recognizer.recognize_google(audio, language='en-US')
                if len(test_result.split()) >= 3:
                    pass
                else:
                    recognizer.energy_threshold = max(150, recognizer.energy_threshold * 0.8)
            except Exception:
                recognizer.energy_threshold = 250
                recognizer.pause_threshold = 3.5
            self.save_calibration_data(
                recognizer.energy_threshold,
                recognizer.pause_threshold,
                success_rate=1.0
            )
        except Exception as e:
            recognizer.energy_threshold = 300
            recognizer.pause_threshold = 4.0
            self.save_calibration_data(
                recognizer.energy_threshold,
                recognizer.pause_threshold,
                success_rate=0.3
            )

    def speak(self, text, wait=False):
        import threading
        def speak_thread():
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as e:
                logging.exception(f"TTS Error in speak (text={text}, wait={wait}):")
        if wait:
            speak_thread()
            return None
        else:
            thread = threading.Thread(target=speak_thread, daemon=True)
            thread.start()
            return thread

    def listen_for_command(self, timeout=3):
        """Listen for voice command with proper resource management."""
        import speech_recognition as sr
        import time
        from contextlib import contextmanager
        
        @contextmanager
        def audio_resources():
            """Context manager for proper audio resource cleanup."""
            recognizer = None
            mic = None
            try:
                recognizer = sr.Recognizer()
                mic = self.select_best_microphone()
                yield recognizer, mic
            finally:
                # Proper cleanup without manual del
                if recognizer:
                    recognizer = None
                if mic:
                    mic = None
        
        try:
            with audio_resources() as (recognizer, mic):
                # Apply rate limiting for Google Speech API
                self._apply_google_api_rate_limit()
                
                with mic as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.2)
                    audio = recognizer.listen(
                        source,
                        timeout=timeout,
                        phrase_time_limit=7
                    )
                
                # Try multiple recognition approaches with proper error handling
                command = self._try_speech_recognition(recognizer, audio)
                if command:
                    self.success_count += 1
                    return command
                
                self.adjust_sensitivity()
                return None
                
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            logging.exception(f"Error in listen_for_command: {e}")
            return None

    def _apply_google_api_rate_limit(self):
        """Apply rate limiting for Google Speech API (45 calls per minute)."""
        import time
        
        if not hasattr(self, '_last_api_call'):
            self._last_api_call = 0
            self._api_call_interval = 60.0 / 45  # 45 calls per minute
        
        now = time.time()
        time_since_last = now - self._last_api_call
        if time_since_last < self._api_call_interval:
            time.sleep(self._api_call_interval - time_since_last)
        self._last_api_call = time.time()

    def _try_speech_recognition(self, recognizer, audio):
        """Try speech recognition with multiple fallback options."""
        import speech_recognition as sr
        
        # Try primary language (US English)
        try:
            return recognizer.recognize_google(audio, language='en-US').lower()
        except (sr.UnknownValueError, sr.RequestError):
            pass
        
        # Try fallback language (UK English)
        try:
            return recognizer.recognize_google(audio, language='en-GB').lower()
        except (sr.UnknownValueError, sr.RequestError):
            pass
        
        # Try with confidence analysis
        try:
            results = recognizer.recognize_google(audio, language='en-US', show_all=True)
            if results and 'alternative' in results:
                alternatives = results['alternative']
                if alternatives:
                    command = alternatives[0]['transcript'].lower()
                    confidence = alternatives[0].get('confidence', 0)
                    if confidence > 0.3:
                        return command
        except (sr.UnknownValueError, sr.RequestError):
            pass
        
        return None

    def listen_for_wake_word(self):
        import speech_recognition as sr
        try:
            recognizer = sr.Recognizer()
            mic = self.select_best_microphone()
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio = recognizer.listen(
                    source,
                    timeout=30,
                    phrase_time_limit=5
                )
            try:
                recognized_text = recognizer.recognize_google(audio, language='en-US').lower()
                # No manual deletion needed - Python's garbage collector will handle cleanup
                if self.wake_word.lower() in recognized_text:
                    return True
                else:
                    return False
            except sr.UnknownValueError:
                return False
            except sr.RequestError:
                return False
        except sr.WaitTimeoutError:
            return False
        except Exception as e:
            logging.exception(f"Wake word listening error in listen_for_wake_word (wake_word={self.wake_word}):")
            return False

    def adjust_sensitivity(self):
        if self.attempt_count > 2:
            success_rate = self.success_count / self.attempt_count
            if success_rate < 0.3:
                self.recognizer.energy_threshold = max(100, self.recognizer.energy_threshold * 0.7)
                self.recognizer.pause_threshold = min(5.0, self.recognizer.pause_threshold * 1.2)
