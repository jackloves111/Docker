from flask import Blueprint
from app.utils.response import success, error
from app.core.scheduler import start_scheduler, stop_scheduler, get_scheduler_status, sync_jobs
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')

@bp.route('/status', methods=['GET'])
def scheduler_status():
    logger.debug("[API] GET /api/scheduler/status - 获取调度器状态")
    status = get_scheduler_status()
    logger.debug(f"[API] 调度器状态: {status}")
    return success(status)

@bp.route('/start', methods=['POST'])
def scheduler_start():
    logger.info("[API] POST /api/scheduler/start - 启动调度器")
    try:
        start_scheduler()
        logger.info("[API] 调度器启动成功")
        return success({'running': True}, '调度器已启动')
    except Exception as e:
        logger.error(f"[API] 启动调度器失败: {e}")
        return error(f'启动调度器失败: {str(e)}')

@bp.route('/stop', methods=['POST'])
def scheduler_stop():
    logger.info("[API] POST /api/scheduler/stop - 停止调度器")
    try:
        stop_scheduler()
        logger.info("[API] 调度器已停止")
        return success({'running': False}, '调度器已停止')
    except Exception as e:
        logger.error(f"[API] 停止调度器失败: {e}")
        return error(f'停止调度器失败: {str(e)}')

@bp.route('/sync', methods=['POST'])
def scheduler_sync():
    logger.info("[API] POST /api/scheduler/sync - 同步调度器任务")
    try:
        sync_jobs()
        status = get_scheduler_status()
        logger.info(f"[API] 调度器同步完成，状态: {status}")
        return success(status, '调度器已同步')
    except Exception as e:
        logger.error(f"[API] 同步调度器失败: {e}")
        return error(f'同步调度器失败: {str(e)}')
