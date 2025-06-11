# 🎤 Enhanced Spotify Voice Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)  

A sophisticated Linux-native voice-controlled Spotify assistant with **wake word detection**, **persistent voice calibration**, and **background mode support**. Optimized for Hyprland on Arch Linux but compatible with other Linux distributions. Now fully modularized for maintainability and clarity.

## ✨ Key Features

- 🛌 **Wake Word Activation**: Say "jarvis" to wake the assistant
- 🎵 **Complete Song Recognition**: Captures full song names like "Hotel California by Eagles"
- 🔧 **Persistent Calibration**: One-time voice setup, remembers your settings
- 📱 **Background Mode**: Works silently with desktop notifications (Hyprland optimized)
- 🎯 **Smart Fallback**: Automatic text mode when voice recognition fails
- 🔊 **Enhanced Audio Processing**: Extended pause detection for natural speech
- 💾 **Zero Configuration**: Saves voice settings automatically
- **Log Rotation**: Log files are automatically rotated—no manual cleanup needed. Up to 5 log files of 1MB each are kept in `logs/`.

## 🎭 How It Works

**Wake Word Mode (Default):**
1. 😴 **Sleeping**: App listens only for "jarvis"
2. 👂 **Awakened**: Say "jarvis" to activate
3. 🎵 **Command**: Speak your full command ("play Hotel California by Eagles")
4. ✅ **Execute**: Song plays, app returns to sleep
5. 🔄 **Repeat**: No interruptions while you enjoy music

**Smart Timeouts:**
- **3 seconds** to start speaking after wake word
- **7 seconds** to complete your full command
- **30 seconds** wake word listening timeout

## 🎯 Voice Commands

### Music Control
```
"jarvis" → "play Bohemian Rhapsody by Queen"
"jarvis" → "play Hotel California"
"jarvis" → "pause"
"jarvis" → "next track"
"jarvis" → "previous"
"jarvis" → "volume up"
"jarvis" → "what's playing"
```

### System Commands
```
"jarvis" → "quit"
Ctrl+C → Switch to text mode
Type 'voice' → Return to voice mode
Type 'wake' → Change wake word
Type 'recalibrate' → Redo voice setup
```

## 🚀 Quick Start

### 1. Install Dependencies

**Arch Linux (Automated):**
```bash
chmod +x setup.sh
./setup.sh
```

**Manual Installation:**
```bash
# Arch Linux
sudo pacman -S python python-pip portaudio espeak-ng alsa-utils pulseaudio libnotify

# Ubuntu/Debian
sudo apt install python3 python3-pip portaudio19-dev espeak-ng libnotify-bin

# Install Python packages
pip install -r requirements.txt
```

### 2. Get Spotify API Credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Click "Create an App"
3. App Name: "Enhanced Voice Assistant"
4. Copy **Client ID** and **Client Secret**
5. Add Redirect URI: `http://127.0.0.1:8080/callback`

### 3. Configure Environment

```bash
cp .env.template .env
nano .env
```

Fill in your Spotify credentials:
```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback
```

### 4. Start the Assistant


```bash
# Make sure Spotify is running
spotify &

# Start the enhanced assistant (from project root)
python -m app.main
```

### 5. First Time Setup

1. **Voice Calibration**: App will ask you to say "play Hotel California by Eagles" once
2. **Spotify Authorization**: Browser opens for Spotify login (first time only)
3. **Ready to Use**: Wake word "jarvis" is now active

## 🏗️ Enhanced Architecture

```
┌─────────────────────────────────────────────┐
│        Enhanced Voice Assistant             │
├─────────────────────────────────────────────┤
│  🛌 Wake Word Detection (Built-in)          │
├─────────────────────────────────────────────┤
│  🎤 Enhanced Speech Recognition (Google)    │
├─────────────────────────────────────────────┤
│  💾 Persistent Voice Calibration            │
├─────────────────────────────────────────────┤
│  🧠 Smart Command Processing                │
├─────────────────────────────────────────────┤
│  🎵 Spotify Web API Integration             │
├─────────────────────────────────────────────┤
│  📱 Desktop Notifications (notify-send)     │
├─────────────────────────────────────────────┤
│  🗣️ Contextual Text-to-Speech               │
└─────────────────────────────────────────────┘
```

### Core Technologies

- **spotipy**: Spotify Web API integration
- **SpeechRecognition**: Google Speech-to-Text
- **pyttsx3**: Text-to-speech synthesis
- **pyaudio**: Audio input/output
- **notify-send**: Desktop notifications
- **Built-in wake word**: No external dependencies

## 🎛️ Advanced Features

### Persistent Voice Calibration
- **One-time setup**: Voice test only on first run
- **Auto-saves settings**: Stored in `.voice_calibration.json`
- **7-day validity**: Recalibrates weekly for optimal performance
- **Ambient noise adaptation**: Adjusts to your environment

### Background Mode (Hyprland Optimized)
- **Desktop notifications**: Visual feedback for all actions
- **Silent operation**: No terminal interaction required
- **System tray friendly**: Runs minimized
- **Resource efficient**: Sleeps between commands

### Smart Fallback System
- **Automatic text mode**: When voice recognition fails
- **Seamless transitions**: Voice ↔ Text mode switching
- **Recovery options**: Easy return to voice mode
- **Graceful degradation**: Never leaves you stranded

## 🔧 Customization

