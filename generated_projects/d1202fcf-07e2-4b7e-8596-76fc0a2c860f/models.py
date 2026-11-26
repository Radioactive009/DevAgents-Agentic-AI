class Product:
    def __init__(self, pid, name, price):
        self.pid = pid
        self.name = name
        self.price = price


cart = {"items": {}}


def reset():
    cart["items"] = {}


def add(pid, qty=1):
    cart["items"][pid] = cart["items"].get(pid, 0) + qty
    return cart["items"]


def update(pid, qty):
    if qty <= 0:
        cart["items"].pop(pid, None)
    else:
        cart["items"][pid] = qty
    return cart["items"]


def remove(pid):
    cart["items"].pop(pid, None)
    return cart["items"]


def total(catalog):
    return sum(catalog[pid]["price"] * qty for pid, qty in cart["items"].items())
