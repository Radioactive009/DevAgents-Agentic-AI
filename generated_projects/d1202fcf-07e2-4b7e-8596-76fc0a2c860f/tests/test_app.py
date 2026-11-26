import app as app_module
from models import reset


def client():
    app_module.reset()
    return app_module.app.test_client()


def test_index_shows_products():
    c = client()
    r = c.get("/")
    assert r.status_code == 200
    assert b"Laptop" in r.data


def test_cart_add_remove_update():
    c = client()
    c.post("/cart/add", data={"pid": "p1"}, follow_redirects=True)
    assert b"Laptop" in c.get("/cart").data
    c.post("/cart/update", data={"pid": "p1", "qty": 3})
    assert b"Laptop x 3" in c.get("/cart").data
    c.post("/cart/remove", data={"pid": "p1"}, follow_redirects=True)
    assert b"Laptop" not in c.get("/cart").data


def test_cart_rejects_unknown_product():
    c = client()
    assert c.post("/cart/add", data={"pid": "nope"}).status_code == 400


def test_checkout_places_order_then_closes_empty():
    c = client()
    c.post("/cart/add", data={"pid": "p2"}, follow_redirects=True)
    r = c.post("/checkout")
    assert r.status_code == 200
    assert b"Order placed" in r.data
    assert c.get("/cart").data == b"<!doctype html><html><body><ul></ul><p>Total: $0</p></body></html>"
    app_module.orders.pop()


def test_checkout_empty():
    c = client()
    assert c.post("/checkout").status_code == 400
