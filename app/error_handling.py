"""
Comprehensive Error Handling Module for Spotify Voice Assistant.
Provides standardized error handling, logging, and recovery mechanisms.
"""

import logging
import functools
import traceback
from typing import Any, Callable, Optional, Type, Union
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    API_RATE_LIMIT = "api_rate_limit"
    AUDIO = "audio"
    FILE_SYSTEM = "file_system"
    SPOTIFY = "spotify"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


class SpotifyVoiceAssistantError(Exception):
    """Base exception for Spotify Voice Assistant."""
    
    def __init__(self, message: str, category: ErrorCategory, severity: ErrorSeverity, 
                 cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.cause = cause
        self.timestamp = None
        
    def __str__(self):
        return f"[{self.category.value.upper()}] {self.message}"


class NetworkError(SpotifyVoiceAssistantError):
    """Network-related errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.NETWORK, severity, cause)


class AuthenticationError(SpotifyVoiceAssistantError):
    """Authentication-related errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.CRITICAL, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.AUTHENTICATION, severity, cause)


class RateLimitError(SpotifyVoiceAssistantError):
    """API rate limit errors."""
    def __init__(self, message: str, retry_after: int = 60, severity: ErrorSeverity = ErrorSeverity.MEDIUM, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.API_RATE_LIMIT, severity, cause)
        self.retry_after = retry_after


class AudioError(SpotifyVoiceAssistantError):
    """Audio system errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.AUDIO, severity, cause)


class FileSystemError(SpotifyVoiceAssistantError):
    """File system errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.FILE_SYSTEM, severity, cause)


class SpotifyError(SpotifyVoiceAssistantError):
    """Spotify-specific errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.HIGH, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.SPOTIFY, severity, cause)


class ConfigurationError(SpotifyVoiceAssistantError):
    """Configuration errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.CRITICAL, cause: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.CONFIGURATION, severity, cause)


