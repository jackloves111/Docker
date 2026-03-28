from app.db.database import db
from datetime import datetime

class TaskLog:
    @staticmethod
    def create(target_id, target_name, action, status='running'):
        with db.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO task_logs (target_id, target_name, action, status, started_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (target_id, target_name, action, status, datetime.now().isoformat()))
            return cursor.lastrowid

    @staticmethod
    def update(log_id, status, message=None, old_image_id=None, new_image_id=None):
        with db.get_cursor() as cursor:
            cursor.execute('''
                UPDATE task_logs
                SET status = ?,
                    message = ?,
                    old_image_id = ?,
                    new_image_id = ?,
                    finished_at = ?
                WHERE id = ?
            ''', (status, message, old_image_id, new_image_id, datetime.now().isoformat(), log_id))

    @staticmethod
    def get_all(limit=50):
        with db.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM task_logs
                ORDER BY started_at DESC
                LIMIT ?
            ''', (limit,))
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def get_by_target(target_id, limit=20):
        with db.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM task_logs
                WHERE target_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            ''', (target_id, limit))
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def get_latest():
        with db.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM task_logs
                ORDER BY started_at DESC
                LIMIT 10
            ''')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def get_by_id(log_id):
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM task_logs WHERE id = ?', (log_id,))
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None

    @staticmethod
    def get_stats():
        with db.get_cursor() as cursor:
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running
                FROM task_logs
            ''')
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row))
