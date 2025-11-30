"""
Spotify Voice Assistant Package
Enhanced cross-platform voice assistant for Spotify control.
"""

__version__ = "1.0.0"
__author__ = "DevCrewX"

# Import main classes for easier access
from .assistant import EnhancedVoiceAssistant
from .spotify_control import SpotifyController
from .audio import AudioManager
from .notifications import NotificationManager
from .platform_utils import is_windows, is_linux, is_mac, get_spotify_executable_path
from .utils import load_environment

__all__ = [
    'EnhancedVoiceAssistant', 
    'SpotifyController', 
    'AudioManager', 
    'NotificationManager',
    'is_windows', 
    'is_linux', 
    'is_mac', 
    'get_spotify_executable_path',
    'load_environment'
]