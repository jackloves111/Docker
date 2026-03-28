from app.db.database import db
from datetime import datetime
import json

class Notification:
    @staticmethod
    def get_all():
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM notifications ORDER BY created_at DESC')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            results = []
            for row in rows:
                d = dict(zip(columns, row))
                if d.get('config'):
                    d['config'] = json.loads(d['config'])
                results.append(d)
            return results

    @staticmethod
    def create(name, notif_type='web', config=None, enabled=1):
        config_json = json.dumps(config) if config else '{}'
        with db.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO notifications (name, type, config, enabled)
                VALUES (?, ?, ?, ?)
            ''', (name, notif_type, config_json, enabled))
            return cursor.lastrowid

    @staticmethod
    def update(notif_id, **kwargs):
        fields = []
        values = []
        for key, value in kwargs.items():
            if key == 'config':
                fields.append('config = ?')
                values.append(json.dumps(value))
            else:
                fields.append(f'{key} = ?')
                values.append(value)
        values.append(notif_id)

        with db.get_cursor() as cursor:
            cursor.execute(f'UPDATE notifications SET {", ".join(fields)} WHERE id = ?', values)

    @staticmethod
    def delete(notif_id):
        with db.get_cursor() as cursor:
            cursor.execute('DELETE FROM notifications WHERE id = ?', (notif_id,))

    @staticmethod
    def get_enabled():
        with db.get_cursor() as cursor:
            cursor.execute('SELECT * FROM notifications WHERE enabled = 1')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            results = []
            for row in rows:
                d = dict(zip(columns, row))
                if d.get('config'):
                    d['config'] = json.loads(d['config'])
                results.append(d)
            return results

class WebNotification:
    @staticmethod
    def create(notif_type, title, message):
        with db.get_cursor() as cursor:
            cursor.execute('''
                INSERT INTO web_notifications (type, title, message)
                VALUES (?, ?, ?)
            ''', (notif_type, title, message))
            return cursor.lastrowid

    @staticmethod
    def get_all(limit=50):
        with db.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM web_notifications
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def get_unread():
        with db.get_cursor() as cursor:
            cursor.execute('''
                SELECT * FROM web_notifications
                WHERE read = 0
                ORDER BY created_at DESC
            ''')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def mark_read(notif_ids=None):
        if notif_ids:
            placeholders = ','.join('?' * len(notif_ids))
            with db.get_cursor() as cursor:
                cursor.execute(f'UPDATE web_notifications SET read = 1 WHERE id IN ({placeholders})', notif_ids)
        else:
            with db.get_cursor() as cursor:
                cursor.execute('UPDATE web_notifications SET read = 1')

    @staticmethod
    def get_unread_count():
        with db.get_cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM web_notifications WHERE read = 0')
            return cursor.fetchone()[0]
