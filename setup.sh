#!/bin/bash

# Enhanced Spotify Voice Assistant Setup Script
# Automated setup for Arch Linux with wake word "jarvis"

set -e  # Exit on any error

echo "🎤 Setting up Enhanced Spotify Voice Assistant for Arch Linux..."
echo "✨ Features: Wake word 'jarvis', persistent calibration, background mode"
echo

# Check if running on Arch Linux
if ! command -v pacman &> /dev/null; then
    echo "❌ This setup script is designed for Arch Linux."
    echo "Please install dependencies manually on your system."
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo pacman -S --needed --noconfirm \
    python \
    python-pip \
    portaudio \
    espeak-ng \
    alsa-utils \
    pulseaudio \
    libnotify

# Create virtual environment
echo "🐍 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✅ Virtual environment created."
else
    echo "✅ Virtual environment already exists."
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies in virtual environment..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Check if Spotify is installed
if ! command_exists spotify; then
    echo "⚠️  Spotify is not installed. You can install it using:"
    echo "   AUR: yay -S spotify"
    echo "   Snap: sudo snap install spotify"
    echo "   Flatpak: flatpak install spotify"
    echo
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "✅ Created .env file. Please edit it with your credentials."
else
    echo "✅ .env file already exists."
fi

echo
echo "🎉 Setup complete!"
echo
echo "📋 Next steps:"
echo "1. Edit the .env file with your Spotify credentials:"
echo "   nano .env"
echo
echo "2. Get Spotify API credentials:"
echo "   - Go to https://developer.spotify.com/dashboard/"
echo "   - Create a new app named 'Enhanced Voice Assistant'"
echo "   - Copy Client ID and Client Secret to .env"
echo "   - Add redirect URI: http://127.0.0.1:8080/callback"
echo
echo "3. Start Spotify on your system:"
echo "   spotify &"
echo
echo "4. Run the enhanced voice assistant:"
echo "   python enhanced_voice_assistant.py"
echo
echo "🎤 Enhanced voice commands (wake word: 'jarvis'):"
echo "   Wake word: Say 'jarvis' to activate, then:"
echo "   - 'play Hotel California by Eagles' - Play specific song"
echo "   - 'play Bohemian Rhapsody' - Play song (artist optional)"
echo "   - 'pause' - Pause playback"
echo "   - 'next track' - Skip to next"
echo "   - 'previous' - Go to previous track"
echo "   - 'volume up/down' - Adjust volume"
echo "   - 'what's playing' - Get current track info"
echo "   - 'quit' - Stop the assistant"
echo
echo "🔧 System commands:"
echo "   - Ctrl+C → Switch to text mode"
echo "   - Type 'voice' → Return to voice mode"
echo "   - Type 'wake' → Change wake word"
echo "   - Type 'recalibrate' → Redo voice setup"
echo
echo "🎛️ Smart features:"
echo "   - ✅ One-time voice calibration (remembers your settings)"
echo "   - ✅ Auto-fallback to text mode when voice fails"
echo "   - ✅ Desktop notifications for background operation"
echo "   - ✅ Wake word detection with no external dependencies"
echo

