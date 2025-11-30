import platform
import os
import sys

def get_platform():
    """Detect the current platform."""
    return platform.system().lower()

def is_windows():
    """Check if running on Windows."""
    return get_platform() == 'windows'

def is_linux():
    """Check if running on Linux."""
    return get_platform() == 'linux'

def is_mac():
    """Check if running on macOS."""
    return get_platform() == 'darwin'

def get_spotify_executable_path():
    """Get platform-specific Spotify executable path."""
    if is_windows():
        # Common Windows Spotify installation paths
        possible_paths = [
            os.path.expanduser("~\\AppData\\Roaming\\Spotify\\Spotify.exe"),
            "C:\\Users\\%USERNAME%\\AppData\\Roaming\\Spotify\\Spotify.exe",
            "C:\\Program Files\\Spotify\\Spotify.exe",
            "C:\\Program Files (x86)\\Spotify\\Spotify.exe"
        ]
        
        # Check Windows Store version with proper error handling
        try:
            import logging
            # Check if Spotify is installed via Windows Store
            store_path = "Microsoft\\WindowsApps\\Spotify.exe"
            local_appdata = os.environ.get('LOCALAPPDATA')
            if local_appdata:
                full_store_path = os.path.join(local_appdata, store_path)
                if os.path.exists(full_store_path) and os.access(full_store_path, os.X_OK):
                    possible_paths.insert(0, full_store_path)
        except (ImportError, OSError, KeyError) as e:
            # Log the error but continue - this is not critical for functionality
            import logging
            logging.debug(f"Windows Store Spotify check failed: {e}")
            pass
        
        for path in possible_paths:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                return expanded_path
        return None
    
    elif is_linux():
        # Linux paths - use safe subprocess instead of os.system()
        import subprocess
        import shutil
        
        # Safe executable detection using shutil.which
        if shutil.which("spotify"):
            return "spotify"
        
        # Safe flatpak detection with timeout
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application"],
                capture_output=True, text=True, timeout=5
            )
            if "com.spotify.Client" in result.stdout:
                return "flatpak run com.spotify.Client"
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        return None
    
    elif is_mac():
        # macOS paths
        possible_paths = [
            "/Applications/Spotify.app/Contents/MacOS/Spotify",
            "/System/Applications/Spotify.app/Contents/MacOS/Spotify"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    return None

def get_notification_command():
    """Get platform-specific notification command."""
    if is_windows():
        return None  # Will use Python library
    elif is_linux():
        return "notify-send"
    elif is_mac():
        return "osascript"  # For AppleScript notifications
    return None

def get_audio_requirements():
    """Get platform-specific audio requirements and installation commands."""
    if is_windows():
        return {
            "system_deps": [],  # No system packages needed on Windows
            "python_deps": ["pyaudio", "SpeechRecognition", "pyttsx3"],
            "install_commands": [
                "pip install pyaudio",
                "pip install SpeechRecognition", 
                "pip install pyttsx3"
            ],
            "notes": [
                "PyAudio may require Microsoft C++ Build Tools on Windows",
                "Alternative: pip install pipwin && pipwin install pyaudio"
            ]
        }
    elif is_linux():
        return {
            "system_deps": ["portaudio", "espeak-ng", "alsa-utils", "pulseaudio"],
            "python_deps": ["pyaudio", "SpeechRecognition", "pyttsx3"],
            "install_commands": [
                "sudo pacman -S portaudio espeak-ng alsa-utils pulseaudio",  # Arch
                "sudo apt install portaudio19-dev espeak-ng",  # Ubuntu/Debian
            ]
        }
    elif is_mac():
        return {
            "system_deps": ["portaudio"],
            "python_deps": ["pyaudio", "SpeechRecognition", "pyttsx3"],
            "install_commands": [
                "brew install portaudio",
                "pip install pyaudio SpeechRecognition pyttsx3"
            ]
        }
    return {}

def setup_platform_environment():
    """Perform platform-specific environment setup."""
    if is_windows():
        # Windows-specific setup - only available on Windows
        try:
            import ctypes
            # Enable ANSI color codes in Windows terminal (Windows only)
            if sys.platform == "win32":
                kernel32 = ctypes.windll.kernel32  # type: ignore
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except (ImportError, AttributeError, OSError):
            # Silently fail if not available - this is not critical
            pass
    
    elif is_linux():
        # Linux-specific setup (if needed)
        pass
    
    elif is_mac():
        # macOS-specific setup (if needed)
        pass
