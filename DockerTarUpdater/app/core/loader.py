import os
import subprocess
import logging
import re

logger = logging.getLogger(__name__)

class Loader:
    def load(self, tar_path: str, target_tag: str) -> tuple:
        logger.info(f"[加载器] 开始加载镜像，文件: {tar_path}, 标签: {target_tag}")

        if not os.path.exists(tar_path):
            logger.error(f"[加载器] Tar 文件不存在: {tar_path}")
            return False, None, "Tar 文件不存在"

        file_size = os.path.getsize(tar_path)
        logger.debug(f"[加载器] 文件大小: {file_size} 字节")

        try:
            logger.info(f"[加载器] 执行 docker load -i {tar_path}")
            result = subprocess.run(
                ['docker', 'load', '-i', tar_path],
                capture_output=True,
                text=True,
                timeout=600
            )

            logger.debug(f"[加载器] docker load 返回码: {result.returncode}")
            logger.debug(f"[加载器] stdout: {result.stdout}")
            logger.debug(f"[加载器] stderr: {result.stderr}")

            if result.returncode != 0:
                logger.error(f"[加载器] docker load 失败: {result.stderr}")
                return False, None, result.stderr

            image_id = self._extract_image_id(result.stdout)
            if not image_id:
                logger.error(f"[加载器] 无法从输出中提取镜像 ID，输出: {result.stdout}")
                return False, None, "无法从加载输出中提取镜像 ID"

            logger.info(f"[加载器] 镜像加载成功，镜像ID: {image_id}")

            logger.info(f"[加载器] 执行 docker tag {image_id} {target_tag}")
            tag_result = subprocess.run(
                ['docker', 'tag', image_id, target_tag],
                capture_output,
                text=True
            )

            if tag_result.returncode != 0:
                logger.error(f"[加载器] 镜像打标签失败: {tag_result.stderr}")
                return False, image_id, tag_result.stderr

            logger.info(f"[加载器] 镜像打标签成功: {target_tag}")
            return True, image_id, target_tag

        except subprocess.TimeoutExpired:
            error_msg = "加载超时 (>10分钟)"
            logger.error(f"[加载器] {error_msg}")
            return False, None, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[加载器] 加载异常: {error_msg}")
            return False, None, error_msg

    def _extract_image_id(self, output: str) -> str:
        logger.debug(f"[加载器] 正在从输出中提取镜像 ID: {output}")

        match = re.search(r'(sha256:[a-f0-9]{12,64})', output)
        if match:
            image_id = match.group(1)
            logger.debug(f"[加载器] 通过正则找到镜像 ID: {image_id}")
            return image_id

        lines = output.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('Loaded image:'):
                result = line.replace('Loaded image:', '').strip()
                logger.debug(f"[加载器] 从 'Loaded image:' 提取: {result}")
                return result
            if line.startswith('Loaded:'):
                result = line.replace('Loaded:', '').strip()
                logger.debug(f"[加载器] 从 'Loaded:' 提取: {result}")
                return result

        logger.warning(f"[加载器] 无法从输出中提取镜像 ID")
        return None
