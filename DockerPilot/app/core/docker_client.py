"""
Docker Client - Wraps docker SDK for Python
"""

import os
import logging
import docker
from docker.errors import NotFound, APIError

logger = logging.getLogger(__name__)

SOCKET_PATH = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")


def get_client():
    """Get Docker client connected to host daemon"""
    logger.info(f"[Docker] Connecting to: {SOCKET_PATH}")
    client = docker.DockerClient(base_url=f"unix://{SOCKET_PATH}")
    logger.info(f"[Docker] Docker client created successfully")
    return client


def check_connection() -> dict:
    """Check Docker daemon connection"""
    try:
        client = get_client()
        info = client.info()
        return {
            "connected": True,
            "server_version": info.get("ServerVersion", "unknown"),
            "os": info.get("OperatingSystem", "unknown"),
            "containers_running": info.get("ContainersRunning", 0),
            "images": info.get("Images", 0),
        }
    except Exception as e:
        logger.error(f"[Docker] Connection check failed: {e}")
        return {"connected": False, "error": str(e)}


def list_images():
    """List all local Docker images"""
    try:
        client = get_client()
        images = client.images.list()
        result = []
        for img in images:
            tags = img.tags or ["<none>:<none>"]
            result.append({
                "id": img.short_id,
                "full_id": img.id,
                "tags": tags,
                "size": img.attrs.get("Size", 0),
                "created": img.attrs.get("Created", ""),
            })
        return result
    except Exception as e:
        logger.error(f"[Docker] List images failed: {e}")
        return []


def list_containers(all: bool = True):
    """List Docker containers using CLI"""
    import subprocess
    try:
        cmd = ["docker", "ps"]
        if all:
            cmd.append("-a")
        cmd.extend(["--format", '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.Status}}","state":"{{.State}}","created":"{{.CreatedAt}}","ports":"{{.Ports}}"}'])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error(f"[Docker] CLI error: {result.stderr}")
            return []

        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    import json
                    c = json.loads(line)
                    containers.append({
                        "id": c.get("id", ""),
                        "full_id": c.get("id", ""),
                        "name": c.get("name", ""),
                        "image": c.get("image", ""),
                        "status": c.get("status", ""),
                        "state": c.get("state", ""),
                        "created": c.get("created", ""),
                        "ports": c.get("ports", ""),
                    })
                except json.JSONDecodeError:
                    continue

        logger.info(f"[Docker] Found {len(containers)} containers via CLI")
        return containers
    except Exception as e:
        logger.error(f"[Docker] List containers failed: {e}", exc_info=True)
        return []


def get_container(container_id: str):
    """Get container by ID or name"""
    try:
        client = get_client()
        container = client.containers.get(container_id)
        return {
            "id": container.short_id,
            "full_id": container.id,
            "name": container.name,
            "image": container.image.tags[0] if container.image.tags else str(container.image.short_id),
            "status": container.status,
            "state": container.state,
            "created": container.attrs.get("Created", ""),
            "ports": container.ports,
            "mounts": [
                {
                    "type": m.get("Type"),
                    "source": m.get("Source"),
                    "destination": m.get("Destination"),
                    "mode": m.get("Mode"),
                    "rw": m.get("RW"),
                }
                for m in container.attrs.get("Mounts", [])
            ],
            "network_settings": container.attrs.get("NetworkSettings", {}),
        }
    except NotFound:
        return None
    except Exception as e:
        logger.error(f"[Docker] Get container failed: {e}")
        return None


def get_container_logs(container_id: str, tail: int = 100) -> str:
    """Get container logs"""
    try:
        client = get_client()
        container = client.containers.get(container_id)
        logs = container.logs(tail=tail, timestamps=True)
        return logs.decode("utf-8", errors="replace")
    except NotFound:
        return f"Container {container_id} not found"
    except Exception as e:
        logger.error(f"[Docker] Get logs failed: {e}")
        return f"Error: {str(e)}"


def stop_container(container_id: str) -> bool:
    """Stop a running container"""
    try:
        client = get_client()
        container = client.containers.get(container_id)
        container.stop(timeout=10)
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.error(f"[Docker] Stop container failed: {e}")
        return False


def start_container(container_id: str) -> bool:
    """Start a stopped container"""
    try:
        client = get_client()
        container = client.containers.get(container_id)
        container.start()
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.error(f"[Docker] Start container failed: {e}")
        return False


def remove_container(container_id: str, force: bool = False) -> bool:
    """Remove a container"""
    try:
        client = get_client()
        container = client.containers.get(container_id)
        container.remove(force=force)
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.error(f"[Docker] Remove container failed: {e}")
        return False


def remove_image(image_id: str, force: bool = False) -> bool:
    """Remove a Docker image"""
    try:
        client = get_client()
        client.images.remove(image_id, force=force)
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.error(f"[Docker] Remove image failed: {e}")
        return False


def tag_image(image_id: str, repository: str, tag: str = "latest") -> bool:
    """Tag a Docker image"""
    try:
        client = get_client()
        image = client.images.get(image_id)
        image.tag(repository, tag)
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.error(f"[Docker] Tag image failed: {e}")
        return False


def untag_image(image_id: str, tag: str) -> bool:
    """Remove a tag from a Docker image"""
    try:
        client = get_client()
        # Get the image to verify it exists
        image = client.images.get(image_id)
        
        # Use low-level API to remove just the tag
        # The tag parameter should be the full tag like "nginx:latest"
        client.api.remove_image(tag, noprune=True)
        return True
    except NotFound:
        return False
    except Exception as e:
        logger.error(f"[Docker] Untag image failed: {e}")
        return False
