import subprocess
import logging

logger = logging.getLogger(__name__)

class Cleanup:
    def __init__(self):
        pass

    def remove_tar(self, tar_path: str) -> bool:
        try:
            import os
            if tar_path and os.path.exists(tar_path):
                os.remove(tar_path)
                logger.info(f"Removed tar file: {tar_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove tar {tar_path}: {e}")
        return False

    def remove_old_image(self, image_id: str) -> tuple:
        if not image_id:
            return True, "No old image to remove"

        try:
            logger.info(f"Removing old image: {image_id}")
            result = subprocess.run(
                ['docker', 'rmi', image_id],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                if 'No such image' in result.stderr or 'is being used by' in result.stderr:
                    logger.warning(f"Cannot remove image {image_id}: {result.stderr}")
                    return False, result.stderr
                return False, result.stderr

            logger.info(f"Removed old image: {image_id}")
            return True, f"Removed image {image_id[:12]}"

        except Exception as e:
            logger.error(f"Failed to remove old image: {e}")
            return False, str(e)

    def cleanup_target_downloads(self, target_name: str, temp_dir: str) -> bool:
        try:
            import os
            import shutil
            target_dir = os.path.join(temp_dir, target_name.replace(' ', '_'))
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
                logger.info(f"Cleaned up downloads for {target_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup downloads for {target_name}: {e}")
        return False
