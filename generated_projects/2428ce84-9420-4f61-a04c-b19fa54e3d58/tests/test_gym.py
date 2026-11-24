"""
Pytest Suite for Gym Application.
"""
import pytest
from fastapi.testclient import TestClient
from app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_trainers(client):
    res = client.get("/api/trainers")
    assert res.status_code == 200
    assert len(res.json()) == 3

def test_book_trainer(client):
    res = client.post("/api/book", json={"trainer_name": "Marcus Vance", "client_name": "Alex", "phone": "555-0199"})
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"
