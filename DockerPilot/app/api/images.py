"""
Image API - Pull and Load Docker images
"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form
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
    auto_replace: bool = False  # Detect and update containers using old image


class LoadImageRequest(BaseModel):
    url: str
    auto_replace: bool = False  # Detect and update containers using old image


@router.get("")
def get_images():
    images = list_images()
    # Determine which images are ACTUALLY in use by a running container.
    # We judge by the image ID the container is currently running,
    # NOT by Config.Image: Config.Image stores the reference used at creation,
    # which may be a tag now pointing at a DIFFERENT (newer) image.
    client = None
    in_use_image_ids = set()
    in_use_config_refs = set()
    try:
        from app.core.docker_client import get_client
        client = get_client()
        containers = client.containers.list(all=True)

        for c in containers:
            if c.image:
                in_use_image_ids.add(c.image.id)
                in_use_image_ids.add(c.image.short_id)
            config_image = c.attrs.get('Config', {}).get('Image', '')
            if config_image:
                in_use_config_refs.add(config_image)
    except Exception:
        pass

    # Mark images with in_use flag
    for img in images:
        img['in_use'] = False

        # 1. Match by actual image ID (most reliable: the container runs THIS image)
        if img.get('full_id') in in_use_image_ids or img.get('id') in in_use_image_ids:
            img['in_use'] = True
            continue

        # 2. Match by tag: a tag is "in use" only if it ALSO equals the
        #    container's running image ID reference. Because Config.Image tag
        #    may have moved to a newer image, only consider it used when the
        #    container's running image has that exact tag.
        running_tags = set()
        if client is not None:
            try:
                ci = client.images.get(img['id'])
                running_tags = set(ci.tags)
            except Exception:
                running_tags = set()

        for tag in img.get('tags', []):
            if tag in in_use_config_refs and tag in running_tags:
                img['in_use'] = True
                break

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
        # "默认" = Docker Hub (official), no custom registry
        registry_url = ""
        username = ""
        password = ""

    # Create task
    task_id = task_manager.create_task("image_pull", f"Pull {data.image_name}")
    task_manager.update_task(task_id, name=data.image_name, message="开始拉取...")

    def _pull(task_mgr, tid):
        def callback(msg):
            task_mgr.update_task(tid, message=msg)
        result = pull_image(registry_url, data.image_name, username, password, callback)
        if result['success']:
            # Record as managed image
            from app.models.managed_image import ManagedImage
            ManagedImage.add(data.image_name, "pull")

            # Detect and update containers if auto_replace enabled
            update_result = None
            if data.auto_replace:
                task_mgr.update_task(tid, message="正在检测需要更新的容器...")
                from app.core.container_replace import detect_and_update_containers
                update_result = detect_and_update_containers(data.image_name)

            output = result.get('output', '')
            if update_result:
                output += f"\n\n[自动更新] {update_result.get('message', '')}"
                for r in update_result.get('results', []):
                    status = '✅' if r.get('success') else ('⏭️' if r.get('status') == 'skipped' else '❌')
                    output += f"\n  {status} {r.get('container', '?')}: {r.get('message', r.get('error', ''))}"

            task_mgr.update_task(
                tid,
                status="success",
                progress=100,
                output=output,
                update_result=update_result,
                message=f"成功拉取 {data.image_name}"
            )
        else:
            task_mgr.update_task(
                tid,
                status="failed",
                error=result.get('error', 'Unknown error'),
                message=f"拉取失败: {data.image_name}"
            )

    task_manager.run_task(task_id, _pull)

    return success({"task_id": task_id}, "Pull task started")


@router.post("/load")
def api_load_image(data: LoadImageRequest):
    """Start async load image from URL"""
    # Create task
    task_id = task_manager.create_task("image_load", f"Load from URL")
    task_manager.update_task(task_id, message="开始下载...")

    def _load(task_mgr, tid):
        def callback(msg):
            task_mgr.update_task(tid, message=msg)
        result = load_image_from_url(data.url, callback)
        if result['success']:
            # Record loaded images as managed
            from app.models.managed_image import ManagedImage
            loaded_images = []
            for img_tag in result.get('images', []):
                if img_tag and img_tag != '<none>':
                    ManagedImage.add(img_tag, "load")
                    loaded_images.append(img_tag)

            # Detect and update containers if auto_replace enabled
            update_result = None
            if data.auto_replace and loaded_images:
                task_mgr.update_task(tid, message="正在检测需要更新的容器...")
                from app.core.container_replace import detect_and_update_containers
                for img_tag in loaded_images:
                    r = detect_and_update_containers(img_tag)
                    if update_result is None:
                        update_result = r
                    else:
                        update_result['updated'] += r.get('updated', 0)
                        update_result['skipped'] += r.get('skipped', 0)
                        update_result['failed'] += r.get('failed', 0)
                        update_result['results'] = update_result.get('results', []) + r.get('results', [])

            output = result.get('output', '')
            if update_result:
                output += f"\n\n[自动更新] {update_result.get('message', '')}"
                for r in update_result.get('results', []):
                    status = '✅' if r.get('success') else ('⏭️' if r.get('status') == 'skipped' else '❌')
                    output += f"\n  {status} {r.get('container', '?')}: {r.get('message', r.get('error', ''))}"

            task_mgr.update_task(
                tid,
                status="success",
                progress=100,
                output=output,
                update_result=update_result,
                message=f"成功加载镜像"
            )
        else:
            task_mgr.update_task(
                tid,
                status="failed",
                error=result.get('error', 'Unknown error'),
                message=f"加载镜像失败"
            )

    task_manager.run_task(task_id, _load)

    return success({"task_id": task_id}, "Load task started")


@router.post("/load/upload")
async def api_load_image_upload(file: UploadFile = File(...), auto_replace: bool = Form(False)):
    """Load image from uploaded tar file"""
    # Create task
    task_id = task_manager.create_task("image_load", f"Load uploaded file")
    task_manager.update_task(task_id, name=file.filename, message="正在上传文件...")

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
            message=f"文件已上传 ({file_size} 字节)，正在加载到 Docker..."
        )

        def _load_uploaded(task_mgr, tid):
            try:
                from app.core.docker_client import get_client
                client = get_client()

                task_mgr.update_task(tid, progress=50, message="正在将镜像加载到 Docker...")
                
                # Docker SDK load() requires file object, not path
                with open(temp_path, 'rb') as f:
                    result = client.images.load(f)
                
                loaded_images = []
                for img in result:
                    tags = img.tags or ["<none>"]
                    loaded_images.append(tags[0])

                # Record loaded images as managed
                from app.models.managed_image import ManagedImage
                managed_tags = []
                for img_tag in loaded_images:
                    if img_tag and img_tag != '<none>':
                        ManagedImage.add(img_tag, "upload")
                        managed_tags.append(img_tag)

                # Detect and update containers if auto_replace enabled
                update_result = None
                if auto_replace and managed_tags:
                    task_mgr.update_task(tid, message="Detecting containers to update...")
                    from app.core.container_replace import detect_and_update_containers
                    for img_tag in managed_tags:
                        r = detect_and_update_containers(img_tag)
                        if update_result is None:
                            update_result = r
                        else:
                            update_result['updated'] += r.get('updated', 0)
                            update_result['skipped'] += r.get('skipped', 0)
                            update_result['failed'] += r.get('failed', 0)
                            update_result['results'] = update_result.get('results', []) + r.get('results', [])

                output = f"Loaded {len(loaded_images)} image(s): {', '.join(loaded_images)}"
                if update_result:
                    output += f"\n\n[Auto-Update] {update_result.get('message', '')}"
                    for r in update_result.get('results', []):
                        status = '✅' if r.get('success') else ('⏭️' if r.get('status') == 'skipped' else '❌')
                        output += f"\n  {status} {r.get('container', '?')}: {r.get('message', r.get('error', ''))}"

                # Cleanup
                os.remove(temp_path)

                task_mgr.update_task(
                    tid,
                    status="success",
                    progress=100,
                    output=output,
                    update_result=update_result,
                    message=f"成功加载 {len(loaded_images)} 个镜像"
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
