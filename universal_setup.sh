#!/usr/bin/env bash
# Universal Interactive Setup Script for Enhanced Spotify Voice Assistant
# Supports: Arch, Ubuntu/Debian, Fedora, openSUSE, and most modern distros

set -e

banner() {
    echo -e "\n🎤 Enhanced Spotify Voice Assistant Universal Setup"
    echo "✨ Features: Wake word 'jarvis', persistent calibration, background mode"
    echo
}

banner

# Detect package manager
detect_pm() {
    if command -v pacman >/dev/null; then
        echo "pacman"
    elif command -v apt >/dev/null; then
        echo "apt"
    elif command -v dnf >/dev/null; then
        echo "dnf"
    elif command -v zypper >/dev/null; then
        echo "zypper"
    else
        echo "unknown"
    fi
}

PM=$(detect_pm)

if [ "$PM" = "unknown" ]; then
    echo "❌ Unsupported Linux distribution. Please install dependencies manually."
    echo "Required: python3 python3-pip portaudio espeak-ng libnotify"
    exit 1
fi

# Confirm system dependencies
read -p "📦 Install system dependencies for your distro? [Y/n] " sysdeps
sysdeps=${sysdeps:-Y}
if [[ $sysdeps =~ ^[Yy]$ ]]; then
    case "$PM" in
        pacman)
            sudo pacman -Sy --noconfirm python python-pip portaudio espeak-ng libnotify
            ;;
        apt)
            sudo apt update
            sudo apt install -y python3 python3-pip portaudio19-dev espeak-ng libnotify-bin
            ;;
        dnf)
            sudo dnf install -y python3 python3-pip portaudio-devel espeak-ng libnotify
            ;;
        zypper)
            sudo zypper install -y python3 python3-pip portaudio-devel espeak-ng libnotify-tools
            ;;
    esac
else
    echo "⚠️  Skipping system dependency installation. Make sure all dependencies are present!"
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    read -p "🐍 Create Python virtual environment? [Y/n] " venvcreate
    venvcreate=${venvcreate:-Y}
    if [[ $venvcreate =~ ^[Yy]$ ]]; then
        python3 -m venv venv
        echo "✅ Virtual environment created."
    else
        echo "⚠️  Skipping venv creation. Using system Python."
    fi
else
    echo "✅ Virtual environment already exists."
fi

# Activate venv if present
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install Python dependencies
read -p "📦 Install Python dependencies from requirements.txt? [Y/n] " pydeps
pydeps=${pydeps:-Y}
if [[ $pydeps =~ ^[Yy]$ ]]; then
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt || python3 -m pip install pyaudio spotipy SpeechRecognition pyttsx3
fi

# Check for notify-send
if ! command -v notify-send >/dev/null; then
    echo "[!] notify-send not found. Please ensure a notification daemon is running."
    echo "On i3/sway: sudo pacman -S dunst   |   On Hyprland: sudo pacman -S mako"
    echo "On Ubuntu: sudo apt install dunst"
fi

# Check for Spotify (native or Flatpak)
if ! command -v spotify >/dev/null && ! flatpak list | grep -q com.spotify.Client; then
    echo "[!] Spotify is not installed."
    read -p "Install Spotify via Flatpak? [Y/n] " flatpakspot
    flatpakspot=${flatpakspot:-Y}
    if [[ $flatpakspot =~ ^[Yy]$ ]]; then
        flatpak install -y flathub com.spotify.Client
    else
        echo "Install manually:"
        echo "  Arch: sudo pacman -S spotify"
        echo "  Ubuntu: sudo snap install spotify || flatpak install flathub com.spotify.Client"
        echo "  Fedora/openSUSE: flatpak install flathub com.spotify.Client"
    fi
fi

# Create env/.env file if it doesn't exist
if [ ! -f env/.env ]; then
    read -p "📝 Create env/.env file from template? [Y/n] " envfile
    envfile=${envfile:-Y}
    if [[ $envfile =~ ^[Yy]$ ]]; then
        cp env/.env.template env/.env
        echo "✅ Created env/.env file. Please edit it with your credentials."
    fi
else
    echo "✅ env/.env file already exists."
fi

echo
cat << EOF
🎉 Setup complete!

📋 Next steps:
1. Edit the env/.env file with your Spotify credentials:
   nano env/.env

2. Get Spotify API credentials:
   - Go to https://developer.spotify.com/dashboard/
   - Create a new app named 'Enhanced Voice Assistant'
   - Copy Client ID and Client Secret to .env
   - Add redirect URI: http://127.0.0.1:8080/callback

3. Start Spotify on your system (not needed if using Flatpak, the assistant will auto-launch it):
   spotify &

4. Run the enhanced voice assistant:
   python -m app.main

🎤 Enhanced voice commands (wake word: 'jarvis'):
   Wake word: Say 'jarvis' to activate, then:
   - 'play Hotel California by Eagles' - Play specific song
   - 'play Bohemian Rhapsody' - Play song (artist optional)
   - 'pause' - Pause playback
   - 'next track' - Skip to next
   - 'previous' - Go to previous track
   - 'volume up/down' - Adjust volume
   - 'what's playing' - Get current track info
   - 'quit' - Stop the assistant

🔧 System commands:
   - Ctrl+C → Switch to text mode
   - Type 'voice' → Return to voice mode
   - Type 'wake' → Change wake word
   - Type 'recalibrate' → Redo voice setup

🎛️ Smart features:
   - ✅ One-time voice calibration (remembers your settings, see calibration/.voice_calibration.json)
   - ✅ Auto-fallback to text mode when voice fails
   - ✅ Desktop notifications for background operation (no terminal clutter)
   - ✅ Wake word detection with no external dependencies
   - ✅ Logs stored in logs/voice_assistant.log
   - ✅ Spotify cache in cache/.spotify_cache
EOF