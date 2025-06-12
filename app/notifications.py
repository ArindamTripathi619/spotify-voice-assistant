import subprocess
import logging

class NotificationManager:
    def __init__(self):
        self.notifications_enabled = False
        self.setup_notifications()

    def setup_notifications(self):
        try:
            result = subprocess.run(['which', 'notify-send'], capture_output=True, text=True)
            if result.returncode == 0:
                self.notifications_enabled = True
                logging.info("Desktop notifications enabled.")
            else:
                self.notifications_enabled = False
                logging.warning("notify-send not found, notifications disabled.", exc_info=True)
        except Exception as e:
            self.notifications_enabled = False
            logging.warning(f"Notification setup failed: {e}", exc_info=True)

    def send_notification(self, title, message, icon="audio-headphones", urgency="normal", timeout=5000):
        if not self.notifications_enabled:
            return
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
            logging.warning(f"Notification failed: {e}", exc_info=True)
