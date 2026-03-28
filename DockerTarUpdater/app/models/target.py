from app.db.database import db
from datetime import datetime
import json

class Target:
    @staticmethod
    def get_all():
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM targets ORDER BY created_at DESC')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def get_by_id(target_id):
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM targets WHERE id = ?', (target_id,))
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            return dict(zip(columns, row)) if row else None

    @staticmethod
    def create(name, tar_url, image_tag, schedule_type='interval', schedule_value='360'):
        with db.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO targets (name, tar_url, image_tag, schedule_type, schedule_value)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, tar_url, image_tag, schedule_type, schedule_value))
            return cursor.lastrowid

    @staticmethod
    def update(target_id, **kwargs):
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f'{key} = ?')
            values.append(value)
        fields.append('updated_at = ?')
        values.append(datetime.now().isoformat())
        values.append(target_id)

        with db.get_cursor() as cursor:
            cursor.execute(f'UPDATE targets SET {", ".join(fields)} WHERE id = ?', values)

    @staticmethod
    def delete(target_id):
        with db.get_cursor() as cursor:
            cursor.execute('DELETE FROM targets WHERE id = ?', (target_id,))

    @staticmethod
    def get_enabled():
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM targets WHERE enabled = 1')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def update_status(target_id, status, log=None):
        with db.get_cursor() as cursor:
            cursor.execute('''
                UPDATE targets
                SET last_update_status = ?,
                    last_update_log = ?,
                    last_update_time = ?
                WHERE id = ?
            ''', (status, log, datetime.now().isoformat(), target_id))
