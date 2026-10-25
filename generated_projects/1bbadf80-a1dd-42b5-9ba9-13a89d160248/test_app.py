from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def _create(title="buy milk"):
    r = client.post("/tasks", json={"title": title})
    assert r.status_code == 201
    return r.json()


def test_create_task():
    task = _create()
    assert task["completed"] is False
    assert isinstance(task["id"], int)


def test_create_empty_title_is_422():
    r = client.post("/tasks", json={"title": ""})
    assert r.status_code == 422


def test_missing_title_is_422():
    r = client.post("/tasks", json={})
    assert r.status_code == 422


def test_list_tasks():
    _create("a")
    _create("b")
    r = client.get("/tasks")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_update_task():
    task = _create("orig")
    r = client.patch(f"/tasks/{task['id']}", json={"title": "new", "completed": True})
    assert r.status_code == 200
    assert r.json()["title"] == "new"
    assert r.json()["completed"] is True


def test_update_empty_title_is_422():
    task = _create()
    r = client.patch(f"/tasks/{task['id']}", json={"title": ""})
    assert r.status_code == 422


def test_update_missing_is_404():
    r = client.patch("/tasks/999", json={"title": "x"})
    assert r.status_code == 404


def test_delete_task():
    task = _create()
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get("/tasks").json() and all(t["id"] != task["id"] for t in client.get("/tasks").json())


def test_delete_missing_is_404():
    assert client.delete("/tasks/999").status_code == 404