import speech_recognition as sr
import pyttsx3
import logging
import os

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
        self.success_count = 0
        self.attempt_count = 0
        logging.info("AudioManager initialized.")


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
            logging.error(f"Audio setup failed: {e}")
            if self.notifier:
                self.notifier.send_notification(
                    "❌ Audio Error",
                    f"Failed to setup audio: {str(e)[:50]}...",
                    "dialog-error"
                )
            raise

    def select_best_microphone(self):
        mic_list = sr.Microphone.list_microphone_names()
        sample_rate = 44100  # Match typical output device sample rate
        try:
            return sr.Microphone(sample_rate=sample_rate)
        except Exception:
            if mic_list:
                return sr.Microphone(device_index=0, sample_rate=sample_rate)
            else:
                raise RuntimeError("No microphones found.")

    def load_calibration_data(self):
        import json
        from datetime import datetime, timedelta
        try:
            if os.path.exists(self.calibration_file):
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                calibration_date = datetime.fromisoformat(data.get('date', '2000-01-01'))
                if datetime.now() - calibration_date < timedelta(days=7):
                    if 'wake_word' in data:
                        self.wake_word = data['wake_word']
                    return data
            return None
        except Exception as e:
            logging.warning(f"Failed to load calibration data: {e}")
            return None

    def save_calibration_data(self, energy_threshold, pause_threshold, success_rate=1.0):
        import json
        from datetime import datetime
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
            return True
        except Exception as e:
            logging.warning(f"Failed to save calibration data: {e}")
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
                logging.warning(f"Ambient adjustment failed: {e}")
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
                logging.error(f"TTS Error: {e}")
        if wait:
            speak_thread()
            return None
        else:
            thread = threading.Thread(target=speak_thread, daemon=True)
            thread.start()
            return thread

    def listen_for_command(self, timeout=3):
        import speech_recognition as sr
        try:
            recognizer = sr.Recognizer()
            mic = self.select_best_microphone()
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=7
                )
            command = None
            try:
                command = recognizer.recognize_google(audio, language='en-US').lower()
                self.success_count += 1
                del recognizer
                del mic
                return command
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                pass
            try:
                command = recognizer.recognize_google(audio, language='en-GB').lower()
                self.success_count += 1
                del recognizer
                del mic
                return command
            except:
                pass
            try:
                results = recognizer.recognize_google(audio, language='en-US', show_all=True)
                if results and 'alternative' in results:
                    alternatives = results['alternative']
                    if alternatives:
                        command = alternatives[0]['transcript'].lower()
                        confidence = alternatives[0].get('confidence', 0)
                        if confidence > 0.3:
                            self.success_count += 1
                            del recognizer
                            del mic
                            return command
            except:
                pass
            self.adjust_sensitivity()
            del recognizer
            del mic
            return None
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            logging.error(f"Enhanced listening error: {e}")
            return None
        finally:
            self.attempt_count += 1

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
                del recognizer
                del mic
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
            logging.error(f"Wake word listening error: {e}")
            return False

    def adjust_sensitivity(self):
        if self.attempt_count > 2:
            success_rate = self.success_count / self.attempt_count
            if success_rate < 0.3:
                self.recognizer.energy_threshold = max(100, self.recognizer.energy_threshold * 0.7)
                self.recognizer.pause_threshold = min(5.0, self.recognizer.pause_threshold * 1.2)
