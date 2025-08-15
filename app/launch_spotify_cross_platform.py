import subprocess
import sys
import os
import logging
from .platform_utils import get_spotify_executable_path, is_windows, is_linux, is_mac

def launch_spotify():
    """Launch Spotify desktop app cross-platform."""
    spotify_path = get_spotify_executable_path()
    
    if not spotify_path:
        logging.warning("Spotify executable not found on this platform")
        return False
    
    try:
        if is_windows():
            return _launch_spotify_windows(spotify_path)
        elif is_linux():
            return _launch_spotify_linux(spotify_path)
        elif is_mac():
            return _launch_spotify_mac(spotify_path)
        else:
            logging.error("Unsupported platform for Spotify launching")
            return False
    except Exception as e:
        logging.error(f"Failed to launch Spotify: {e}")
        return False

def _launch_spotify_windows(spotify_path):
    """Launch Spotify on Windows."""
    try:
        # Use subprocess.Popen with shell=False for better security
        subprocess.Popen([spotify_path], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        logging.info(f"Spotify launched successfully on Windows: {spotify_path}")
        return True
    except FileNotFoundError:
        logging.error(f"Spotify executable not found at: {spotify_path}")
        return False
    except Exception as e:
        logging.error(f"Error launching Spotify on Windows: {e}")
        return False

def _launch_spotify_linux(spotify_path):
    """Launch Spotify on Linux."""
    try:
        if spotify_path == "spotify":
            subprocess.Popen(["spotify"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif "flatpak" in spotify_path:
            subprocess.Popen(["flatpak", "run", "com.spotify.Client"], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen([spotify_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        logging.info(f"Spotify launched successfully on Linux: {spotify_path}")
        return True
    except FileNotFoundError:
        logging.error(f"Spotify executable not found: {spotify_path}")
        return False
    except Exception as e:
        logging.error(f"Error launching Spotify on Linux: {e}")
        return False

def _launch_spotify_mac(spotify_path):
    """Launch Spotify on macOS."""
    try:
        subprocess.Popen(["open", "-a", "Spotify"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info(f"Spotify launched successfully on macOS: {spotify_path}")
        return True
    except Exception as e:
        logging.error(f"Error launching Spotify on macOS: {e}")
        return False

def check_spotify_installation():
    """Check if Spotify is installed on the current platform."""
    spotify_path = get_spotify_executable_path()
    return spotify_path is not None

def get_spotify_installation_instructions():
    """Get platform-specific Spotify installation instructions."""
    if is_windows():
        return {
            "methods": [
                "Download from https://www.spotify.com/download/windows/",
                "Install via Microsoft Store",
                "Use Windows Package Manager: winget install Spotify.Spotify"
            ],
            "notes": "The assistant supports both desktop app and Windows Store versions"
        }
    elif is_linux():
        return {
            "methods": [
                "Flatpak: flatpak install flathub com.spotify.Client",
                "Snap: sudo snap install spotify",
                "AUR (Arch): yay -S spotify",
                "Debian/Ubuntu: Download .deb from spotify.com"
            ],
            "notes": "Flatpak version is recommended for best compatibility"
        }
    elif is_mac():
        return {
            "methods": [
                "Download from https://www.spotify.com/download/mac/",
                "Install via Homebrew: brew install --cask spotify",
                "Install from Mac App Store"
            ],
            "notes": "All versions are supported"
        }
    else:
        return {
            "methods": ["Visit https://www.spotify.com/download/ for your platform"],
            "notes": "Platform-specific launcher not implemented"
        }
