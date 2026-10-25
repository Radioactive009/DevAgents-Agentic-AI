import pytest
from fastapi.testclient import TestClient

import app as app_module


@pytest.fixture()
def client():
    app_module.store.reset()
    return TestClient(app_module.app)


def test_create_task(client):
    resp = client.post("/tasks", json={"title": "Write tests"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["title"] == "Write tests"
    assert data["completed"] is False


def test_create_task_requires_title(client):
    resp = client.post("/tasks", json={})
    assert resp.status_code == 422


def test_create_task_rejects_empty_title(client):
    resp = client.post("/tasks", json={"title": ""})
    assert resp.status_code == 422


def test_list_tasks(client):
    client.post("/tasks", json={"title": "A"})
    client.post("/tasks", json={"title": "B"})
    resp = client.get("/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert [t["title"] for t in data] == ["A", "B"]


def test_get_task(client):
    created = client.post("/tasks", json={"title": "Find me"}).json()
    resp = client.get(f"/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Find me"


def test_get_missing_task(client):
    resp = client.get("/tasks/999")
    assert resp.status_code == 404


def test_update_task_title(client):
    created = client.post("/tasks", json={"title": "Old"}).json()
    resp = client.put(f"/tasks/{created['id']}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


def test_update_task_completed(client):
    created = client.post("/tasks", json={"title": "Do it"}).json()
    resp = client.put(f"/tasks/{created['id']}", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["completed"] is True
    assert resp.json()["title"] == "Do it"


def test_update_task_empty_title_rejected(client):
    created = client.post("/tasks", json={"title": "Keep"}).json()
    resp = client.put(f"/tasks/{created['id']}", json={"title": ""})
    assert resp.status_code == 422


def test_update_missing_task(client):
    resp = client.put("/tasks/999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_task(client):
    created = client.post("/tasks", json={"title": "Delete me"}).json()
    resp = client.delete(f"/tasks/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_missing_task(client):
    client.delete("/tasks/999")
    assert client.get("/tasks/999").status_code == 404
