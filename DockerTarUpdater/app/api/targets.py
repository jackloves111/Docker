from flask import Blueprint, request
from app.utils.response import success, error
from app.models.target import Target
from app.models.task import TaskLog
from app.utils.docker_client import get_container_info, list_containers
from app.core.scheduler import add_job, remove_job
from app.core.engine import trigger_upgrade
import threading

bp = Blueprint('targets', __name__, url_prefix='/api/targets')

@bp.route('', methods=['GET'])
def get_targets():
    targets = Target.get_all()
    return success(targets)

@bp.route('/<int:target_id>', methods=['GET'])
def get_target(target_id):
    target = Target.get_by_id(target_id)
    if not target:
        return error('Target not found', 404)
    return success(target)

@bp.route('', methods=['POST'])
def create_target():
    data = request.get_json()
    if not data:
        return error('Invalid request data')

    name = data.get('name')
    tar_url = data.get('tar_url')
    image_tag = data.get('image_tag')

    if not all([name, tar_url, image_tag]):
        return error('Missing required fields')

    try:
        target_id = Target.create(
            name=name,
            tar_url=tar_url,
            image_tag=image_tag,
            schedule_type=data.get('schedule_type', 'interval'),
            schedule_value=data.get('schedule_value', '360')
        )

        target = Target.get_by_id(target_id)
        if target.get('enabled'):
            add_job(target)

        return success({'id': target_id}, 'Target created')
    except Exception as e:
        return error(f'Failed to create target: {str(e)}')

@bp.route('/<int:target_id>', methods=['PUT'])
def update_target(target_id):
    data = request.get_json()
    if not data:
        return error('Invalid request data')

    target = Target.get_by_id(target_id)
    if not target:
        return error('Target not found', 404)

    allowed_fields = ['name', 'tar_url', 'image_tag', 'schedule_type', 'schedule_value', 'enabled']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    try:
        Target.update(target_id, **update_data)

        updated_target = Target.get_by_id(target_id)
        if updated_target.get('enabled'):
            add_job(updated_target)
        else:
            remove_job(target_id)

        return success(updated_target, 'Target updated')
    except Exception as e:
        return error(f'Failed to update target: {str(e)}')

@bp.route('/<int:target_id>', methods=['DELETE'])
def delete_target(target_id):
    target = Target.get_by_id(target_id)
    if not target:
        return error('Target not found', 404)

    try:
        remove_job(target_id)
        Target.delete(target_id)
        return success(message='Target deleted')
    except Exception as e:
        return error(f'Failed to delete target: {str(e)}')

@bp.route('/<int:target_id>/trigger', methods=['POST'])
def trigger_upgrade_api(target_id):
    target = Target.get_by_id(target_id)
    if not target:
        return error('Target not found', 404)

    thread = threading.Thread(target=trigger_upgrade, args=(target_id,))
    thread.daemon = True
    thread.start()

    return success(message='Upgrade triggered')

@bp.route('/<int:target_id>/info', methods=['GET'])
def get_target_info(target_id):
    target = Target.get_by_id(target_id)
    if not target:
        return error('Target not found', 404)

    try:
        container_info = get_container_info(target['name'])
        if container_info:
            return success(container_info)
        else:
            return success({'status': 'not_found'}, 'Container not found')
    except Exception as e:
        return error(f'Failed to get container info: {str(e)}')

@bp.route('/containers', methods=['GET'])
def get_docker_containers():
    try:
        containers = list_containers()
        return success(containers)
    except Exception as e:
        return error(f'Failed to list containers: {str(e)}')
