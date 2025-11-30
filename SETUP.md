# Setup Guide - Enhanced Spotify Voice Assistant

This guide provides comprehensive setup instructions for all supported platforms.

## 🚀 Quick Start (Recommended)

### Universal Setup Script

The easiest way to get started is using our universal setup script that automatically detects your platform:

```bash
# Make executable and run
chmod +x setup
./setup
```

This script will:
- Detect your operating system (Linux, Windows, macOS)
- Install system dependencies
- Create Python virtual environment  
- Install Python packages
- Check for Spotify installation
- Create configuration files
- Provide next steps

## 📋 Platform-Specific Instructions

### Linux (All Distributions)

**Automatic Setup:**
```bash
./universal_setup.sh
```

**Manual Setup:**
1. Install system dependencies:
   - **Arch/Manjaro:** `sudo pacman -S python python-pip portaudio espeak-ng libnotify`
   - **Ubuntu/Debian:** `sudo apt install python3 python3-pip portaudio19-dev espeak-ng libnotify-bin`
   - **Fedora:** `sudo dnf install python3 python3-pip portaudio-devel espeak-ng libnotify`
   - **openSUSE:** `sudo zypper install python3 python3-pip portaudio-devel espeak-ng libnotify-tools`

2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Windows

**Automatic Setup (PowerShell - Recommended):**
```powershell
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```

**Automatic Setup (Command Prompt):**
```cmd
setup_windows.bat
```

**Manual Setup:**
1. Install Python from [python.org](https://python.org/downloads/)
   - ✅ Check "Add Python to PATH" during installation
2. Create virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

### macOS

**Automatic Setup:**
```bash
./universal_setup.sh  # Uses Homebrew
```

**Manual Setup:**
1. Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. Install dependencies: `brew install python portaudio espeak`
3. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install Python packages: `pip install -r requirements.txt`

## 🎵 Spotify Setup

1. **Install Spotify:**
   - **Linux:** `flatpak install flathub com.spotify.Client` or native package
   - **Windows:** Download from [spotify.com](https://www.spotify.com/download/windows/)
   - **macOS:** `brew install --cask spotify` or Mac App Store

2. **Get API Credentials:**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Create new app named "Enhanced Voice Assistant"
   - Copy Client ID and Client Secret
   - Add redirect URI: `http://127.0.0.1:8080/callback`

3. **Configure Environment:**
   ```bash
   cp env/.env.template env/.env
   nano env/.env  # Add your credentials
   ```

## 🎤 Running the Assistant

### Start the Assistant
```bash
# With virtual environment activated
python -m app.main

# Or direct execution
./venv/bin/python -m app.main  # Linux/macOS
venv\Scripts\python -m app.main  # Windows
```

### Voice Commands (Wake Word: "jarvis")
Say "jarvis" first, then:
- `"play Hotel California by Eagles"` - Play specific song
- `"pause"` / `"resume"` - Control playback
- `"next track"` / `"previous"` - Navigate tracks
- `"volume up"` / `"volume down"` - Adjust volume
- `"what's playing"` - Get current track info
- `"quit"` - Stop assistant

### System Controls
- **Ctrl+C** → Switch to text mode
- Type `voice` → Return to voice mode
- Type `wake` → Change wake word
- Type `recalibrate` → Redo voice setup

## 🛠️ Troubleshooting

### Common Issues

**PyAudio Installation Failed (Windows):**
1. Install Microsoft Visual C++ Build Tools
2. Or download PyAudio wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)
3. Install manually: `pip install downloaded_wheel.whl`

**No Audio Device Found:**
- Linux: Check `pulseaudio` or `pipewire` is running
- Windows: Ensure microphone permissions are granted
- macOS: Grant microphone access in System Preferences

**Spotify Not Found:**
- Ensure Spotify is installed and running
- The assistant can auto-launch Spotify if installed correctly

**Permission Denied (Linux):**
- Add user to audio group: `sudo usermod -a -G audio $USER`
- Logout and login again

### Advanced Configuration

**Custom Wake Word:**
- Edit `env/.env`: `WAKE_WORD=your_word_here`
- Or change during runtime with `wake` command

**Audio Settings:**
- Calibration data stored in `calibration/.voice_calibration.json`
- Logs available in `logs/voice_assistant.log`

**Notification Settings:**
- Linux: Requires notification daemon (dunst, mako, etc.)
- Windows: Uses native Windows 10+ notifications
- macOS: Uses native macOS notifications

## 📁 File Structure

```
spotify-voice-assistant/
├── app/                    # Main application code
├── env/                    # Environment configuration
├── cache/                  # Spotify authentication cache
├── calibration/            # Voice calibration data
├── logs/                   # Application logs
├── setup                   # Universal setup script
├── universal_setup.sh      # Linux multi-distro setup
├── setup_windows.ps1       # Windows PowerShell setup
├── setup_windows.bat       # Windows batch setup
├── requirements.txt        # Python dependencies
└── README.md              # Project overview
```

## 🎯 Features

- ✅ **Cross-platform compatibility** (Linux, Windows, macOS)
- ✅ **Wake word detection** (customizable, default: "jarvis")
- ✅ **Persistent voice calibration** (remembers your settings)
- ✅ **Desktop notifications** (no terminal clutter)
- ✅ **Auto-fallback to text mode** (when voice fails)
- ✅ **Secure credential storage** (encrypted tokens)
- ✅ **Rate limiting** (prevents API abuse)
- ✅ **Comprehensive error handling** (graceful failures)

## 💡 Tips

1. **First Run:** Allow extra time for voice calibration
2. **Background Mode:** Use Ctrl+C for text mode when voice isn't working
3. **Multiple Devices:** The assistant will auto-select the best Spotify device
4. **Custom Commands:** Modify `app/assistant.py` to add new voice commands
5. **Debugging:** Check `logs/voice_assistant.log` for detailed error information

---

For additional help, check the [README.md](README.md) or open an issue on GitHub.