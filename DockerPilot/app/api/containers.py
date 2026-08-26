"""
Container API - Manage running containers
"""

from fastapi import APIRouter
from app.utils.response import success, error
from app.core.docker_client import (
    list_containers, get_container, get_container_logs,
    stop_container, start_container, remove_container
)

router = APIRouter(prefix="/api/containers", tags=["containers"])


@router.get("")
def list_all_containers():
    containers = list_containers(all=True)
    return success(containers)


@router.get("/{container_id}")
def get_container_info(container_id: str):
    container = get_container(container_id)
    if not container:
        return error("Container not found", 404)
    return success(container)


@router.get("/{container_id}/logs")
def get_container_logs_api(container_id: str, tail: int = 100):
    logs = get_container_logs(container_id, tail)
    return success({"logs": logs})


@router.post("/{container_id}/stop")
def stop_container_api(container_id: str):
    success_flag = stop_container(container_id)
    if success_flag:
        return success(message="Container stopped")
    else:
        return error("Failed to stop container")


@router.post("/{container_id}/start")
def start_container_api(container_id: str):
    success_flag = start_container(container_id)
    if success_flag:
        return success(message="Container started")
    else:
        return error("Failed to start container")


@router.delete("/{container_id}")
def remove_container_api(container_id: str):
    success_flag = remove_container(container_id, force=True)
    if success_flag:
        return success(message="Container removed")
    else:
        return error("Failed to remove container")
