from flask import Blueprint, request
from app.utils.response import success, error
from app.models.task import TaskLog
from app.models.target import Target
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@bp.route('', methods=['GET'])
def get_tasks():
    limit = request.args.get('limit', 50, type=int)
    logger.debug(f"[API] GET /api/tasks - 获取任务日志，限制: {limit}")
    tasks = TaskLog.get_all(limit=limit)
    logger.debug(f"[API] 返回 {len(tasks)} 条任务日志")
    return success(tasks)

@bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    logger.debug(f"[API] GET /api/tasks/{task_id} - 获取单个任务")
    task = TaskLog.get_by_id(task_id)
    if not task:
        logger.warning(f"[API] 任务 {task_id} 未找到")
        return error('任务不存在', 404)
    return success(task)

@bp.route('/latest', methods=['GET'])
def get_latest_tasks():
    logger.debug("[API] GET /api/tasks/latest - 获取最新任务")
    tasks = TaskLog.get_latest()
    logger.debug(f"[API] 返回 {len(tasks)} 条最新任务")
    return success(tasks)

@bp.route('/target/<int:target_id>', methods=['GET'])
def get_tasks_by_target(target_id):
    limit = request.args.get('limit', 20, type=int)
    logger.debug(f"[API] GET /api/tasks/target/{target_id} - 获取目标的任务，限制: {limit}")
    tasks = TaskLog.get_by_target(target_id, limit=limit)
    logger.debug(f"[API] 返回 {len(tasks)} 条任务")
    return success(tasks)

@bp.route('/stats', methods=['GET'])
def get_stats():
    logger.debug("[API] GET /api/tasks/stats - 获取统计信息")
    task_stats = TaskLog.get_stats()
    target_stats = {
        'total': len(Target.get_all()),
        'enabled': len(Target.get_enabled())
    }
    logger.debug(f"[API] 任务统计: {task_stats}, 目标统计: {target_stats}")
    return success({
        'tasks': task_stats,
        'targets': target_stats
    })
