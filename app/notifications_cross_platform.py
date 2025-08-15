import logging
from .platform_utils import is_windows, is_linux, is_mac

class CrossPlatformNotificationManager:
    def __init__(self):
        self.notifications_enabled = False
        self.notification_backend = None
        self.setup_notifications()

    def setup_notifications(self):
        """Setup platform-specific notification system."""
        try:
            if is_windows():
                self._setup_windows_notifications()
            elif is_linux():
                self._setup_linux_notifications()
            elif is_mac():
                self._setup_mac_notifications()
            else:
                logging.warning("Unsupported platform for notifications")
                self.notifications_enabled = False
        except Exception as e:
            logging.warning(f"Notification setup failed: {e}")
            self.notifications_enabled = False

    def _setup_windows_notifications(self):
        """Setup Windows toast notifications."""
        try:
            # Try win10toast first (lightweight)
            from win10toast import ToastNotifier
            self.notification_backend = 'win10toast'
            self.toaster = ToastNotifier()
            self.notifications_enabled = True
            logging.info("Windows toast notifications enabled (win10toast)")
        except ImportError:
            try:
                # Fallback to plyer (cross-platform)
                from plyer import notification
                self.notification_backend = 'plyer'
                self.plyer_notification = notification
                self.notifications_enabled = True
                logging.info("Cross-platform notifications enabled (plyer)")
            except ImportError:
                logging.warning("No notification libraries available. Install win10toast or plyer")
                self.notifications_enabled = False

    def _setup_linux_notifications(self):
        """Setup Linux notify-send notifications."""
        import subprocess
        try:
            result = subprocess.run(['which', 'notify-send'], capture_output=True, text=True)
            if result.returncode == 0:
                self.notification_backend = 'notify-send'
                self.notifications_enabled = True
                logging.info("Linux desktop notifications enabled (notify-send)")
            else:
                # Fallback to plyer
                try:
                    from plyer import notification
                    self.notification_backend = 'plyer'
                    self.plyer_notification = notification
                    self.notifications_enabled = True
                    logging.info("Cross-platform notifications enabled (plyer)")
                except ImportError:
                    logging.warning("notify-send not found and plyer not available")
                    self.notifications_enabled = False
        except Exception as e:
            logging.warning(f"Linux notification setup failed: {e}")
            self.notifications_enabled = False

    def _setup_mac_notifications(self):
        """Setup macOS notifications."""
        try:
            # Try plyer first
            from plyer import notification
            self.notification_backend = 'plyer'
            self.plyer_notification = notification
            self.notifications_enabled = True
            logging.info("macOS notifications enabled (plyer)")
        except ImportError:
            # Fallback to osascript
            import subprocess
            try:
                subprocess.run(['which', 'osascript'], capture_output=True, check=True)
                self.notification_backend = 'osascript'
                self.notifications_enabled = True
                logging.info("macOS notifications enabled (osascript)")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logging.warning("No notification system available on macOS")
                self.notifications_enabled = False

    def send_notification(self, title, message, icon="audio-headphones", urgency="normal", timeout=5000):
        """Send cross-platform notification."""
        if not self.notifications_enabled:
            return

        try:
            if self.notification_backend == 'win10toast':
                self._send_windows_toast(title, message, timeout)
            elif self.notification_backend == 'plyer':
                self._send_plyer_notification(title, message, timeout)
            elif self.notification_backend == 'notify-send':
                self._send_linux_notification(title, message, icon, urgency, timeout)
            elif self.notification_backend == 'osascript':
                self._send_mac_notification(title, message)
        except Exception as e:
            logging.warning(f"Failed to send notification: {e}")

    def _send_windows_toast(self, title, message, timeout):
        """Send Windows toast notification."""
        try:
            # Convert timeout from milliseconds to seconds for win10toast
            duration = max(1, timeout // 1000)
            self.toaster.show_toast(
                title=title,
                msg=message,
                duration=duration,
                threaded=True
            )
        except Exception as e:
            logging.warning(f"Windows toast notification failed: {e}")

    def _send_plyer_notification(self, title, message, timeout):
        """Send notification using plyer (cross-platform)."""
        try:
            self.plyer_notification.notify(
                title=title,
                message=message,
                timeout=timeout // 1000,  # plyer expects seconds
                app_name="Enhanced Spotify Assistant"
            )
        except Exception as e:
            logging.warning(f"Plyer notification failed: {e}")

    def _send_linux_notification(self, title, message, icon, urgency, timeout):
        """Send Linux notification using notify-send."""
        import subprocess
        try:
            cmd = [
                'notify-send',
                '--app-name=Enhanced Spotify Assistant',
                f'--icon={icon}',
                f'--urgency={urgency}',
                f'--expire-time={timeout}',
                '--category=music',
                title,
                message
            ]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logging.warning(f"Linux notification failed: {e}")

    def _send_mac_notification(self, title, message):
        """Send macOS notification using osascript."""
        import subprocess
        try:
            script = f'''
            display notification "{message}" with title "{title}" sound name "default"
            '''
            subprocess.run(['osascript', '-e', script], capture_output=True)
        except Exception as e:
            logging.warning(f"macOS notification failed: {e}")

# For backward compatibility, alias to the cross-platform version
NotificationManager = CrossPlatformNotificationManager
