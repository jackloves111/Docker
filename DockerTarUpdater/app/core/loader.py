import os
import logging
import re

logger = logging.getLogger(__name__)

class Loader:
    def __init__(self):
        import docker
        import os
        socket_path = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')
        self.docker_client = docker.DockerClient(base_url=f'unix://{socket_path}')

    def load(self, tar_path: str, target_tag: str) -> tuple:
        logger.info(f"[加载器] 开始加载镜像，文件: {tar_path}, 标签: {target_tag}")

        if not os.path.exists(tar_path):
            logger.error(f"[加载器] Tar 文件不存在: {tar_path}")
            return False, None, "Tar 文件不存在"

        file_size = os.path.getsize(tar_path)
        logger.debug(f"[加载器] 文件大小: {file_size} 字节")

        try:
            logger.info(f"[加载器] 通过 Docker API 加载镜像...")

            with open(tar_path, 'rb') as f:
                result = self.docker_client.images.load(f)

            logger.debug(f"[加载器] Docker API 返回: {result}")

            image_id = self._extract_image_id_from_load_result(result)
            if not image_id:
                image_id = self._find_loaded_image_id(result)
                if not image_id:
                    logger.error(f"[加载器] 无法从加载结果中提取镜像 ID: {result}")
                    return False, None, "无法从加载结果中提取镜像 ID"

            logger.info(f"[加载器] 镜像加载成功，镜像ID: {image_id}")

            logger.info(f"[加载器] 打标签: {image_id} -> {target_tag}")
            self.docker_client.images.get(image_id).tag(target_tag)

            logger.info(f"[加载器] 镜像打标签成功: {target_tag}")
            return True, image_id, target_tag

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[加载器] 加载异常: {error_msg}")
            return False, None, error_msg

    def _extract_image_id_from_load_result(self, result) -> str:
        if not result:
            return None
        for img in result:
            if hasattr(img, 'id'):
                image_id = img.id
                logger.debug(f"[加载器] 从 Image 对象获取镜像 ID: {image_id}, 标签: {img.tags}")
                return image_id
        return None

    def _find_loaded_image_id(self, result) -> str:
        if not result:
            return None
        for img in result:
            if hasattr(img, 'id') and hasattr(img, 'tags'):
                logger.debug(f"[加载器] Image 对象: ID={img.id}, 标签={img.tags}")
                return img.id
        return None
