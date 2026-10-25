from typing import List, Optional, Dict

from models import Task, TaskUpdate


class TaskStore:
    """In-memory task store with CRUD operations."""

    def __init__(self):
        self._tasks: Dict[int, Task] = {}
        self._next_id = 1

    def create(self, title: str) -> Task:
        task = Task(id=self._next_id, title=title, completed=False)
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task

    def list(self) -> List[Task]:
        return [self._tasks[k] for k in sorted(self._tasks)]

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update(self, task_id: int, title: Optional[str] = None,
               completed: Optional[bool] = None) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if title is not None:
            task.title = title
        if completed is not None:
            task.completed = completed
        return task

    def delete(self, task_id: int) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def reset(self):
        """Clear all tasks (useful for tests)."""
        self._tasks.clear()
        self._next_id = 1
