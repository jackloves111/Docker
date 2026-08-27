"""
Batch Group Model - Combination of images and projects
"""

import json
import logging
from app.db.database import db

logger = logging.getLogger(__name__)


class BatchGroup:
    @staticmethod
    def get_all():
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM batch_group ORDER BY id DESC")
            groups = [dict(row) for row in cursor.fetchall()]
            for g in groups:
                g['items'] = BatchItem.get_by_group(g['id'])
            return groups

    @staticmethod
    def get_by_id(group_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM batch_group WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            if row:
                group = dict(row)
                group['items'] = BatchItem.get_by_group(group_id)
                return group
            return None

    @staticmethod
    def create(name: str, required_vars: list = None, continue_on_error: bool = False,
               description: str = ""):
        with db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO batch_group (name, required_vars, continue_on_error, description)
                   VALUES (?, ?, ?, ?)""",
                (name, json.dumps(required_vars or []), 1 if continue_on_error else 0, description)
            )
            return cursor.lastrowid

    @staticmethod
    def update(group_id: int, **kwargs):
        allowed = ['name', 'required_vars', 'continue_on_error', 'description']
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        if 'required_vars' in fields and isinstance(fields['required_vars'], list):
            fields['required_vars'] = json.dumps(fields['required_vars'])
        if 'continue_on_error' in fields:
            fields['continue_on_error'] = 1 if fields['continue_on_error'] else 0
        with db.get_cursor() as cursor:
            set_clause = ', '.join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [group_id]
            cursor.execute(f"UPDATE batch_group SET {set_clause} WHERE id = ?", values)

    @staticmethod
    def delete(group_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM batch_group WHERE id = ?", (group_id,))

    @staticmethod
    def get_all_required_vars(group_id: int) -> list:
        """Get all unique required vars from all items in the group"""
        group = BatchGroup.get_by_id(group_id)
        if not group:
            return []
        all_vars = set()
        for item in group.get('items', []):
            config = json.loads(item.get('item_config', '{}'))
            if 'required_vars' in config:
                all_vars.update(config['required_vars'])
        return sorted(list(all_vars))


class BatchItem:
    @staticmethod
    def get_by_group(group_id: int):
        with db.get_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM batch_item WHERE group_id = ? ORDER BY sort_order",
                (group_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_id(item_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM batch_item WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def create(group_id: int, item_type: str, item_id: int = None,
               item_config: dict = None, auto_replace: bool = False, sort_order: int = 0):
        with db.get_cursor() as cursor:
            cursor.execute(
                """INSERT INTO batch_item (group_id, item_type, item_id, item_config, auto_replace, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (group_id, item_type, item_id, json.dumps(item_config or {}), 1 if auto_replace else 0, sort_order)
            )
            return cursor.lastrowid

    @staticmethod
    def update(item_id: int, **kwargs):
        allowed = ['item_type', 'item_id', 'item_config', 'auto_replace', 'sort_order']
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        if 'item_config' in fields and isinstance(fields['item_config'], dict):
            fields['item_config'] = json.dumps(fields['item_config'])
        if 'auto_replace' in fields:
            fields['auto_replace'] = 1 if fields['auto_replace'] else 0
        with db.get_cursor() as cursor:
            set_clause = ', '.join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [item_id]
            cursor.execute(f"UPDATE batch_item SET {set_clause} WHERE id = ?", values)

    @staticmethod
    def delete(item_id: int):
        with db.get_cursor() as cursor:
            cursor.execute("DELETE FROM batch_item WHERE id = ?", (item_id,))

    @staticmethod
    def reorder(group_id: int, item_orders: list):
        """item_orders: [{id: int, sort_order: int}, ...]"""
        with db.get_cursor() as cursor:
            for item in item_orders:
                cursor.execute(
                    "UPDATE batch_item SET sort_order = ? WHERE id = ? AND group_id = ?",
                    (item['sort_order'], item['id'], group_id)
                )
