import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, socketio=None):
        self.socketio = socketio
        from app.models.notification import WebNotification, Notification
        self.WebNotification = WebNotification
        self.Notification = Notification

    def notify(self, notif_type: str, title: str, message: str, target_name=None):
        try:
            self._save_web_notification(notif_type, title, message)

            if self.socketio:
                self._broadcast_websocket(notif_type, title, message, target_name)

            self._send_other_notifications(notif_type, title, message)

        except Exception as e:
            logger.error(f"Notification error: {e}")

    def _save_web_notification(self, notif_type: str, title: str, message: str):
        try:
            self.WebNotification.create(notif_type, title, message)
        except Exception as e:
            logger.error(f"Failed to save web notification: {e}")

    def _broadcast_websocket(self, notif_type: str, title: str, message: str, target_name=None):
        try:
            payload = {
                'type': notif_type,
                'title': title,
                'message': message,
                'target': target_name,
                'timestamp': datetime.now().isoformat()
            }
            self.socketio.emit('notification', payload)
        except Exception as e:
            logger.error(f"WebSocket broadcast error: {e}")

    def _send_other_notifications(self, notif_type: str, title: str, message: str):
        try:
            enabled_notifs = self.Notification.get_enabled()
            for notif in enabled_notifs:
                if notif['type'] == 'web':
                    continue
                elif notif['type'] == 'dingtalk':
                    self._send_dingtalk(notif, title, message)
                elif notif['type'] == 'feishu':
                    self._send_feishu(notif, title, message)
                elif notif['type'] == 'email':
                    self._send_email(notif, title, message)
        except Exception as e:
            logger.error(f"Failed to send other notifications: {e}")

    def _send_dingtalk(self, notif: dict, title: str, message: str):
        try:
            import requests
            config = notif.get('config', {})
            webhook = config.get('webhook')
            if not webhook:
                return

            data = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': title,
                    'text': f"**{title}**\n\n{message}\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            requests.post(webhook, json=data, timeout=10)
        except Exception as e:
            logger.error(f"DingTalk notification failed: {e}")

    def _send_feishu(self, notif: dict, title: str, message: str):
        pass

    def _send_email(self, notif: dict, title: str, message: str):
        pass

    def notify_update_start(self, target_name: str, new_image_tag: str):
        self.notify('info', f'Starting update for {target_name}',
                   f'Downloading and loading {new_image_tag}', target_name)

    def notify_update_success(self, target_name: str, old_image: str, new_image: str):
        self.notify('success', f'{target_name} updated successfully',
                   f'{old_image} → {new_image}', target_name)

    def notify_update_failed(self, target_name: str, error: str):
        self.notify('error', f'{target_name} update failed',
                   f'Error: {error}', target_name)
