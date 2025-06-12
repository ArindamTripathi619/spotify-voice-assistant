import subprocess
import sys

def launch_spotify():
    """Launch Spotify desktop app on Linux. Try native, then Flatpak."""
    try:
        subprocess.Popen(["spotify"])
        return True
    except FileNotFoundError:
        # Try Flatpak
        try:
            subprocess.Popen(["flatpak", "run", "com.spotify.Client"])
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Error launching Spotify via Flatpak: {e}")
            return False
    except Exception as e:
        print(f"Error launching Spotify: {e}")
        return False
