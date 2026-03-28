from flask import Blueprint, request
from app.utils.response import success, error
from app.models.task import TaskLog
from app.models.target import Target

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@bp.route('', methods=['GET'])
def get_tasks():
    limit = request.args.get('limit', 50, type=int)
    tasks = TaskLog.get_all(limit=limit)
    return success(tasks)

@bp.route('/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = TaskLog.get_by_id(task_id)
    if not task:
        return error('Task not found', 404)
    return success(task)

@bp.route('/latest', methods=['GET'])
def get_latest_tasks():
    tasks = TaskLog.get_latest()
    return success(tasks)

@bp.route('/target/<int:target_id>', methods=['GET'])
def get_tasks_by_target(target_id):
    limit = request.args.get('limit', 20, type=int)
    tasks = TaskLog.get_by_target(target_id, limit=limit)
    return success(tasks)

@bp.route('/stats', methods=['GET'])
def get_stats():
    task_stats = TaskLog.get_stats()
    target_stats = {
        'total': len(Target.get_all()),
        'enabled': len(Target.get_enabled())
    }
    return success({
        'tasks': task_stats,
        'targets': target_stats
    })
