"""
Docker API - Docker daemon health check
"""

from fastapi import APIRouter
from app.utils.response import success, error
from app.core.docker_client import check_connection, list_containers

router = APIRouter(prefix="/api/docker", tags=["docker"])


@router.get("/health")
def docker_health():
    result = check_connection()
    return success(result)


@router.get("/containers")
def get_all_containers():
    containers = list_containers(all=True)
    return success(containers)
