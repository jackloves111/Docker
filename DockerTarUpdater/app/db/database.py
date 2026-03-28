import sqlite3
import os
from contextlib import contextmanager

class Database:
    _instance = None
    _db_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self, data_dir='/config'):
        os.makedirs(data_dir, exist_ok=True)
        self._db_path = os.path.join(data_dir, 'dockertarupdater.db')
        self._init_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self._db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        return conn

    @contextmanager
    def get_cursor(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def _init_tables(self):
        with self.get_cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(128) NOT NULL UNIQUE,
                    tar_url VARCHAR(512) NOT NULL,
                    url_type VARCHAR(16) DEFAULT 'direct',
                    image_tag VARCHAR(256) NOT NULL,
                    schedule_type VARCHAR(32) DEFAULT 'interval',
                    schedule_value VARCHAR(128) DEFAULT '360',
                    enabled INTEGER DEFAULT 1,
                    last_update_time DATETIME,
                    last_update_status VARCHAR(32),
                    last_update_log TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_id INTEGER NOT NULL,
                    target_name VARCHAR(128),
                    action VARCHAR(64),
                    status VARCHAR(32),
                    message TEXT,
                    old_image_id VARCHAR(128),
                    new_image_id VARCHAR(128),
                    started_at DATETIME,
                    finished_at DATETIME,
                    FOREIGN KEY (target_id) REFERENCES targets(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(128),
                    type VARCHAR(32) DEFAULT 'web',
                    config TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS web_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type VARCHAR(32),
                    title VARCHAR(256),
                    message TEXT,
                    read INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

db = Database()