class ErrorHandler:
    """Centralized error handling and logging."""
    
    def __init__(self, logger: Optional[logging.Logger] = None, notifier=None):
        self.logger = logger or logging.getLogger(__name__)
        self.notifier = notifier
        self.error_counts = {}
        self.max_retries = 3
    
    def handle_error(self, error: Exception, context: str = "", 
                    notify_user: bool = True, reraise: bool = False) -> None:
        """Handle an error with appropriate logging and user notification."""
        
        # Convert to standardized error if needed
        if isinstance(error, SpotifyVoiceAssistantError):
            standardized_error = error
        else:
            standardized_error = self._standardize_error(error, context)
        
        # Log the error
        self._log_error(standardized_error, context)
        
        # Track error frequency
        error_key = f"{standardized_error.category.value}:{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Notify user if requested and notifier is available
        if notify_user and self.notifier:
            self._notify_user(standardized_error, context)
        
        # Re-raise if requested
        if reraise:
            raise standardized_error from error
    
    def _standardize_error(self, error: Exception, context: str) -> SpotifyVoiceAssistantError:
        """Convert generic exceptions to standardized errors."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Network-related errors
        if any(term in error_type.lower() or term in error_msg.lower() 
               for term in ['connection', 'timeout', 'network', 'dns', 'unreachable']):
            return NetworkError(f"Network error in {context}: {error_msg}", cause=error)
        
        # Authentication errors
        elif any(term in error_type.lower() or term in error_msg.lower()
                for term in ['auth', 'credential', 'token', 'unauthorized', '401', '403']):
            return AuthenticationError(f"Authentication error in {context}: {error_msg}", cause=error)
        
        # Rate limit errors
        elif any(term in error_type.lower() or term in error_msg.lower()
                for term in ['rate limit', '429', 'quota', 'throttle']):
            return RateLimitError(f"Rate limit exceeded in {context}: {error_msg}", cause=error)
        
        # Audio errors
        elif any(term in error_type.lower() or term in error_msg.lower()
                for term in ['audio', 'microphone', 'speech', 'pyaudio', 'tts']):
            return AudioError(f"Audio error in {context}: {error_msg}", cause=error)
        
        # File system errors
        elif any(term in error_type.lower() or term in error_msg.lower()
                for term in ['file', 'directory', 'permission', 'disk', 'path']):
            return FileSystemError(f"File system error in {context}: {error_msg}", cause=error)
        
        # Spotify API errors
        elif any(term in error_type.lower() or term in error_msg.lower()
                for term in ['spotify', 'device', 'playback', 'track']):
            return SpotifyError(f"Spotify error in {context}: {error_msg}", cause=error)
        
        # Default to system error
        else:
            return SpotifyVoiceAssistantError(
                f"System error in {context}: {error_msg}",
                ErrorCategory.SYSTEM,
                ErrorSeverity.HIGH,
                cause=error
            )
    
    def _log_error(self, error: SpotifyVoiceAssistantError, context: str) -> None:
        """Log error with appropriate level based on severity."""
        log_message = f"{context}: {error}"
        
        if error.cause:
            log_message += f" (caused by: {error.cause})"
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=error.cause)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=error.cause)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _notify_user(self, error: SpotifyVoiceAssistantError, context: str) -> None:
        """Notify user about the error through the notification system."""
        try:
            # Determine notification icon and urgency based on error
            icon_map = {
                ErrorCategory.NETWORK: "network-error",
                ErrorCategory.AUTHENTICATION: "dialog-password",
                ErrorCategory.API_RATE_LIMIT: "dialog-warning",
                ErrorCategory.AUDIO: "audio-card",
                ErrorCategory.FILE_SYSTEM: "folder-open",
                ErrorCategory.SPOTIFY: "multimedia-player",
                ErrorCategory.CONFIGURATION: "preferences-system",
                ErrorCategory.SYSTEM: "computer"
            }
            
            urgency_map = {
                ErrorSeverity.CRITICAL: "critical",
                ErrorSeverity.HIGH: "normal",
                ErrorSeverity.MEDIUM: "low",
                ErrorSeverity.LOW: "low"
            }
            
            timeout_map = {
                ErrorSeverity.CRITICAL: 0,  # Don't auto-close critical errors
                ErrorSeverity.HIGH: 8000,
                ErrorSeverity.MEDIUM: 5000,
                ErrorSeverity.LOW: 3000
            }
            
            # Create user-friendly error message
            user_message = self._create_user_friendly_message(error)
            
            self.notifier.send_notification(
                title=f"❌ {error.category.value.replace('_', ' ').title()} Error",
                message=user_message,
                icon=icon_map.get(error.category, "dialog-error"),
                urgency=urgency_map.get(error.severity, "normal"),
                timeout=timeout_map.get(error.severity, 5000)
            )
        except Exception as e:
            self.logger.warning(f"Failed to send error notification: {e}")
    
    def _create_user_friendly_message(self, error: SpotifyVoiceAssistantError) -> str:
        """Create user-friendly error messages with helpful suggestions."""
        
        error_msg = error.message
        
        # Add helpful suggestions based on error type
        if error.category == ErrorCategory.NETWORK:
            error_msg += "\n\nSuggestions:\n• Check internet connection\n• Try again in a moment"
        
        elif error.category == ErrorCategory.AUTHENTICATION:
            error_msg += "\n\nSuggestions:\n• Check Spotify credentials\n• Verify app permissions"
        
        elif error.category == ErrorCategory.API_RATE_LIMIT:
            if isinstance(error, RateLimitError):
                error_msg += f"\n\nWill retry in {error.retry_after} seconds"
            else:
                error_msg += "\n\nPlease wait a moment before trying again"
        
        elif error.category == ErrorCategory.AUDIO:
            error_msg += "\n\nSuggestions:\n• Check microphone permissions\n• Verify audio devices"
        
        elif error.category == ErrorCategory.SPOTIFY:
            error_msg += "\n\nSuggestions:\n• Make sure Spotify is running\n• Check device availability"
        
        # Truncate if too long
        if len(error_msg) > 250:
            error_msg = error_msg[:247] + "..."
        
        return error_msg
    
    def get_error_stats(self) -> dict:
        """Get error statistics for monitoring."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_breakdown": dict(self.error_counts),
            "most_common": max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None
        }


def error_handler(category: ErrorCategory = ErrorCategory.SYSTEM, 
                 severity: ErrorSeverity = ErrorSeverity.HIGH,
                 notify_user: bool = True,
                 reraise: bool = False,
                 fallback_value: Any = None):
    """Decorator for automatic error handling."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get error handler from instance if available
                error_mgr = None
                if args and hasattr(args[0], 'error_handler'):
                    error_mgr = args[0].error_handler
                elif args and hasattr(args[0], '_error_handler'):
                    error_mgr = args[0]._error_handler
                else:
                    # Create a basic error handler
                    error_mgr = ErrorHandler()
                
                # Handle the error
                context = f"{func.__module__}.{func.__name__}"
                error_mgr.handle_error(e, context, notify_user, reraise)
                
                # Return fallback value if not re-raising
                if not reraise:
                    return fallback_value
                    
        return wrapper
    return decorator


def safe_call(func: Callable, *args, fallback=None, context: str = "", **kwargs):
    """Safely call a function with error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Safe call failed for {context or func.__name__}: {e}")
        return fallback