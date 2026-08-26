"""
Managed Image Model - Tracks images pulled/loaded through this project
"""

from app.db.database import db


class ManagedImage:
    @staticmethod
    def get_all():
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM managed_image ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all_tags():
        """Get all managed image tags as a list"""
        with db.get_cursor() as cursor:
            cursor.execute("SELECT image_tag FROM managed_image")
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def add(image_tag: str, source: str = "pull"):
        """Add an image tag to managed list (ignore duplicates)"""
        with db.get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO managed_image (image_tag, source) VALUES (?, ?)",
                (image_tag, source)
            )

    @staticmethod
    def remove(image_tag: str):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM managed_image WHERE image_tag = ?", (image_tag,))
