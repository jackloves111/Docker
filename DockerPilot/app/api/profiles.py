"""
Variable Profile API - Path variable preset management
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from app.utils.response import success, error
from app.models.variable_profile import VariableProfile, ProfileVariable

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


class VariableItem(BaseModel):
    var_name: str
    var_value: str
    description: str = ""


class ProfileCreate(BaseModel):
    name: str
    is_default: bool = False
    variables: List[VariableItem] = []


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None


class ProfileVariablesUpdate(BaseModel):
    variables: List[VariableItem]


@router.get("")
def list_profiles():
    profiles = VariableProfile.get_all()
    return success(profiles)


@router.get("/{profile_id}")
def get_profile(profile_id: int):
    profile = VariableProfile.get_by_id(profile_id)
    if not profile:
        return error("Profile not found", 404)
    return success(profile)


@router.post("")
def create_profile(data: ProfileCreate):
    try:
        variables = [v.dict() for v in data.variables]
        profile_id = VariableProfile.create(
            name=data.name,
            is_default=data.is_default,
            variables=variables
        )
        return success({"id": profile_id}, "Profile created")
    except Exception as e:
        return error(f"Failed to create profile: {str(e)}")


@router.put("/{profile_id}")
def update_profile(profile_id: int, data: ProfileUpdate):
    profile = VariableProfile.get_by_id(profile_id)
    if not profile:
        return error("Profile not found", 404)

    update_data = data.dict(exclude_unset=True)
    VariableProfile.update(profile_id, **update_data)
    return success(message="Profile updated")


@router.delete("/{profile_id}")
def delete_profile(profile_id: int):
    profile = VariableProfile.get_by_id(profile_id)
    if not profile:
        return error("Profile not found", 404)
    VariableProfile.delete(profile_id)
    return success(message="Profile deleted")


@router.put("/{profile_id}/variables")
def update_profile_variables(profile_id: int, data: ProfileVariablesUpdate):
    profile = VariableProfile.get_by_id(profile_id)
    if not profile:
        return error("Profile not found", 404)

    variables = [v.dict() for v in data.variables]
    ProfileVariable.bulk_set(profile_id, variables)
    return success(message="Variables updated")
