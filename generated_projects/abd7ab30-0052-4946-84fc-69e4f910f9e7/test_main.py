import pytest
from main import Catalog, Cart, Checkout, Product


def make_catalog():
    catalog = Catalog()
    catalog.add(Product(1, "Bolt", 2.5, 10))
    catalog.add(Product(2, "Wrench", 8.0, None))
    catalog.add(Product(3, "Hammer", 5.0, 0))
    return catalog


def test_catalog_add_update_delete():
    catalog = Catalog()
    p = Product(1, "Bolt", 2.5, 10)
    catalog.add(p)
    assert catalog.get(1) is p
    catalog.update(1, price=3.0)
    assert catalog.get(1).price == 3.0
    assert catalog.delete(1) is p
    assert catalog.get(1) is None
    assert catalog.all() == []


def test_cart_add_and_total():
    catalog = make_catalog()
    cart = Cart()
    resolver = catalog.get
    assert cart.add(catalog.get(1), 2) is True
    assert cart.add(catalog.get(2), 1) is True
    assert cart.total(resolver) == pytest.approx(2.5 * 2 + 8.0)


def test_cart_rejects_out_of_stock():
    catalog = make_catalog()
    cart = Cart()
    assert cart.add(catalog.get(3), 1) is False


def test_cart_empty_and_remove():
    catalog = make_catalog()
    cart = Cart()
    assert cart.is_empty() is True
    cart.add(catalog.get(1))
    assert cart.is_empty() is False
    cart.remove(1)
    assert cart.is_empty() is True


def test_cart_update_quantity():
    catalog = make_catalog()
    cart = Cart()
    cart.add(catalog.get(1))
    cart.update_quantity(1, 3)
    assert cart.total(catalog.get) == pytest.approx(2.5 * 3)
    with pytest.raises(ValueError):
        cart.update_quantity(1, 0)
    with pytest.raises(KeyError):
        cart.update_quantity(99, 1)


def test_checkout_rejects_empty_cart():
    catalog = make_catalog()
    checkout = Checkout(catalog)
    cart = Cart()
    with pytest.raises(ValueError):
        checkout.checkout(cart, {"payment": {"number": "123456789012", "name": "X"}}, catalog.get)


def test_checkout_rejects_invalid_payment():
    catalog = make_catalog()
    checkout = Checkout(catalog)
    cart = Cart()
    cart.add(catalog.get(1))
    with pytest.raises(ValueError):
        checkout.checkout(cart, {"payment": {"number": "123", "name": "X"}}, catalog.get)
    with pytest.raises(ValueError):
        checkout.checkout(cart, {"payment": {"number": "123456789012", "name": ""}}, catalog.get)


def test_checkout_creates_order_and_stocks():
    catalog = make_catalog()
    checkout = Checkout(catalog)
    cart = Cart()
    cart.add(catalog.get(1), 2)
    order = checkout.checkout(cart, {"payment": {"number": "123456789012", "name": "X"}}, catalog.get)
    assert order.order_id == 1
    assert order.total == pytest.approx(5.0)
    assert catalog.get(1).stock == 8
    assert checkout.orders() == [order]
