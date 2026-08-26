"""
Image API - Pull and Load Docker images
"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from app.utils.response import success, error
from app.core.docker_client import list_images, remove_image
from app.core.image_manager import pull_image, load_image_from_url
from app.core.task_manager import task_manager
from app.models.registry import Registry

router = APIRouter(prefix="/api/images", tags=["images"])


class PullImageRequest(BaseModel):
    registry_id: Optional[int] = None
    image_name: str  # e.g., "nginx:latest"


class LoadImageRequest(BaseModel):
    url: str


@router.get("")
def get_images():
    images = list_images()
    return success(images)


@router.get("/tasks")
def get_tasks():
    """Get recent image tasks"""
    tasks = task_manager.get_all_tasks(limit=20)
    # Filter only image tasks
    tasks = [t for t in tasks if t.get("type", "").startswith("image_")]
    return success(tasks)


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get task status"""
    task = task_manager.get_task(task_id)
    if not task:
        return error("Task not found", 404)
    return success(task)


@router.post("/pull")
def api_pull_image(data: PullImageRequest):
    """Start async pull image"""
    # Get registry
    if data.registry_id:
        registry = Registry.get_by_id(data.registry_id)
        if not registry:
            return error("Registry not found", 404)
        registry_url = registry['url']
        username = registry.get('username', '')
        password = registry.get('password', '')
    else:
        registry = Registry.get_default()
        if registry:
            registry_url = registry['url']
            username = registry.get('username', '')
            password = registry.get('password', '')
        else:
            registry_url = ""
            username = ""
            password = ""

    # Create task
    task_id = task_manager.create_task("image_pull", f"Pull {data.image_name}")
    task_manager.update_task(task_id, name=data.image_name, message="Starting pull...")

    def _pull(task_mgr, tid):
        def callback(msg):
            task_mgr.update_task(tid, message=msg)
        result = pull_image(registry_url, data.image_name, username, password, callback)
        if result['success']:
            # Record as managed image
            from app.models.managed_image import ManagedImage
            ManagedImage.add(data.image_name, "pull")
            task_mgr.update_task(
                tid,
                status="success",
                progress=100,
                output=result.get('output', ''),
                message=f"Successfully pulled {data.image_name}"
            )
        else:
            task_mgr.update_task(
                tid,
                status="failed",
                error=result.get('error', 'Unknown error'),
                message=f"Failed to pull {data.image_name}"
            )

    task_manager.run_task(task_id, _pull)

    return success({"task_id": task_id}, "Pull task started")


@router.post("/load")
def api_load_image(data: LoadImageRequest):
    """Start async load image from URL"""
    # Create task
    task_id = task_manager.create_task("image_load", f"Load from URL")
    task_manager.update_task(task_id, message="Starting download...")

    def _load(task_mgr, tid):
        def callback(msg):
            task_mgr.update_task(tid, message=msg)
        result = load_image_from_url(data.url, callback)
        if result['success']:
            # Record loaded images as managed
            from app.models.managed_image import ManagedImage
            for img_tag in result.get('images', []):
                if img_tag and img_tag != '<none>':
                    ManagedImage.add(img_tag, "load")
            task_mgr.update_task(
                tid,
                status="success",
                progress=100,
                output=result.get('output', ''),
                message=f"Successfully loaded image"
            )
        else:
            task_mgr.update_task(
                tid,
                status="failed",
                error=result.get('error', 'Unknown error'),
                message=f"Failed to load image"
            )

    task_manager.run_task(task_id, _load)

    return success({"task_id": task_id}, "Load task started")


@router.post("/load/upload")
async def api_load_image_upload(file: UploadFile = File(...)):
    """Load image from uploaded tar file"""
    # Create task
    task_id = task_manager.create_task("image_load", f"Load uploaded file")
    task_manager.update_task(task_id, name=file.filename, message="Uploading file...")

    # Save uploaded file temporarily
    temp_dir = os.path.join("/config", "uploads")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(temp_path)
        task_manager.update_task(
            task_id,
            message=f"File uploaded ({file_size} bytes). Loading into Docker..."
        )

        def _load_uploaded(task_mgr, tid):
            try:
                from app.core.docker_client import get_client
                client = get_client()

                task_mgr.update_task(tid, progress=50, message="Loading image into Docker...")
                
                # Docker SDK load() requires file object, not path
                with open(temp_path, 'rb') as f:
                    result = client.images.load(f)
                
                loaded_images = []
                for img in result:
                    tags = img.tags or ["<none>"]
                    loaded_images.append(tags[0])

                # Record loaded images as managed
                from app.models.managed_image import ManagedImage
                for img_tag in loaded_images:
                    if img_tag and img_tag != '<none>':
                        ManagedImage.add(img_tag, "upload")

                # Cleanup
                os.remove(temp_path)

                task_mgr.update_task(
                    tid,
                    status="success",
                    progress=100,
                    output=f"Loaded {len(loaded_images)} image(s): {', '.join(loaded_images)}",
                    message=f"Successfully loaded {len(loaded_images)} image(s)"
                )
            except Exception as e:
                # Cleanup on error
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                raise e

        task_manager.run_task(task_id, _load_uploaded)

        return success({"task_id": task_id}, "Upload load task started")

    except Exception as e:
        # Cleanup on error
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return error(f"Failed to upload file: {str(e)}")


@router.delete("/{image_id}")
def api_remove_image(image_id: str):
    success_flag = remove_image(image_id, force=True)
    if success_flag:
        return success(message="Image removed")
    else:
        return error("Failed to remove image")


@router.post("/{image_id}/tag")
def api_tag_image(image_id: str, repository: str, tag: str = "latest"):
    """Add a tag to an image"""
    from app.core.docker_client import tag_image
    success_flag = tag_image(image_id, repository, tag)
    if success_flag:
        return success(message=f"Tagged as {repository}:{tag}")
    else:
        return error("Failed to tag image")


@router.delete("/{image_id}/untag")
def api_untag_image(image_id: str, tag: str):
    """Remove a tag from an image"""
    from app.core.docker_client import untag_image
    success_flag = untag_image(image_id, tag)
    if success_flag:
        # Remove from managed images
        from app.models.managed_image import ManagedImage
        ManagedImage.remove(tag)
        return success(message=f"Removed tag {tag}")
    else:
        return error("Failed to remove tag")


@router.get("/managed")
def get_managed_images():
    """Get list of image tags managed by this project"""
    from app.models.managed_image import ManagedImage
    tags = ManagedImage.get_all_tags()
    return success(tags)
