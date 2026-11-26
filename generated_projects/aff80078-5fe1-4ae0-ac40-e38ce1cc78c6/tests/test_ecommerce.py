"""
Pytest Suite for E-Commerce API.
"""
import pytest
from fastapi.testclient import TestClient
from app import app, PRODUCTS

@pytest.fixture
def client():
    return TestClient(app)

def test_list_products(client):
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    assert data[0]["name"] == "Nike Air Stealth Pro"

def test_add_to_cart(client):
    res = client.post("/api/cart/add", json={"product_id": 1, "quantity": 2})
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_invalid_product_returns_404(client):
    res = client.post("/api/cart/add", json={"product_id": 999, "quantity": 1})
    assert res.status_code == 404
