import logging
import traceback
import requests

logger = logging.getLogger(__name__)


def resolve_api_url(api_url: str) -> str:
    try:
        logger.info(f"[解析] 开始解析 API URL: {api_url}")
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        resolved_url = data.get('DOC_URL') or data.get('url') or data.get('tar_url')
        if not resolved_url:
            raise ValueError(f"API 返回数据中未找到下载链接字段: {data}")
        logger.info(f"[解析] 解析完成，实际下载 URL: {resolved_url}")
        return resolved_url
    except Exception as e:
        logger.error(f"[解析] API URL 解析失败: {e}")
        raise

def run_upgrade_task(target_id):
    from flask import current_app
    from app.models.target import Target
    from app.models.task import TaskLog
    from app.core.notifier import Notifier

    logger.info(f"[升级任务] 开始处理目标 ID: {target_id}")

    config = current_app.config['APP_CONFIG']
    download_config = config.get('download', {})

    logger.debug(f"[升级任务] 下载配置: {download_config}")

    target = Target.get_by_id(target_id)
    if not target:
        logger.error(f"[升级任务] 目标 ID {target_id} 未找到")
        return

    target_name = target['name']
    tar_url = target['tar_url']
    url_type = target.get('url_type', 'direct')
    image_tag = target['image_tag']

    logger.info(f"[升级任务] 目标名称: {target_name}, Tar URL: {tar_url}, URL类型: {url_type}, 镜像标签: {image_tag}")

    log_id = TaskLog.create(target_id, target_name, 'upgrade')
    logger.debug(f"[升级任务] 创建任务日志 ID: {log_id}")

    try:
        logger.info(f"[升级任务] 初始化组件...")
        downloader = __import__('app.core.downloader', fromlist=['Downloader']).Downloader(download_config)
        loader = __import__('app.core.loader', fromlist=['Loader']).Loader()
        recreator = __import__('app.core.recreator', fromlist=['Recreater']).Recreater()
        cleanup = __import__('app.core.cleanup', fromlist=['Cleanup']).Cleanup()
        notifier = Notifier()

        logger.debug(f"[升级任务] 查找所有使用镜像 {image_tag} 的容器...")
        get_containers_by_image = __import__('app.utils.docker_client', fromlist=['get_containers_by_image']).get_containers_by_image
        matched_containers = get_containers_by_image(image_tag)
        
        # 收集所有旧镜像ID以便清理
        old_image_ids = set()
        for container in matched_containers:
            if 'image_id' in container and container['image_id']:
                old_image_ids.add(container['image_id'])
                
        # 生成简短的旧镜像ID字符串用于日志 (截取前12位)
        old_image_id_str = ",".join([img.split(':')[-1][:12] if ':' in img else img[:12] for img in old_image_ids]) if old_image_ids else None
        if old_image_id_str and len(old_image_id_str) > 120:
            old_image_id_str = old_image_id_str[:117] + "..."
        logger.debug(f"[升级任务] 匹配到 {len(matched_containers)} 个容器，旧镜像IDs: {old_image_ids}")

        logger.info(f"[升级任务] 发送升级开始通知...")
        notifier.notify_update_start(target_name, image_tag)

        logger.info(f"[升级任务] 开始下载 tar 包: {tar_url}")
        if url_type == 'api':
            tar_url = resolve_api_url(tar_url)

        success, tar_path, error = downloader.download(tar_url, target_name)
        if not success:
            logger.error(f"[升级任务] 下载失败: {error}")
            TaskLog.update(log_id, 'failed', error, old_image_id_str)
            Target.update_status(target_id, 'failed', error)
            notifier.notify_update_failed(target_name, error)
            return

        logger.info(f"[升级任务] 下载完成，开始加载镜像: {tar_path}")
        TaskLog.update(log_id, 'running', '正在加载镜像...')

        success, image_id, error = loader.load(tar_path, image_tag)
        if not success:
            logger.error(f"[升级任务] 镜像加载失败: {error}")
            TaskLog.update(log_id, 'failed', f"加载失败: {error}", old_image_id_str)
            Target.update_status(target_id, 'failed', f"加载失败: {error}")
            notifier.notify_update_failed(target_name, f"加载失败: {error}")
            cleanup.cleanup_target_downloads(target_name, download_config.get('temp_dir', ''))
            return

        logger.info(f"[升级任务] 镜像加载成功，新镜像ID: {image_id}，开始重建容器...")
        TaskLog.update(log_id, 'running', f'正在重建 {len(matched_containers)} 个容器...', old_image_id_str, image_id)

        # 逐个重建所有匹配的容器
        recreate_errors = []
        for container in matched_containers:
            container_name = container['name']
            logger.info(f"[升级任务] 开始处理容器: {container_name}")
            success, message = recreator.recreate(container_name, image_tag)
            if not success:
                logger.error(f"[升级任务] 容器 {container_name} 重建失败: {message}")
                recreate_errors.append(f"{container_name}: {message}")
        
        if recreate_errors:
            error_msg = "; ".join(recreate_errors)
            TaskLog.update(log_id, 'failed', f"部分/全部重建失败: {error_msg}", old_image_id_str, image_id)
            Target.update_status(target_id, 'failed', f"重建失败: {error_msg}")
            notifier.notify_update_failed(target_name, f"重建失败: {error_msg}")
            cleanup.cleanup_target_downloads(target_name, download_config.get('temp_dir', ''))
            return

        logger.info(f"[升级任务] 清理下载临时文件...")
        cleanup.cleanup_target_downloads(target_name, download_config.get('temp_dir', ''))

        logger.info(f"[升级任务] 清理旧镜像...")
        for old_id in old_image_ids:
            if old_id != image_id:
                cleanup.remove_old_image(old_id)

        logger.info(f"[升级任务] 升级成功完成！目标: {target_name}, 新镜像: {image_tag}")
        TaskLog.update(log_id, 'success', f'已更新 {len(matched_containers)} 个容器到 {image_tag}', old_image_id_str, image_id)
        Target.update_status(target_id, 'success', f'成功更新到 {image_tag}')

        old_image_short = next(iter(old_image_ids))[:12] if old_image_ids else '未知'
        notifier.notify_update_success(target_name, old_image_short, image_tag)

    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"[升级任务] 任务执行异常: {error_msg}")
        TaskLog.update(log_id, 'failed', error_msg)
        Target.update_status(target_id, 'failed', str(e))

        try:
            notifier = Notifier()
            notifier.notify_update_failed(target_name, str(e))
        except:
            pass

def trigger_upgrade(target_id):
    logger.info(f"[触发升级] 收到升级请求，目标ID: {target_id}")
    from app import get_app
    app = get_app()
    if app is None:
        logger.error("[触发升级] Flask 应用未初始化")
        return
    with app.app_context():
        run_upgrade_task(target_id)
