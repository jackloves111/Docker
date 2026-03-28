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

    def download(self, url: str, target_name: str) -> tuple:
        target_dir = os.path.join(self.temp_dir, target_name.replace(' ', '_'))
        os.makedirs(target_dir, exist_ok=True)
        local_path = os.path.join(target_dir, 'image.tar')

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Downloading {url} (attempt {attempt}/{self.max_retries})")

                response = requests.get(url, stream=True, timeout=self.timeout)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                if total_size > 0 and downloaded != total_size:
                    raise Exception(f"Incomplete download: {downloaded}/{total_size}")

                logger.info(f"Download completed: {local_path}")
                return True, local_path, None

            except requests.RequestException as e:
                logger.warning(f"Download failed (attempt {attempt}/{self.max_retries}): {e}")
                if attempt == self.max_retries:
                    return False, None, f"Download failed after {self.max_retries} attempts: {e}"
                time.sleep(5 * attempt)
            except Exception as e:
                logger.error(f"Download error: {e}")
                return False, None, str(e)

        return False, None, "Unknown error"

    def cleanup(self, target_name: str):
        target_dir = os.path.join(self.temp_dir, target_name.replace(' ', '_'))
        try:
            if os.path.exists(target_dir):
                import shutil
                shutil.rmtree(target_dir)
                logger.info(f"Cleaned up download directory: {target_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup {target_dir}: {e}")
