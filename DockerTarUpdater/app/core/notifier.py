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
        logger.debug("[通知器] 初始化通知器")

    def notify(self, notif_type: str, title: str, message: str, target_name=None):
        logger.info(f"[通知器] 发送通知 - 类型: {notif_type}, 标题: {title}, 目标: {target_name}")
        try:
            self._save_web_notification(notif_type, title, message)

            if self.socketio:
                self._broadcast_websocket(notif_type, title, message, target_name)

            self._send_other_notifications(notif_type, title, message)

        except Exception as e:
            logger.error(f"[通知器] 通知发送异常: {e}")

    def _save_web_notification(self, notif_type: str, title: str, message: str):
        try:
            self.WebNotification.create(notif_type, title, message)
            logger.debug("[通知器] Web 通知已保存")
        except Exception as e:
            logger.error(f"[通知器] 保存 Web 通知失败: {e}")

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
            logger.debug(f"[通知器] WebSocket 广播已发送: {payload}")
        except Exception as e:
            logger.error(f"[通知器] WebSocket 广播失败: {e}")

    def _send_other_notifications(self, notif_type: str, title: str, message: str):
        try:
            enabled_notifs = self.Notification.get_enabled()
            logger.debug(f"[通知器] 查找启用的通知渠道，共 {len(enabled_notifs)} 个")
            for notif in enabled_notifs:
                if notif['type'] == 'web':
                    continue
                elif notif['type'] == 'dingtalk':
                    logger.debug(f"[通知器] 发送钉钉通知: {notif.get('name')}")
                    self._send_dingtalk(notif, title, message)
                elif notif['type'] == 'feishu':
                    logger.debug(f"[通知器] 发送飞书通知: {notif.get('name')}")
                    self._send_feishu(notif, title, message)
                elif notif['type'] == 'email':
                    logger.debug(f"[通知器] 发送邮件通知: {notif.get('name')}")
                    self._send_email(notif, title, message)
        except Exception as e:
            logger.error(f"[通知器] 发送其他通知失败: {e}")

    def _send_dingtalk(self, notif: dict, title: str, message: str):
        try:
            import requests
            config = notif.get('config', {})
            webhook = config.get('webhook')
            if not webhook:
                logger.warning("[通知器] 钉钉 Webhook 未配置")
                return

            data = {
                'msgtype': 'markdown',
                'markdown': {
                    'title': title,
                    'text': f"**{title}**\n\n{message}\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            response = requests.post(webhook, json=data, timeout=10)
            logger.info(f"[通知器] 钉钉通知发送结果: {response.status_code}")
        except Exception as e:
            logger.error(f"[通知器] 钉钉通知发送失败: {e}")

    def _send_feishu(self, notif: dict, title: str, message: str):
        logger.debug("[通知器] 飞书通知暂未实现")
        pass

    def _send_email(self, notif: dict, title: str, message: str):
        logger.debug("[通知器] 邮件通知暂未实现")
        pass

    def notify_update_start(self, target_name: str, new_image_tag: str):
        title = f'开始更新 {target_name}'
        message = f'正在下载并加载镜像 {new_image_tag}'
        logger.info(f"[通知器] 通知升级开始: {title}")
        self.notify('info', title, message, target_name)

    def notify_update_success(self, target_name: str, old_image: str, new_image: str):
        title = f'{target_name} 更新成功'
        message = f'{old_image} → {new_image}'
        logger.info(f"[通知器] 通知升级成功: {title} - {message}")
        self.notify('success', title, message, target_name)

    def notify_update_failed(self, target_name: str, error: str):
        title = f'{target_name} 更新失败'
        message = f'错误: {error}'
        logger.info(f"[通知器] 通知升级失败: {title} - {message}")
        self.notify('error', title, message, target_name)
