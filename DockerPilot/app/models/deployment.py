"""
Deployment Model - Execution records
"""

import json
import logging
from app.db.database import db

logger = logging.getLogger(__name__)


class Deployment:
    @staticmethod
    def get_all(limit: int = 50):
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM deployment ORDER BY started_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(deployment_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM deployment WHERE id = ?", (deployment_id,))
            row = cursor.fetchone()
            if row:
                dep = dict(row)
                dep['steps'] = DeploymentStep.get_by_deployment(deployment_id)
                return dep
            return None

    @staticmethod
    def get_by_project(project_id: int, limit: int = 20):
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM deployment WHERE project_id = ? ORDER BY started_at DESC LIMIT ?",
                (project_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_batch(batch_id: int, limit: int = 20):
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM deployment WHERE batch_group_id = ? ORDER BY started_at DESC LIMIT ?",
                (batch_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def create(project_id: int = None, batch_group_id: int = None,
               profile_id: int = None, overrides: dict = None):
        with db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO deployment (project_id, batch_group_id, profile_id, overrides, status)
                   VALUES (?, ?, ?, ?, 'running')""",
                (project_id, batch_group_id, profile_id, json.dumps(overrides or {}))
            )
            return cursor.lastrowid

    @staticmethod
    def update_status(deployment_id: int, status: str, output: str = ""):
        with db.get_cursor() as cursor:
            if status in ('success', 'failed'):
                cursor.execute(
                    """UPDATE deployment SET status = ?, output = ?, finished_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (status, output, deployment_id)
                )
            else:
                cursor.execute(
                    "UPDATE deployment SET status = ?, output = ? WHERE id = ?",
                    (status, output, deployment_id)
                )


class DeploymentStep:
    @staticmethod
    def get_by_deployment(deployment_id: int):
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM deployment_step WHERE deployment_id = ? ORDER BY id",
                (deployment_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def create(deployment_id: int, batch_item_id: int = None, step_type: str = "",
               step_config: dict = None):
        with db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO deployment_step
                   (deployment_id, batch_item_id, step_type, step_config, status)
                   VALUES (?, ?, ?, ?, 'pending')""",
                (deployment_id, batch_item_id, step_type, json.dumps(step_config or {}))
            )
            return cursor.lastrowid

    @staticmethod
    def update_status(step_id: int, status: str, output: str = "", container_id: str = ""):
        with db.get_cursor() as cursor:
            if status in ('success', 'failed'):
                cursor.execute(
                    """UPDATE deployment_step
                       SET status = ?, output = ?, container_id = ?,
                           started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
                           finished_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (status, output, container_id, step_id)
                )
            else:
                cursor.execute(
                    """UPDATE deployment_step
                       SET status = ?, output = ?, container_id = ?,
                           started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                       WHERE id = ?""",
                    (status, output, container_id, step_id)
                )
