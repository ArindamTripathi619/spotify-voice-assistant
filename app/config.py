"""
Configuration management for Spotify Voice Assistant.
Handles loading and validation of configuration from files and environment variables.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class AudioConfig:
    """Audio processing configuration."""
    energy_threshold: int = 200
    pause_threshold: float = 1.0
    phrase_time_limit: float = 7.0
    sample_rate: int = 44100
    max_retries: int = 3
    api_rate_limit_calls_per_minute: int = 45  # Google Speech API
    calibration_duration: float = 0.2


@dataclass
class SpotifyConfig:
    """Spotify integration configuration."""
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://127.0.0.1:8080/callback"
    api_rate_limit_calls_per_second: int = 6
    device_poll_timeout: float = 3.0
    max_device_retries: int = 10


@dataclass
class NotificationConfig:
    """Notification system configuration."""
    enabled: bool = True
    default_timeout: int = 5000
    default_icon: str = "audio-headphones"
    default_urgency: str = "normal"


@dataclass
class AssistantConfig:
    """Main assistant configuration."""
    wake_word: str = "jarvis"
    log_level: str = "INFO"
    cache_dir: str = "../cache"
    log_dir: str = "../logs" 
    calibration_dir: str = "../calibration"
    audio: Optional[AudioConfig] = None
    spotify: Optional[SpotifyConfig] = None
    notifications: Optional[NotificationConfig] = None

    def __post_init__(self):
        """Initialize nested config objects."""
        if self.audio is None:
            self.audio = AudioConfig()
        if self.spotify is None:
            self.spotify = SpotifyConfig()
        if self.notifications is None:
            self.notifications = NotificationConfig()


class ConfigManager:
    """Manages application configuration from multiple sources."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_file()
        self.config = AssistantConfig()
        self.logger = logging.getLogger(__name__)
    
    def _get_default_config_file(self) -> str:
        """Get the default configuration file path."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_dir, 'config', 'config.json')
    
    def load_config(self) -> AssistantConfig:
        """Load configuration from file and environment variables."""
        # First load from file if it exists
        if os.path.exists(self.config_file):
            self._load_from_file()
        else:
            self.logger.info(f"Config file not found: {self.config_file}, using defaults")
        
        # Override with environment variables
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
        
        return self.config
    
    def _load_from_file(self) -> None:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update configuration with file values
            self._update_config_from_dict(config_data)
            self.logger.info(f"Configuration loaded from {self.config_file}")
            
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Failed to load config from {self.config_file}: {e}")
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            # Assistant config
            'WAKE_WORD': ('wake_word', str),
            'LOG_LEVEL': ('log_level', str),
            'CACHE_DIR': ('cache_dir', str),
            'LOG_DIR': ('log_dir', str),
            
            # Spotify config
            'SPOTIFY_CLIENT_ID': ('spotify.client_id', str),
            'SPOTIFY_CLIENT_SECRET': ('spotify.client_secret', str),
            'SPOTIFY_REDIRECT_URI': ('spotify.redirect_uri', str),
            
            # Audio config
            'AUDIO_ENERGY_THRESHOLD': ('audio.energy_threshold', int),
            'AUDIO_PAUSE_THRESHOLD': ('audio.pause_threshold', float),
            'AUDIO_PHRASE_TIME_LIMIT': ('audio.phrase_time_limit', float),
            'AUDIO_SAMPLE_RATE': ('audio.sample_rate', int),
            
            # Notification config
            'NOTIFICATIONS_ENABLED': ('notifications.enabled', bool),
            'NOTIFICATIONS_TIMEOUT': ('notifications.default_timeout', int),
        }
        
        for env_var, (config_path, var_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    # Convert to appropriate type
                    if var_type == bool:
                        converted_value = value.lower() in ('true', '1', 'yes', 'on')
                    elif var_type == int:
                        converted_value = int(value)
                    elif var_type == float:
                        converted_value = float(value)
                    else:
                        converted_value = value
                    
                    # Set the configuration value
                    self._set_config_value(config_path, converted_value)
                    self.logger.debug(f"Set {config_path} from environment: {converted_value}")
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Invalid environment value for {env_var}: {value} ({e})")
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        if 'wake_word' in config_data:
            self.config.wake_word = config_data['wake_word']
        if 'log_level' in config_data:
            self.config.log_level = config_data['log_level']
        if 'cache_dir' in config_data:
            self.config.cache_dir = config_data['cache_dir']
        if 'log_dir' in config_data:
            self.config.log_dir = config_data['log_dir']
        if 'calibration_dir' in config_data:
            self.config.calibration_dir = config_data['calibration_dir']
        
        # Update nested configs
        if 'audio' in config_data:
            audio_data = config_data['audio']
            for key, value in audio_data.items():
                if hasattr(self.config.audio, key):
                    setattr(self.config.audio, key, value)
        
        if 'spotify' in config_data:
            spotify_data = config_data['spotify']
            for key, value in spotify_data.items():
                if hasattr(self.config.spotify, key):
                    setattr(self.config.spotify, key, value)
        
        if 'notifications' in config_data:
            notif_data = config_data['notifications']
            for key, value in notif_data.items():
                if hasattr(self.config.notifications, key):
                    setattr(self.config.notifications, key, value)
    
    def _set_config_value(self, path: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        parts = path.split('.')
        obj = self.config
        
        # Navigate to the parent object
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        # Set the final value
        setattr(obj, parts[-1], value)
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        errors = []
        
        # Ensure nested configs are initialized
        if self.config.spotify is None:
            self.config.spotify = SpotifyConfig()
        if self.config.audio is None:
            self.config.audio = AudioConfig()
        
        # Validate required Spotify credentials
        if not self.config.spotify.client_id.strip():
            errors.append("Spotify Client ID is required")
        if not self.config.spotify.client_secret.strip():
            errors.append("Spotify Client Secret is required")
        
        # Validate audio settings
        if self.config.audio.energy_threshold < 50 or self.config.audio.energy_threshold > 5000:
            errors.append(f"Invalid energy_threshold: {self.config.audio.energy_threshold} (must be 50-5000)")
        
        if self.config.audio.pause_threshold < 0.1 or self.config.audio.pause_threshold > 5.0:
            errors.append(f"Invalid pause_threshold: {self.config.audio.pause_threshold} (must be 0.1-5.0)")
        
        # Validate wake word
        if len(self.config.wake_word.strip()) < 2:
            errors.append("Wake word must be at least 2 characters")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """Save current configuration to file."""
        file_path = config_file or self.config_file
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Convert to dictionary
        config_dict = asdict(self.config)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            self.logger.info(f"Configuration saved to {file_path}")
            
        except IOError as e:
            self.logger.error(f"Failed to save config to {file_path}: {e}")
            raise
    
    def get_absolute_path(self, relative_path: str) -> str:
        """Convert relative path to absolute path from app directory."""
        if os.path.isabs(relative_path):
            return relative_path
        
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_dir, relative_path.lstrip('../'))
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.config.cache_dir,
            self.config.log_dir,
            self.config.calibration_dir
        ]
        
        for rel_dir in directories:
            abs_dir = self.get_absolute_path(rel_dir)
            os.makedirs(abs_dir, mode=0o755, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {abs_dir}")


def create_default_config_file() -> None:
    """Create a default configuration file."""
    config_manager = ConfigManager()
    
    # Create with default values
    default_config = AssistantConfig()
    config_manager.config = default_config
    
    # Save to file
    config_manager.save_config()
    print(f"Default configuration file created: {config_manager.config_file}")
    print("Edit this file to customize your settings.")


if __name__ == '__main__':
    # Command-line tool to create default config
    create_default_config_file()