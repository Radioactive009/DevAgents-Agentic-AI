from fastapi import FastAPI, HTTPException

from models import TaskCreate, TaskUpdate, Task
from store import TaskStore

app = FastAPI(title="Todo API")
store = TaskStore()


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate):
    return store.create(payload.title)


@app.get("/tasks", response_model=list[Task])
def list_tasks():
    return store.list()


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    task = store.update(task_id, title=payload.title, completed=payload.completed)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not store.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
