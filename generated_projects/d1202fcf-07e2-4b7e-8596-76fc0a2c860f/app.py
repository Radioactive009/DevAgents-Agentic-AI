from flask import Flask, render_template_string, request, redirect, url_for
from models import Product, cart, reset, add, update, remove, total

PAGES = {
    "p1": Product("p1", "Laptop", 999),
    "p2": Product("p2", "Mouse", 15),
    "p3": Product("p3", "Keyboard", 45),
}

catalog = {p: {"name": x.name, "price": x.price} for p, x in PAGES.items()}

orders = []


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template_string(
            "<!doctype html><html><head><title>Shop</title></head><body>" +
            "".join(
                f"<div data-pid='{p}'><h2>{v['name']}</h2><p>${v['price']}</p>"
                f"<form method='post' action='/cart/add'><input type='hidden' name='pid' value='{p}'/>"
                f"<button>Add</button></form></div>"
                for p, v in catalog.items()
            ) +
            "</body></html>"
        )

    @app.route("/cart/add", methods=["POST"])
    def add_item():
        pid = request.form.get("pid")
        if pid not in catalog:
            return "bad product", 400
        add(pid, 1)
        return redirect(url_for("cart_view"))

    @app.route("/cart")
    def cart_view():
        lines = [f"{v['name']} x {q} = ${v['price'] * q}" for pl, q in cart["items"].items() for v in [catalog[pl]]]
        html = "<!doctype html><html><body><ul>" + "".join(f"<li>{l}</li>" for l in lines) + \
               f"</ul><p>Total: ${total(catalog)}</p></body></html>"
        return html

    @app.route("/cart/update", methods=["POST"])
    def update_item():
        pid = request.form.get("pid")
        qty = int(request.form.get("qty"))
        if pid not in catalog:
            return "bad product", 400
        update(pid, qty)
        return redirect(url_for("cart_view"))

    @app.route("/cart/remove", methods=["POST"])
    def remove_item():
        remove(request.form.get("pid"))
        return redirect(url_for("cart_view"))

    @app.route("/checkout", methods=["POST"])
    def checkout():
        if not cart["items"]:
            return "Empty cart", 400
        order = {"items": dict(cart["items"]), "total": total(catalog)}
        orders.append(order)
        reset()
        return f"Order placed: {order['total']}"

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
