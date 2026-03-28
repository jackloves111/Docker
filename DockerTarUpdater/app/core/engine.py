import logging
import traceback

logger = logging.getLogger(__name__)

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
    image_tag = target['image_tag']

    logger.info(f"[升级任务] 目标名称: {target_name}, Tar URL: {tar_url}, 镜像标签: {image_tag}")

    log_id = TaskLog.create(target_id, target_name, 'upgrade')
    logger.debug(f"[升级任务] 创建任务日志 ID: {log_id}")

    try:
        logger.info(f"[升级任务] 初始化组件...")
        downloader = __import__('app.core.downloader', fromlist=['Downloader']).Downloader(download_config)
        loader = __import__('app.core.loader', fromlist=['Loader']).Loader()
        recreator = __import__('app.core.recreator', fromlist=['Recreater']).Recreater()
        cleanup = __import__('app.core.cleanup', fromlist=['Cleanup']).Cleanup()
        notifier = Notifier()

        logger.debug(f"[升级任务] 获取容器 {target_name} 的当前信息...")
        old_container_info = None
        try:
            old_container_info = __import__('app.utils.docker_client', fromlist=['get_container_info']).get_container_info(target_name)
            if old_container_info:
                logger.debug(f"[升级任务] 容器当前镜像ID: {old_container_info.get('image_id')}")
        except Exception as e:
            logger.warning(f"[升级任务] 获取容器信息失败: {e}")

        old_image_id = old_container_info['image_id'] if old_container_info else None
        logger.debug(f"[升级任务] 旧镜像ID: {old_image_id}")

        logger.info(f"[升级任务] 发送升级开始通知...")
        notifier.notify_update_start(target_name, image_tag)

        logger.info(f"[升级任务] 开始下载 tar 包: {tar_url}")
        success, tar_path, error = downloader.download(tar_url, target_name)
        if not success:
            logger.error(f"[升级任务] 下载失败: {error}")
            TaskLog.update(log_id, 'failed', error, old_image_id)
            Target.update_status(target_id, 'failed', error)
            notifier.notify_update_failed(target_name, error)
            return

        logger.info(f"[升级任务] 下载完成，开始加载镜像: {tar_path}")
        TaskLog.update(log_id, 'running', '正在加载镜像...')

        success, image_id, error = loader.load(tar_path, image_tag)
        if not success:
            logger.error(f"[升级任务] 镜像加载失败: {error}")
            TaskLog.update(log_id, 'failed', f"加载失败: {error}", old_image_id)
            Target.update_status(target_id, 'failed', f"加载失败: {error}")
            notifier.notify_update_failed(target_name, f"加载失败: {error}")
            cleanup.cleanup_target_downloads(target_name, download_config.get('temp_dir', ''))
            return

        logger.info(f"[升级任务] 镜像加载成功，新镜像ID: {image_id}，开始重建容器...")
        TaskLog.update(log_id, 'running', '正在重建容器...', old_image_id, image_id)

        success, message = recreator.recreate(target_name, image_tag)
        if not success:
            logger.error(f"[升级任务] 容器重建失败: {message}")
            TaskLog.update(log_id, 'failed', f"重建失败: {message}", old_image_id, image_id)
            Target.update_status(target_id, 'failed', f"重建失败: {message}")
            notifier.notify_update_failed(target_name, f"重建失败: {message}")
            return

        logger.info(f"[升级任务] 清理下载临时文件...")
        cleanup.cleanup_target_downloads(target_name, download_config.get('temp_dir', ''))

        if old_image_id and old_image_id != image_id:
            logger.info(f"[升级任务] 清理旧镜像: {old_image_id}")
            cleanup.remove_old_image(old_image_id)

        logger.info(f"[升级任务] 升级成功完成！目标: {target_name}, 新镜像: {image_tag}")
        TaskLog.update(log_id, 'success', f'已更新到 {image_tag}', old_image_id, image_id)
        Target.update_status(target_id, 'success', f'成功更新到 {image_tag}')

        old_image_short = old_image_id[:12] if old_image_id else '未知'
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
