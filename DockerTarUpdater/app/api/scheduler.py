from flask import Blueprint
from app.utils.response import success, error
from app.core.scheduler import start_scheduler, stop_scheduler, get_scheduler_status, sync_jobs

bp = Blueprint('scheduler', __name__, url_prefix='/api/scheduler')

@bp.route('/status', methods=['GET'])
def scheduler_status():
    status = get_scheduler_status()
    return success(status)

@bp.route('/start', methods=['POST'])
def scheduler_start():
    try:
        start_scheduler()
        return success({'running': True}, 'Scheduler started')
    except Exception as e:
        return error(f'Failed to start scheduler: {str(e)}')

@bp.route('/stop', methods=['POST'])
def scheduler_stop():
    try:
        stop_scheduler()
        return success({'running': False}, 'Scheduler stopped')
    except Exception as e:
        return error(f'Failed to stop scheduler: {str(e)}')

@bp.route('/sync', methods=['POST'])
def scheduler_sync():
    try:
        sync_jobs()
        status = get_scheduler_status()
        return success(status, 'Scheduler synced')
    except Exception as e:
        return error(f'Failed to sync scheduler: {str(e)}')
