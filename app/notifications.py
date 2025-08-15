# Cross-platform notification manager
# Automatically detects platform and uses appropriate notification system
from .notifications_cross_platform import CrossPlatformNotificationManager

# For backward compatibility, alias to the cross-platform version
NotificationManager = CrossPlatformNotificationManager
