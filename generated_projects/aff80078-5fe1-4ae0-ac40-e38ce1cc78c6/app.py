"""
AuraStore E-Commerce API & Web Application.
FastAPI service providing product catalog and cart management.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="AuraStore E-Commerce API")

class CartItem(BaseModel):
    product_id: int
    quantity: int = 1

PRODUCTS = [
    {"id": 1, "name": "Nike Air Stealth Pro", "price": 145.0, "category": "Footwear"},
    {"id": 2, "name": "Pulse ANC Headphones", "price": 199.0, "category": "Electronics"},
    {"id": 3, "name": "Titan Smartwatch Ultra", "price": 220.0, "category": "Electronics"},
    {"id": 4, "name": "Aero Waterproof Pack", "price": 89.0, "category": "Accessories"},
]
CART = []

@app.get("/api/products")
def list_products():
    return PRODUCTS

@app.post("/api/cart/add")
def add_to_cart(item: CartItem):
    product = next((p for p in PRODUCTS if p["id"] == item.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    CART.append({"product": product, "quantity": item.quantity})
    return {"status": "success", "cart_count": len(CART)}

@app.get("/api/cart")
def view_cart():
    total = sum(item["product"]["price"] * item["quantity"] for item in CART)
    return {"items": CART, "total": total}
