import subprocess
import logging
import re

logger = logging.getLogger(__name__)

class Loader:
    def load(self, tar_path: str, target_tag: str) -> tuple:
        if not os.path.exists(tar_path):
            return False, None, "Tar file not found"

        try:
            logger.info(f"Loading image from {tar_path}")

            result = subprocess.run(
                ['docker', 'load', '-i', tar_path],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode != 0:
                logger.error(f"Load failed: {result.stderr}")
                return False, None, result.stderr

            image_id = self._extract_image_id(result.stdout)
            if not image_id:
                return False, None, "Failed to extract image ID from load output"

            logger.info(f"Image loaded: {image_id}")

            tag_result = subprocess.run(
                ['docker', 'tag', image_id, target_tag],
                capture_output,
                text=True
            )

            if tag_result.returncode != 0:
                logger.error(f"Tag failed: {tag_result.stderr}")
                return False, image_id, tag_result.stderr

            logger.info(f"Image tagged: {target_tag}")
            return True, image_id, target_tag

        except subprocess.TimeoutExpired:
            error_msg = "Load timeout (>10 minutes)"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Load error: {e}")
            return False, None, error_msg

    def _extract_image_id(self, output: str) -> str:
        match = re.search(r'(sha256:[a-f0-9]{12,64})', output)
        if match:
            return match.group(1)

        lines = output.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('Loaded image:'):
                return line.replace('Loaded image:', '').strip()
            if line.startswith('Loaded:'):
                return line.replace('Loaded:', '').strip()

        return None

import os
