from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import TaskCreate, TaskUpdate, TaskOut

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_tasks: dict[int, dict] = {}
_next_id = 1


def _get_task(task_id: int) -> dict:
    task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate):
    global _next_id
    task = {"id": _next_id, "title": payload.title, "completed": False}
    _tasks[_next_id] = task
    _next_id += 1
    return task


@app.get("/tasks", response_model=list[TaskOut])
def list_tasks():
    return [_tasks[i] for i in sorted(_tasks)]


@app.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate):
    task = _get_task(task_id)
    if payload.title is not None:
        task["title"] = payload.title
    if payload.completed is not None:
        task["completed"] = payload.completed
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    _get_task(task_id)
    del _tasks[task_id]