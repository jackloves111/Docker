import logging
import traceback

logger = logging.getLogger(__name__)

def run_upgrade_task(target_id):
    from flask import current_app
    from app.models.target import Target
    from app.models.task import TaskLog
    from app.core.notifier import Notifier

    config = current_app.config['APP_CONFIG']
    download_config = config.get('download', {})

    target = Target.get_by_id(target_id)
    if not target:
        logger.error(f"Target {target_id} not found")
        return

    target_name = target['name']
    tar_url = target['tar_url']
    image_tag = target['image_tag']

    log_id = TaskLog.create(target_id, target_name, 'upgrade')

    try:
        downloader = __import__('app.core.downloader', fromlist=['Downloader']).Downloader(download_config)
        loader = __import__('app.core.loader', fromlist=['Loader']).Loader()
        recreator = __import__('app.core.recreator', fromlist=['Recreater']).Recreater()
        cleanup = __import__('app.core.cleanup', fromlist=['Cleanup']).Cleanup()
        notifier = Notifier()

        old_container_info = None
        try:
            old_container_info = __import__('app.utils.docker_client', fromlist=['get_container_info']).get_container_info(target_name)
        except:
            pass

        old_image_id = old_container_info['image_id'] if old_container_info else None

        notifier.notify_update_start(target_name, image_tag)

        success, tar_path, error = downloader.download(tar_url, target_name)
        if not success:
            TaskLog.update(log_id, 'failed', error, old_image_id)
            Target.update_status(target_id, 'failed', error)
            notifier.notify_update_failed(target_name, error)
            return

        TaskLog.update(log_id, 'running', 'Loading image...')

        success, image_id, error = loader.load(tar_path, image_tag)
        if not success:
            TaskLog.update(log_id, 'failed', f"Load failed: {error}", old_image_id)
            Target.update_status(target_id, 'failed', f"Load failed: {error}")
            notifier.notify_update_failed(target_name, f"Load failed: {error}")
            cleanup.cleanup_target_downloads(target_name, download_config.get('temp_dir', ''))
            return

        TaskLog.update(log_id, 'running', 'Recreating container...', old_image_id, image_id)

        success, message = recreator.recreate(target_name, image_tag)
        if not success:
            TaskLog.update(log_id, 'failed', f"Recreate failed: {message}", old_image_id, image_id)
            Target.update_status(target_id, 'failed', f"Recreate failed: {message}")
            notifier.notify_update_failed(target_name, f"Recreate failed: {message}")
            return

        cleanup.cleanup_target_downloads(target_name, download_config.get('temp_dir', ''))

        if old_image_id and old_image_id != image_id:
            cleanup.remove_old_image(old_image_id)

        TaskLog.update(log_id, 'success', f'Updated to {image_tag}', old_image_id, image_id)
        Target.update_status(target_id, 'success', f'Successfully updated to {image_tag}')

        old_image_short = old_image_id[:12] if old_image_id else 'unknown'
        notifier.notify_update_success(target_name, old_image_short, image_tag)

        logger.info(f"Successfully updated {target_name}")

    except Exception as e:
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"Upgrade task failed: {error_msg}")
        TaskLog.update(log_id, 'failed', error_msg)
        Target.update_status(target_id, 'failed', str(e))

        try:
            notifier = Notifier()
            notifier.notify_update_failed(target_name, str(e))
        except:
            pass

def trigger_upgrade(target_id):
    from app import app
    with app.app_context():
        run_upgrade_task(target_id)
