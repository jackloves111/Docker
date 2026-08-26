"""
Logs API - Execution history
"""

from fastapi import APIRouter
from app.utils.response import success, error
from app.db.database import db

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def get_all_logs(limit: int = 100, offset: int = 0):
    """Get all execution logs with project/batch info"""
    with db.get_cursor() as cursor:
        # Get deployments with project/batch names
        cursor.execute("""
            SELECT d.*,
                   p.name as project_name,
                   b.name as batch_name,
                   pr.name as profile_name
            FROM deployment d
            LEFT JOIN project p ON d.project_id = p.id
            LEFT JOIN batch_group b ON d.batch_group_id = b.id
            LEFT JOIN variable_profile pr ON d.profile_id = pr.id
            ORDER BY d.started_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        deployments = [dict(row) for row in cursor.fetchall()]

        # Get steps for each deployment
        for dep in deployments:
            cursor.execute(
                "SELECT * FROM deployment_step WHERE deployment_id = ? ORDER BY id",
                (dep['id'],)
            )
            dep['steps'] = [dict(row) for row in cursor.fetchall()]

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM deployment")
        total = cursor.fetchone()[0]

    return success({
        "logs": deployments,
        "total": total,
        "limit": limit,
        "offset": offset
    })


@router.get("/{deployment_id}")
def get_log_detail(deployment_id: int):
    """Get detailed log for a specific deployment"""
    with db.get_cursor() as cursor:
        cursor.execute("""
            SELECT d.*,
                   p.name as project_name,
                   b.name as batch_name,
                   pr.name as profile_name
            FROM deployment d
            LEFT JOIN project p ON d.project_id = p.id
            LEFT JOIN batch_group b ON d.batch_group_id = b.id
            LEFT JOIN variable_profile pr ON d.profile_id = pr.id
            WHERE d.id = ?
        """, (deployment_id,))
        row = cursor.fetchone()
        if not row:
            return error("Deployment not found", 404)

        dep = dict(row)
        cursor.execute(
            "SELECT * FROM deployment_step WHERE deployment_id = ? ORDER BY id",
            (deployment_id,)
        )
        dep['steps'] = [dict(row) for row in cursor.fetchall()]

    return success(dep)


@router.get("/stats/summary")
def get_log_stats():
    """Get execution statistics"""
    with db.get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM deployment")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM deployment WHERE status = 'success'")
        success_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM deployment WHERE status = 'failed'")
        failed_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM deployment WHERE status = 'running'")
        running_count = cursor.fetchone()[0]

    return success({
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "running": running_count
    })