### Change Wake Word
```bash
# In text mode, type:
wake
# Enter new wake word (e.g., "computer", "assistant")
```

### Adjust Voice Sensitivity
The app automatically adjusts sensitivity based on success rate. For manual calibration:
```bash
# In text mode, type:
recalibrate
```

### Background Notifications
Configure notification daemon for your DE:
```bash
# Hyprland (mako)
sudo pacman -S mako

# i3/sway (dunst)
sudo pacman -S dunst

# GNOME/KDE (built-in)
# No additional setup needed
```

## 🐛 Troubleshooting

### Common Issues

**1. Wake word not detected**
- Speak clearly and at normal pace
- Check microphone permissions
- Try recalibrating: type `recalibrate` in text mode

**2. "No module named 'pyaudio'"**
```bash
# Install portaudio first
sudo pacman -S portaudio  # Arch
sudo apt install portaudio19-dev  # Ubuntu

# Reinstall pyaudio
pip install --force-reinstall pyaudio
```

**3. "No active device found"**
- Ensure Spotify is running and logged in
- Start playing something in Spotify first
- Check Spotify Connect devices

**4. Speech recognition fails**
- Check internet connection (uses Google API)
- Test microphone: `arecord -d 5 test.wav && aplay test.wav`
- App will automatically fall back to text mode

**5. Notifications not working**
```bash
# Install notification system
sudo pacman -S libnotify  # Arch
sudo apt install libnotify-bin  # Ubuntu

# Test notifications
notify-send "Test" "Notification working"
```

### Debug Commands

```bash
# Test components
python -c "import spotipy; print('✅ Spotify OK')"
python -c "import speech_recognition; print('✅ Speech Recognition OK')"
python -c "import pyttsx3; print('✅ TTS OK')"

# Test microphone
arecord -d 3 test.wav && aplay test.wav

# Check audio devices
arecord -l
```

## 🔮 Roadmap

### Phase 2 Features
- 🎵 **Playlist Management**: Create and manage playlists by voice
- 🤖 **AI Music Discovery**: Smart recommendations based on mood
- 🌐 **Multi-Platform**: YouTube Music, Apple Music support
- 📱 **Mobile Companion**: Android/iOS remote control
- 🏠 **Smart Home Integration**: Control lights, temperature
- 🎯 **Custom Wake Words**: Train personalized activation phrases

### Technical Improvements
- 🧠 **Offline Mode**: Local speech recognition option
- 🔊 **Multi-Room Audio**: Sync across multiple devices
- 🌍 **Multi-Language**: Support for other languages
- 📊**🎵 Made with ❤️ for music lovers and Linux enthusiasts**

*"Hey jarvis, play some good music!"* 🎤
listening habits

## 📁 Project Structure

```
spotify-voice-assistant/

├── app/
│   ├── assistant.py           # 🎤 Main orchestration (entry point logic)
│   ├── audio.py               # 🎙️ Audio, calibration, and recognition logic
│   ├── spotify_control.py     # � Spotify API integration
│   ├── notifications.py       # 🔔 Desktop notification logic
│   ├── utils.py               # ⚙️ Environment loader
│   ├── main.py                # 🚀 Entry point (run with python -m app.main)
│   └── __init__.py            # 📦 Package marker
├── requirements.txt           # 📦 Python dependencies
├── env/.env                   # ⚙️ Environment variables
├── setup.sh                   # 🚀 Arch Linux setup script
├── README.md                  # 📖 This file
├── QUICKSTART.md              # ⚡ Quick setup guide
├── calibration/.voice_calibration.json # 💾 Auto-generated voice settings
├── cache/.spotify_cache       # 🔑 Auto-generated Spotify tokens
├── logs/voice_assistant.log   # 📝 Log file
└── venv/                      # 🐍 Virtual environment
```

## 🤝 Contributing

Contributions welcome! Areas where help is needed:

- 🐛 **Bug Reports**: Test on different Linux distributions
- 🎵 **Feature Requests**: Music discovery and playlist features
- 🌍 **Translations**: Multi-language support
- 📱 **Desktop Environments**: Testing on KDE, GNOME, etc.
- 🎤 **Voice Models**: Offline speech recognition

### Development Setup

```bash
git clone <your-fork>
cd spotify-voice-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test your changes
python -m app.main
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Spotify Web API**: Music control foundation
- **Google Speech Recognition**: Accurate voice recognition
- **Python Community**: Excellent libraries and tools
- **Linux Desktop Developers**: Making background mode possible
- **Hyprland Community**: Inspiration for modern desktop integration

---

## 📧 Contact

Created by [Arindam Tripathi](https://github.com/ArindamTripathi619).  
For any inquiries or suggestions, feel free to reach out!

### Social Links  
[![Instagram](https://img.shields.io/badge/Instagram-%23E4405F.svg?&style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/_arindxm/)  [![Facebook](https://img.shields.io/badge/Facebook-%231877F2.svg?&style=for-the-badge&logo=facebook&logoColor=white)](https://www.facebook.com/arindam.tripathi.180/)  [![LinkedIn](https://img.shields.io/badge/LinkedIn-%230077B5.svg?&style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/arindam-tripathi-962551349/)  [![YouTube](https://img.shields.io/badge/YouTube-%23FF0000.svg?&style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@arindamtripathi4602)  

---

**🎵 Made with ❤️ by Arindam Tripathi**

*"Hey jarvis, play some good music!"* 🎤
