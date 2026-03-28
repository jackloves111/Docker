from flask import Blueprint, request
from app.utils.response import success, error
from app.models.target import Target
from app.models.task import TaskLog
from app.utils.docker_client import get_container_info, list_containers, get_containers_by_image
from app.core.scheduler import add_job, remove_job
from app.core.engine import trigger_upgrade
import threading
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('targets', __name__, url_prefix='/api/targets')

@bp.route('', methods=['GET'])
def get_targets():
    logger.debug("[API] GET /api/targets - 获取所有目标")
    targets = Target.get_all()
    logger.debug(f"[API] 返回 {len(targets)} 个目标")
    return success(targets)

@bp.route('/<int:target_id>', methods=['GET'])
def get_target(target_id):
    logger.debug(f"[API] GET /api/targets/{target_id} - 获取单个目标")
    target = Target.get_by_id(target_id)
    if not target:
        logger.warning(f"[API] 目标 {target_id} 未找到")
        return error('目标不存在', 404)
    return success(target)

@bp.route('', methods=['POST'])
def create_target():
    logger.info("[API] POST /api/targets - 创建目标")
    data = request.get_json()
    if not data:
        logger.warning("[API] 创建目标失败: 无效的请求数据")
        return error('无效的请求数据')

    tar_url = data.get('tar_url')
    image_tag = data.get('image_tag')

    logger.debug(f"[API] 创建目标数据: tar_url={tar_url}, image_tag={image_tag}")

    if not all([tar_url, image_tag]):
        logger.warning("[API] 创建目标失败: 缺少必填字段")
        return error('缺少必填字段')

    try:
        target_id = Target.create(
            tar_url=tar_url,
            image_tag=image_tag,
            schedule_type=data.get('schedule_type', 'interval'),
            schedule_value=data.get('schedule_value', '360')
        )

        logger.info(f"[API] 目标创建成功: ID={target_id}")

        target = Target.get_by_id(target_id)
        if target.get('enabled'):
            add_job(target)
            logger.debug(f"[API] 目标已启用，添加到调度器")

        return success({'id': target_id}, '目标创建成功')
    except Exception as e:
        logger.error(f"[API] 创建目标异常: {e}")
        return error(f'创建目标失败: {str(e)}')

@bp.route('/<int:target_id>', methods=['PUT'])
def update_target(target_id):
    logger.info(f"[API] PUT /api/targets/{target_id} - 更新目标")
    data = request.get_json()
    if not data:
        logger.warning(f"[API] 更新目标 {target_id} 失败: 无效的请求数据")
        return error('无效的请求数据')

    target = Target.get_by_id(target_id)
    if not target:
        logger.warning(f"[API] 更新目标失败: 目标 {target_id} 不存在")
        return error('目标不存在', 404)

    allowed_fields = ['tar_url', 'image_tag', 'schedule_type', 'schedule_value', 'enabled']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    logger.debug(f"[API] 更新字段: {update_data}")

    try:
        Target.update(target_id, **update_data)
        logger.info(f"[API] 目标 {target_id} 更新成功")

        updated_target = Target.get_by_id(target_id)
        if updated_target.get('enabled'):
            add_job(updated_target)
            logger.debug(f"[API] 目标已启用，更新调度器")
        else:
            remove_job(target_id)
            logger.debug(f"[API] 目标已禁用，从调度器移除")

        return success(updated_target, '目标更新成功')
    except Exception as e:
        logger.error(f"[API] 更新目标 {target_id} 异常: {e}")
        return error(f'更新目标失败: {str(e)}')

@bp.route('/<int:target_id>', methods=['DELETE'])
def delete_target(target_id):
    logger.info(f"[API] DELETE /api/targets/{target_id} - 删除目标")
    target = Target.get_by_id(target_id)
    if not target:
        logger.warning(f"[API] 删除目标失败: 目标 {target_id} 不存在")
        return error('目标不存在', 404)

    try:
        remove_job(target_id)
        logger.debug(f"[API] 从调度器移除目标 {target_id}")
        Target.delete(target_id)
        logger.info(f"[API] 目标 {target_id} 删除成功")
        return success(message='目标删除成功')
    except Exception as e:
        logger.error(f"[API] 删除目标 {target_id} 异常: {e}")
        return error(f'删除目标失败: {str(e)}')

@bp.route('/<int:target_id>/trigger', methods=['POST'])
def trigger_upgrade_api(target_id):
    logger.info(f"[API] POST /api/targets/{target_id}/trigger - 触发升级")
    target = Target.get_by_id(target_id)
    if not target:
        logger.warning(f"[API] 触发升级失败: 目标 {target_id} 不存在")
        return error('目标不存在', 404)

    logger.info(f"[API] 启动升级线程，目标: {target['name']}")
    thread = threading.Thread(target=trigger_upgrade, args=(target_id,))
    thread.daemon = True
    thread.start()

    return success(message='升级已触发')

@bp.route('/<int:target_id>/info', methods=['GET'])
def get_target_info(target_id):
    logger.debug(f"[API] GET /api/targets/{target_id}/info - 获取容器信息")
    target = Target.get_by_id(target_id)
    if not target:
        logger.warning(f"[API] 获取容器信息失败: 目标 {target_id} 不存在")
        return error('目标不存在', 404)

    try:
        matched_containers = get_containers_by_image(target['image_tag'])
        if matched_containers:
            logger.debug(f"[API] 容器信息获取成功，找到 {len(matched_containers)} 个相关容器")
            return success({'containers': matched_containers})
        else:
            logger.warning(f"[API] 未找到匹配的容器: {target['image_tag']}")
            return success({'status': 'not_found', 'containers': []}, '未找到匹配的容器')
    except Exception as e:
        logger.error(f"[API] 获取容器信息异常: {e}")
        return error(f'获取容器信息失败: {str(e)}')

@bp.route('/containers', methods=['GET'])
def get_docker_containers():
    logger.debug("[API] GET /api/targets/containers - 列出所有容器")
    try:
        containers = list_containers()
        logger.info(f"[API] 返回 {len(containers)} 个容器信息")
        return success(containers)
    except Exception as e:
        logger.error(f"[API] 列出容器异常: {e}")
        return error(f'列出容器失败: {str(e)}')
