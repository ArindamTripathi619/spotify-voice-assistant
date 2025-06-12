# ⚡ Enhanced Spotify Voice Assistant - Quick Start

Get your **enhanced voice assistant** with wake word "jarvis" running in 5 minutes!

## 🚀 One-Command Setup (Arch Linux)

```bash
# Run automated setup
chmod +x setup.sh
./setup.sh

# Configure credentials
cp .env.template .env
nano .env

# Start the enhanced assistant (from project root)
python -m app.main
```

## 📋 Step-by-Step Guide

### Step 1: Install Dependencies

**Arch Linux (Automated):**
```bash
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

### Step 2: Get Spotify API Credentials

**Only Spotify API needed - No external wake word service!**

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Click "**Create an App**"
3. App Name: "Enhanced Voice Assistant"
4. Copy **Client ID** and **Client Secret**
5. Add Redirect URI: `http://127.0.0.1:8080/callback`

### Step 3: Configure Environment

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

### Step 4: Start Spotify

> **Note:** You do NOT need to manually start Spotify! The assistant will launch Spotify automatically if needed (supports Flatpak and native installs).

### Step 5: Run Enhanced Assistant

```bash
python -m app.main
```

## 🎤 First Time Setup

1. **Voice Calibration**: App asks you to say "play Hotel California by Eagles" **once**
2. **Spotify Authorization**: Browser opens for Spotify login (first time only)
3. **Ready**: Wake word "jarvis" is now active!

## 🎯 Voice Commands

**Wake Word:** Say "**jarvis**" to activate, then:

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
"jarvis" → "quit"              # Exit app
Ctrl+C → Switch to text mode    # Manual control
Type 'voice' → Return to voice  # Back to voice mode
Type 'wake' → Change wake word   # Customize activation
```

## 🔧 Smart Features

### Wake Word Mode (Default)
- **😴 Sleeps** between commands (no interruptions)
- **👂 Wakes** when you say "jarvis"
- **🎵 Executes** your command
- **😴 Sleeps** again until next "jarvis"

### Auto-Fallback
- **Voice fails** → Automatic text mode with notifications
- **Easy return** → Type 'voice' to go back
- **Never stuck** → Always have a way to control music

### Persistent Settings
- **One-time calibration** → Remembers your voice settings
- **Auto-saves** → No repeated setup
- **Background ready** → Perfect for Hyprland/i3/sway

### Log Rotation
- **Log files** are automatically rotated (up to 5 files, 1MB each). No manual cleanup needed.

## 🐛 Quick Troubleshooting

**Wake word not working?**
- Speak clearly: "jarvis" (pause) "play song name"
- Check microphone: `arecord -d 3 test.wav && aplay test.wav`
- Recalibrate: Type `recalibrate` in text mode

**"No active device" error?**
- Make sure Spotify is running and logged in
- Start playing something in Spotify first

**Speech recognition fails?**
- App automatically switches to text mode
- Check internet connection (uses Google Speech API)
- Type commands manually until voice works

**Notifications not showing?**
```bash
# Install notification system
sudo pacman -S libnotify  # Arch
sudo apt install libnotify-bin  # Ubuntu

# Test
notify-send "Test" "Working!"
```

## 📱 Background Mode

**Perfect for tiling window managers:**
- Run in background with desktop notifications
- No terminal interaction needed
- Visual feedback through notification system
- Resource efficient (sleeps when not needed)

```bash
# Run in background
python -m app.main &

# Or create a desktop entry/autostart
```

## 🎛️ Customization

```bash
# Change wake word (in text mode)
wake
# Enter: "computer", "assistant", "friday", etc.

# Recalibrate voice recognition
recalibrate

# Switch between voice and text modes
Ctrl+C  # → text mode
voice   # → voice mode
```

---

## 🆘 Need More Help?

- **Full documentation**: Check [README.md](README.md)
- **Component testing**: `python -c "import spotipy; print('OK')"`
- **Audio testing**: `arecord -d 3 test.wav && aplay test.wav`
- **Log analysis**: Run app and check terminal output

**🎵 Enjoy your enhanced voice-controlled music experience!**

*"Hey jarvis, play my favorite song!"* 🎤

