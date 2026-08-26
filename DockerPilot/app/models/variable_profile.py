"""
Variable Profile Model - Path variable preset management
"""

import json
import logging
from app.db.database import db

logger = logging.getLogger(__name__)


class VariableProfile:
    @staticmethod
    def get_all():
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM variable_profile ORDER BY is_default DESC, id")
            profiles = [dict(row) for row in cursor.fetchall()]
            for p in profiles:
                p['is_default'] = bool(p['is_default'])
                p['variables'] = ProfileVariable.get_by_profile(p['id'])
            return profiles

    @staticmethod
    def get_by_id(profile_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM variable_profile WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            if row:
                profile = dict(row)
                profile['is_default'] = bool(profile['is_default'])
                profile['variables'] = ProfileVariable.get_by_profile(profile_id)
                return profile
            return None

    @staticmethod
    def get_default():
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM variable_profile WHERE is_default = 1 LIMIT 1")
            row = cursor.fetchone()
            if row:
                profile = dict(row)
                profile['is_default'] = bool(profile['is_default'])
                profile['variables'] = ProfileVariable.get_by_profile(profile['id'])
                return profile
            return None

    @staticmethod
    def create(name: str, is_default: bool = False, variables: list = None):
        with db.get_cursor() as cursor:
            if is_default:
                cursor.execute("UPDATE variable_profile SET is_default = 0")
            cursor.execute(
                "INSERT INTO variable_profile (name, is_default) VALUES (?, ?)",
                (name, 1 if is_default else 0)
            )
            profile_id = cursor.lastrowid
            if variables:
                for v in variables:
                    ProfileVariable.create(profile_id, v['var_name'], v['var_value'], v.get('description', ''), cursor=cursor)
            return profile_id

    @staticmethod
    def update(profile_id: int, **kwargs):
        allowed = ['name', 'is_default']
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        with db.get_cursor() as cursor:
            if fields.get('is_default'):
                cursor.execute("UPDATE variable_profile SET is_default = 0")
            set_clause = ', '.join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [profile_id]
            cursor.execute(f"UPDATE variable_profile SET {set_clause} WHERE id = ?", values)

    @staticmethod
    def delete(profile_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM variable_profile WHERE id = ?", (profile_id,))


class ProfileVariable:
    @staticmethod
    def get_by_profile(profile_id: int):
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM profile_variable WHERE profile_id = ? ORDER BY id",
                (profile_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def create(profile_id: int, var_name: str, var_value: str, description: str = "", cursor=None):
        def _exec(cur):
            cur.execute(
                "INSERT INTO profile_variable (profile_id, var_name, var_value, description) VALUES (?, ?, ?, ?)",
                (profile_id, var_name, var_value, description)
            )
            return cur.lastrowid
        if cursor:
            return _exec(cursor)
        with db.get_cursor() as c:
            return _exec(c)

    @staticmethod
    def update(var_id: int, **kwargs):
        allowed = ['var_name', 'var_value', 'description']
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        with db.get_cursor() as cursor:
            set_clause = ', '.join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [var_id]
            cursor.execute(f"UPDATE profile_variable SET {set_clause} WHERE id = ?", values)

    @staticmethod
    def delete(var_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM profile_variable WHERE id = ?", (var_id,))

    @staticmethod
    def delete_by_profile(profile_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM profile_variable WHERE profile_id = ?", (profile_id,))

    @staticmethod
    def bulk_set(profile_id: int, variables: list):
        """Replace all variables for a profile"""
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM profile_variable WHERE profile_id = ?", (profile_id,))
            for v in variables:
                cursor.execute(
                    "INSERT INTO profile_variable (profile_id, var_name, var_value, description) VALUES (?, ?, ?, ?)",
                    (profile_id, v['var_name'], v['var_value'], v.get('description', ''))
                )


