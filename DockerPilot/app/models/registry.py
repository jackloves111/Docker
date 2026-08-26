"""
Registry Model - Docker image source management
"""

import json
import logging
from app.db.database import db

logger = logging.getLogger(__name__)


class Registry:
    @staticmethod
    def get_all():
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM registry ORDER BY is_default DESC, id")
            registries = [dict(row) for row in cursor.fetchall()]
            for r in registries:
                r['is_default'] = bool(r['is_default'])
            return registries

    @staticmethod
    def get_by_id(registry_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM registry WHERE id = ?", (registry_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['is_default'] = bool(result['is_default'])
                return result
            return None

    @staticmethod
    def get_default():
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM registry WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create(name: str, url: str, username: str = "", password: str = "", is_default: bool = False):
        with db.get_cursor() as cursor:
            if is_default:
                cursor.execute("UPDATE registry SET is_default = 0")
            cursor.execute(
                "INSERT INTO registry (name, url, username, password, is_default) VALUES (?, ?, ?, ?, ?)",
                (name, url, username, password, 1 if is_default else 0)
            )
            return cursor.lastrowid

    @staticmethod
    def update(registry_id: int, **kwargs):
        allowed = ['name', 'url', 'username', 'password', 'is_default']
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        with db.get_cursor() as cursor:
            if fields.get('is_default'):
                cursor.execute("UPDATE registry SET is_default = 0")
            set_clause = ', '.join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [registry_id]
            cursor.execute(f"UPDATE registry SET {set_clause} WHERE id = ?", values)

    @staticmethod
    def delete(registry_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM registry WHERE id = ?", (registry_id,))
