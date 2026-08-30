"""
Image Manager - Pull and Load Docker images
"""

import os
import time
import logging
import requests
from app.core.docker_client import get_client

logger = logging.getLogger(__name__)

TEMP_DIR = os.environ.get("DOWNLOAD_TEMP_DIR", "/config/downloads")


def pull_image(registry_url: str, image_name: str, username: str = "", password: str = "",
               callback=None) -> dict:
    """
    Pull Docker image from registry
    registry_url: e.g., "docker.io", "registry.cn-hangzhou.aliyuncs.com"
    image_name: e.g., "nginx:latest"
    """
    try:
        client = get_client()

        # Build full image reference
        if registry_url and registry_url not in ("docker.io", "https://docker.io"):
            full_image = f"{registry_url}/{image_name}"
        else:
            full_image = image_name

        logger.info(f"[Image] Pulling {full_image}")

        # Authenticate if needed
        if username and password:
            client.login(registry=registry_url, username=username, password=password)

        # Pull with stream
        output_lines = []
        for line in client.api.pull(full_image, stream=True, decode=True):
            status = line.get("status", "")
            progress = line.get("progress", "")
            error = line.get("error", "")

            if error:
                return {"success": False, "error": error, "output": "\n".join(output_lines)}

            msg = f"{status} {progress}".strip()
            if msg:
                output_lines.append(msg)
                if callback:
                    callback(msg)

        return {
            "success": True,
            "image": full_image,
            "output": "\n".join(output_lines)
        }
    except Exception as e:
        logger.error(f"[Image] Pull failed: {e}")
        return {"success": False, "error": str(e)}


def load_image_from_url(url: str, callback=None) -> dict:
    """
    Download tar file from URL and load into Docker
    """
    try:
        os.makedirs(TEMP_DIR, exist_ok=True)
        local_path = os.path.join(TEMP_DIR, f"image_{int(time.time())}.tar")

        # Download
        if callback:
            callback(f"Downloading from {url}")

        logger.info(f"[Image] Downloading {url}")
        response = requests.get(url, stream=True, timeout=(10, 600))
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if callback and total_size > 0:
                        pct = (downloaded / total_size) * 100
                        callback(f"Downloaded {downloaded}/{total_size} bytes ({pct:.1f}%)")

        logger.info(f"[Image] Download complete: {local_path} ({downloaded} bytes)")

        # Load
        if callback:
            callback("正在将镜像加载到 Docker...")

        client = get_client()
        with open(local_path, 'rb') as f:
            result = client.images.load(f)
        loaded_images = []
        for img in result:
            tags = img.tags or ["<none>"]
            loaded_images.append(tags[0])

        # Cleanup
        os.remove(local_path)

        return {
            "success": True,
            "images": loaded_images,
            "output": f"Loaded {len(loaded_images)} image(s): {', '.join(loaded_images)}"
        }
    except Exception as e:
        logger.error(f"[Image] Load failed: {e}")
        # Cleanup on error
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass
        return {"success": False, "error": str(e)}
