from flask import Blueprint, request
from app.utils.response import success, error
from app.models.notification import Notification, WebNotification

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@bp.route('', methods=['GET'])
def get_notifications():
    notifications = Notification.get_all()
    return success(notifications)

@bp.route('', methods=['POST'])
def create_notification():
    data = request.get_json()
    if not data:
        return error('Invalid request data')

    name = data.get('name')
    notif_type = data.get('type', 'web')
    config = data.get('config', {})
    enabled = data.get('enabled', 1)

    if not name:
        return error('Name is required')

    try:
        notif_id = Notification.create(name, notif_type, config, enabled)
        return success({'id': notif_id}, 'Notification created')
    except Exception as e:
        return error(f'Failed to create notification: {str(e)}')

@bp.route('/<int:notif_id>', methods=['PUT'])
def update_notification(notif_id):
    data = request.get_json()
    if not data:
        return error('Invalid request data')

    try:
        Notification.update(notif_id, **data)
        return success(message='Notification updated')
    except Exception as e:
        return error(f'Failed to update notification: {str(e)}')

@bp.route('/<int:notif_id>', methods=['DELETE'])
def delete_notification(notif_id):
    try:
        Notification.delete(notif_id)
        return success(message='Notification deleted')
    except Exception as e:
        return error(f'Failed to delete notification: {str(e)}')

@bp.route('/web/list', methods=['GET'])
def get_web_notifications():
    notifications = WebNotification.get_all(limit=50)
    return success(notifications)

@bp.route('/web/unread', methods=['GET'])
def get_unread_notifications():
    notifications = WebNotification.get_unread()
    return success(notifications)

@bp.route('/web/unread/count', methods=['GET'])
def get_unread_count():
    count = WebNotification.get_unread_count()
    return success({'count': count})

@bp.route('/web/read', methods=['PUT'])
def mark_notifications_read():
    data = request.get_json() or {}
    notif_ids = data.get('ids')
    WebNotification.mark_read(notif_ids if notif_ids else None)
    return success(message='Notifications marked as read')
