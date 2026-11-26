class Product:
    def __init__(self, product_id, name, price, stock):
        self.product_id = product_id
        self.name = name
        self.price = price
        self.stock = stock


class Catalog:
    def __init__(self):
        self._items = {}

    def add(self, product):
        self._items[product.product_id] = product

    def update(self, product_id, **fields):
        product = self._items[product_id]
        for key, value in fields.items():
            setattr(product, key, value)
        return product

    def delete(self, product_id):
        return self._items.pop(product_id)

    def get(self, product_id):
        return self._items.get(product_id)

    def all(self):
        return list(self._items.values())


class Cart:
    def __init__(self):
        self._items = {}

    def add(self, product, quantity=1):
        if product.stock is not None and product.stock <= 0:
            return False
        current = self._items.get(product.product_id, 0)
        if product.stock is not None and current + quantity > product.stock:
            return False
        self._items[product.product_id] = current + quantity
        return True

    def remove(self, product_id):
        return self._items.pop(product_id, None)

    def update_quantity(self, product_id, quantity):
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if product_id not in self._items:
            raise KeyError(product_id)
        self._items[product_id] = quantity

    def is_empty(self):
        return not self._items

    def quantities(self):
        return dict(self._items)

    def total(self, resolver):
        total = 0.0
        for product_id, quantity in self._items.items():
            product = resolver(product_id)
            if product is None:
                raise KeyError(product_id)
            total += product.price * quantity
        return total


class Order:
    def __init__(self, order_id, items, total):
        self.order_id = order_id
        self.items = items
        self.total = total


class Checkout:
    def __init__(self, catalog, next_order_id=1):
        self._catalog = catalog
        self._next_order_id = next_order_id
        self._orders = []

    def _validate_payment(self, payment):
        number = str(payment.get("number", "")).strip()
        if len(number) < 12 or not number.isdigit():
            raise ValueError("invalid card number")
        if not payment.get("name"):
            raise ValueError("cardholder name is required")

    def checkout(self, cart, payload, resolver):
        if cart.is_empty():
            raise ValueError("cart is empty")
        items = []
        total = 0.0
        for product_id, quantity in cart.items(payload.get("items')):
            product = resolver(product_id)
            if product is None:
                raise ValueError(f"unknown product {product_id}")
            if product.stock is not None and quantity > product.stock:
                raise ValueError(f"out of stock for {product_id}")
            total += product.price * quantity
            items.append({"product_id": product_id, "quantity": quantity})
        self._validate_payment(payload.get("payment", {}))
        order = Order(self._next_order_id, items, total)
        self._next_order_id += 1
        self._orders.append(order)
        for item in items:
            product = resolver(item["product_id"])
            if product.stock is not None:
                product.stock -= item["quantity"]
        cart.clear()
        return order

    def orders(self):
        return list(self._orders)