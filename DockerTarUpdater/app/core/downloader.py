import os
import requests
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Downloader:
    def __init__(self, config=None):
        self.config = config or {}
        self.temp_dir = self.config.get('temp_dir', '/tmp/dockertarupdater/downloads')
        self.timeout = self.config.get('timeout', 300)
        self.max_retries = self.config.get('max_retries', 3)
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"[下载器] 初始化完成，临时目录: {self.temp_dir}, 超时: {self.timeout}秒, 最大重试: {self.max_retries}")

    def download(self, url: str, target_name: str) -> tuple:
        logger.info(f"[下载器] 开始下载，目标名称: {target_name}, URL: {url}")
        target_dir = os.path.join(self.temp_dir, target_name.replace(' ', '_'))
        os.makedirs(target_dir, exist_ok=True)
        local_path = os.path.join(target_dir, 'image.tar')
        logger.debug(f"[下载器] 下载路径: {local_path}")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[下载器] 第 {attempt}/{self.max_retries} 次下载尝试...")

                response = requests.get(url, stream=True, timeout=(10, None))
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                logger.debug(f"[下载器] 文件大小: {total_size} 字节")

                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                if total_size > 0 and downloaded != total_size:
                    raise Exception(f"下载不完整: 已下载 {downloaded}/{total_size} 字节")

                actual_size = os.path.getsize(local_path)
                if actual_size < 5 * 1024 * 1024:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    return False, None, f"文件过小: {actual_size} 字节 < 5MB"
                logger.info(f"[下载器] 下载完成，文件大小: {actual_size} 字节，保存路径: {local_path}")
                return True, local_path, None

            except requests.RequestException as e:
                logger.warning(f"[下载器] 下载失败 (第 {attempt}/{self.max_retries} 次): {e}")
                if attempt == self.max_retries:
                    logger.error(f"[下载器] 下载失败，已达到最大重试次数 {self.max_retries}")
                    return False, None, f"下载失败，已重试 {self.max_retries} 次: {e}"
                logger.info(f"[下载器] 等待 {5 * attempt} 秒后重试...")
                time.sleep(5 * attempt)
            except Exception as e:
                logger.error(f"[下载器] 下载异常: {e}")
                return False, None, str(e)

        return False, None, "未知错误"

    def cleanup(self, target_name: str):
        target_dir = os.path.join(self.temp_dir, target_name.replace(' ', '_'))
        try:
            if os.path.exists(target_dir):
                import shutil
                shutil.rmtree(target_dir)
                logger.info(f"[下载器] 清理下载目录完成: {target_dir}")
        except Exception as e:
            logger.error(f"[下载器] 清理下载目录失败 {target_dir}: {e}")
