"""
Project Model - Saved docker run or compose configurations
"""

import json
import logging
from app.db.database import db

logger = logging.getLogger(__name__)


class Project:
    @staticmethod
    def get_all():
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM project ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(project_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM project WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create(name: str, project_type: str, command: str = "", compose_content: str = "",
               required_vars: list = None, description: str = ""):
        with db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO project (name, type, command, compose_content, required_vars, description)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, project_type, command, compose_content,
                 json.dumps(required_vars or []), description)
            )
            return cursor.lastrowid

    @staticmethod
    def update(project_id: int, **kwargs):
        allowed = ['name', 'type', 'command', 'compose_content', 'required_vars', 'description']
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        # Convert list to JSON string
        if 'required_vars' in fields and isinstance(fields['required_vars'], list):
            fields['required_vars'] = json.dumps(fields['required_vars'])
        with db.get_cursor() as cursor:
            fields['updated_at'] = 'CURRENT_TIMESTAMP'
            set_parts = []
            values = []
            for k, v in fields.items():
                if v == 'CURRENT_TIMESTAMP':
                    set_parts.append(f"{k} = CURRENT_TIMESTAMP")
                else:
                    set_parts.append(f"{k} = ?")
                    values.append(v)
            values.append(project_id)
            cursor.execute(f"UPDATE project SET {', '.join(set_parts)} WHERE id = ?", values)

    @staticmethod
    def delete(project_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM project WHERE id = ?", (project_id,))

    @staticmethod
    def get_required_var_names(project_id: int) -> list:
        project = Project.get_by_id(project_id)
        if project:
            return json.loads(project.get('required_vars', '[]'))
        return []
