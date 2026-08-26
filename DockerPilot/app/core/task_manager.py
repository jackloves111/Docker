"""
Task Manager - Track async operations
"""

import threading
import logging
from datetime import datetime
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        self._tasks = {}
        self._lock = threading.Lock()

    def create_task(self, task_type: str, name: str = "") -> str:
        """Create a new task and return its ID"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "name": name,
                "status": "pending",
                "progress": 0,
                "message": "",
                "output": "",
                "error": None,
                "created_at": datetime.now().isoformat(),
                "finished_at": None,
            }
        return task_id

    def update_task(self, task_id: str, **kwargs):
        """Update task fields"""
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update(kwargs)

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get task by ID"""
        with self._lock:
            return self._tasks.get(task_id)

    def get_all_tasks(self, limit: int = 50) -> list:
        """Get recent tasks"""
        with self._lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda x: x.get("created_at", ""),
                reverse=True
            )
            return tasks[:limit]

    def run_task(self, task_id: str, func: Callable, *args, **kwargs):
        """Run a function in a background thread"""
        def _run():
            try:
                self.update_task(task_id, status="running", progress=10)
                result = func(self, task_id, *args, **kwargs)
                if result is None:
                    self.update_task(
                        task_id,
                        status="success",
                        progress=100,
                        finished_at=datetime.now().isoformat()
                    )
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                self.update_task(
                    task_id,
                    status="failed",
                    error=str(e),
                    finished_at=datetime.now().isoformat()
                )

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()


# Singleton instance
task_manager = TaskManager()
