"""
DockerPilot - Database Layer
SQLite database with connection management
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "/config/pilot.db")


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @contextmanager
    def get_cursor(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_cursor() as cursor:
            # Registry - Docker image source
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    username TEXT DEFAULT '',
                    password TEXT DEFAULT '',
                    is_default INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Variable profile - path variable presets
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS variable_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Profile variables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile_variable (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    var_name TEXT NOT NULL,
                    var_value TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    FOREIGN KEY (profile_id) REFERENCES variable_profile(id) ON DELETE CASCADE
                )
            """)

            # Project - saved docker run or compose configs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('run', 'compose')),
                    command TEXT DEFAULT '',
                    compose_content TEXT DEFAULT '',
                    required_vars TEXT DEFAULT '[]',
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Batch group - combination of images and projects
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_group (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    required_vars TEXT DEFAULT '[]',
                    continue_on_error INTEGER DEFAULT 0,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Batch items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batch_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    item_type TEXT NOT NULL CHECK(item_type IN ('image_pull', 'image_load', 'project_run')),
                    item_id INTEGER,
                    item_config TEXT DEFAULT '{}',
                    auto_replace INTEGER DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (group_id) REFERENCES batch_group(id) ON DELETE CASCADE
                )
            """)

            # Deployment - execution record
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    batch_group_id INTEGER,
                    profile_id INTEGER,
                    overrides TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    output TEXT DEFAULT '',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE SET NULL,
                    FOREIGN KEY (batch_group_id) REFERENCES batch_group(id) ON DELETE SET NULL,
                    FOREIGN KEY (profile_id) REFERENCES variable_profile(id) ON DELETE SET NULL
                )
            """)

            # Deployment steps - for batch execution
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS deployment_step (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deployment_id INTEGER NOT NULL,
                    batch_item_id INTEGER,
                    step_type TEXT NOT NULL,
                    step_config TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    output TEXT DEFAULT '',
                    container_id TEXT DEFAULT '',
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY (deployment_id) REFERENCES deployment(id) ON DELETE CASCADE
                )
            """)

            # Managed images - tracks images pulled/loaded through this project
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS managed_image (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_tag TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL DEFAULT 'pull',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Settings - key-value store for app settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration: add auto_replace column to batch_item if missing
            cursor.execute("PRAGMA table_info(batch_item)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'auto_replace' not in columns:
                cursor.execute("ALTER TABLE batch_item ADD COLUMN auto_replace INTEGER DEFAULT 0")
                logger.info("[DB] Migration: added auto_replace column to batch_item")

            logger.info(f"[DB] Database initialized at {self.db_path}")


# Singleton instance
db = Database()
