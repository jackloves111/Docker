"""
Settings API - App settings management
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.utils.response import success, error
from app.db.database import db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    key: str
    value: str


@router.get("/{key}")
def get_setting(key: str):
    """Get a setting value"""
    with db.get_cursor() as cursor:
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return success({"key": key, "value": row[0]})
        return success({"key": key, "value": None})


@router.get("")
def get_all_settings():
    """Get all settings"""
    with db.get_cursor() as cursor:
        cursor.execute("SELECT * FROM settings")
        settings = {row[0]: row[1] for row in cursor.fetchall()}
    return success(settings)


@router.put("/{key}")
def update_setting(key: str, data: SettingUpdate):
    """Update a setting"""
    with db.get_cursor() as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, data.value)
        )
    return success(message="Setting updated")


@router.post("")
def create_setting(data: SettingUpdate):
    """Create or update a setting"""
    with db.get_cursor() as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (data.key, data.value)
        )
    return success(message="Setting saved")
