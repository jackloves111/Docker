from flask import Blueprint, request
from app.utils.response import success, error
from app.models.notification import Notification, WebNotification
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@bp.route('', methods=['GET'])
def get_notifications():
    logger.debug("[API] GET /api/notifications - 获取所有通知配置")
    notifications = Notification.get_all()
    logger.debug(f"[API] 返回 {len(notifications)} 个通知配置")
    return success(notifications)

@bp.route('', methods=['POST'])
def create_notification():
    logger.info("[API] POST /api/notifications - 创建通知配置")
    data = request.get_json()
    if not data:
        logger.warning("[API] 创建通知失败: 无效的请求数据")
        return error('无效的请求数据')

    name = data.get('name')
    notif_type = data.get('type', 'web')
    config = data.get('config', {})
    enabled = data.get('enabled', 1)

    logger.debug(f"[API] 通知配置: name={name}, type={notif_type}")

    if not name:
        logger.warning("[API] 创建通知失败: 名称不能为空")
        return error('名称不能为空')

    try:
        notif_id = Notification.create(name, notif_type, config, enabled)
        logger.info(f"[API] 通知配置创建成功: ID={notif_id}, 名称={name}")
        return success({'id': notif_id}, '通知配置创建成功')
    except Exception as e:
        logger.error(f"[API] 创建通知异常: {e}")
        return error(f'创建通知失败: {str(e)}')

@bp.route('/<int:notif_id>', methods=['PUT'])
def update_notification(notif_id):
    logger.info(f"[API] PUT /api/notifications/{notif_id} - 更新通知配置")
    data = request.get_json()
    if not data:
        logger.warning(f"[API] 更新通知 {notif_id} 失败: 无效的请求数据")
        return error('无效的请求数据')

    try:
        Notification.update(notif_id, **data)
        logger.info(f"[API] 通知配置 {notif_id} 更新成功")
        return success(message='通知配置更新成功')
    except Exception as e:
        logger.error(f"[API] 更新通知 {notif_id} 异常: {e}")
        return error(f'更新通知失败: {str(e)}')

@bp.route('/<int:notif_id>', methods=['DELETE'])
def delete_notification(notif_id):
    logger.info(f"[API] DELETE /api/notifications/{notif_id} - 删除通知配置")
    try:
        Notification.delete(notif_id)
        logger.info(f"[API] 通知配置 {notif_id} 删除成功")
        return success(message='通知配置删除成功')
    except Exception as e:
        logger.error(f"[API] 删除通知 {notif_id} 异常: {e}")
        return error(f'删除通知失败: {str(e)}')

@bp.route('/web/list', methods=['GET'])
def get_web_notifications():
    logger.debug("[API] GET /api/notifications/web/list - 获取 Web 通知列表")
    notifications = WebNotification.get_all(limit=50)
    logger.debug(f"[API] 返回 {len(notifications)} 条 Web 通知")
    return success(notifications)

@bp.route('/web/unread', methods=['GET'])
def get_unread_notifications():
    logger.debug("[API] GET /api/notifications/web/unread - 获取未读通知")
    notifications = WebNotification.get_unread()
    logger.debug(f"[API] 返回 {len(notifications)} 条未读通知")
    return success(notifications)

@bp.route('/web/unread/count', methods=['GET'])
def get_unread_count():
    logger.debug("[API] GET /api/notifications/web/unread/count - 获取未读数量")
    count = WebNotification.get_unread_count()
    logger.debug(f"[API] 未读通知数量: {count}")
    return success({'count': count})

@bp.route('/web/read', methods=['PUT'])
def mark_notifications_read():
    logger.info("[API] PUT /api/notifications/web/read - 标记通知已读")
    data = request.get_json() or {}
    notif_ids = data.get('ids')
    WebNotification.mark_read(notif_ids if notif_ids else None)
    logger.info("[API] 通知已标记为已读")
    return success(message='通知已标记为已读')
