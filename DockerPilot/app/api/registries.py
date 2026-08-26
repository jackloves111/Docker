"""
Registry API - Docker image source management
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.utils.response import success, error
from app.models.registry import Registry

router = APIRouter(prefix="/api/registries", tags=["registries"])


class RegistryCreate(BaseModel):
    name: str
    url: str
    username: str = ""
    password: str = ""
    is_default: bool = False


class RegistryUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_default: Optional[bool] = None


@router.get("")
def list_registries():
    registries = Registry.get_all()
    return success(registries)


@router.get("/{registry_id}")
def get_registry(registry_id: int):
    registry = Registry.get_by_id(registry_id)
    if not registry:
        return error("Registry not found", 404)
    return success(registry)


@router.post("")
def create_registry(data: RegistryCreate):
    try:
        registry_id = Registry.create(
            name=data.name,
            url=data.url,
            username=data.username,
            password=data.password,
            is_default=data.is_default
        )
        return success({"id": registry_id}, "Registry created")
    except Exception as e:
        return error(f"Failed to create registry: {str(e)}")


@router.put("/{registry_id}")
def update_registry(registry_id: int, data: RegistryUpdate):
    registry = Registry.get_by_id(registry_id)
    if not registry:
        return error("Registry not found", 404)

    update_data = data.dict(exclude_unset=True)
    Registry.update(registry_id, **update_data)
    return success(message="Registry updated")


@router.delete("/{registry_id}")
def delete_registry(registry_id: int):
    registry = Registry.get_by_id(registry_id)
    if not registry:
        return error("Registry not found", 404)
    Registry.delete(registry_id)
    return success(message="Registry deleted")
