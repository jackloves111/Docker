import logging

logger = logging.getLogger(__name__)

class Cleanup:
    def __init__(self):
        import docker
        import os
        socket_path = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')
        self.docker_client = docker.DockerClient(base_url=f'unix://{socket_path}')
        logger.debug("[清理器] 初始化清理器")

    def remove_tar(self, tar_path: str) -> bool:
        try:
            import os
            if tar_path and os.path.exists(tar_path):
                os.remove(tar_path)
                logger.info(f"[清理器] 删除 tar 文件: {tar_path}")
                return True
            else:
                logger.warning(f"[清理器] tar 文件不存在: {tar_path}")
        except Exception as e:
            logger.error(f"[清理器] 删除 tar 文件失败 {tar_path}: {e}")
        return False

    def remove_old_image(self, image_id: str) -> tuple:
        if not image_id:
            logger.debug("[清理器] 没有旧镜像需要删除")
            return True, "没有旧镜像需要删除"

        try:
            logger.info(f"[清理器] 开始删除旧镜像: {image_id}")
            image = self.docker_client.images.get(image_id)
            image.remove()
            logger.info(f"[清理器] 成功删除旧镜像: {image_id}")
            return True, f"已删除镜像 {image_id[:12]}"
        except Exception as e:
            error_str = str(e)
            if 'No such image' in error_str:
                logger.warning(f"[清理器] 镜像不存在: {image_id}")
                return True, f"镜像不存在: {image_id}"
            if 'is being used by' in error_str:
                logger.warning(f"[清理器] 镜像正在被使用，无法删除: {image_id}, 错误: {error_str}")
                return False, error_str
            logger.error(f"[清理器] 删除旧镜像异常: {error_str}")
            return False, error_str

    def cleanup_target_downloads(self, target_name: str, temp_dir: str) -> bool:
        try:
            import os
            import shutil
            target_dir = os.path.join(temp_dir, target_name.replace(' ', '_'))
            logger.debug(f"[清理器] 检查下载目录: {target_dir}")
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
                logger.info(f"[清理器] 清理下载目录: {target_name} ({target_dir})")
                return True
            else:
                logger.debug(f"[清理器] 下载目录不存在，无需清理: {target_dir}")
        except Exception as e:
            logger.error(f"[清理器] 清理下载目录失败 {target_name}: {e}")
        return False
