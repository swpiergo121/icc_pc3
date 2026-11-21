#!/usr/bin/env python3

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps

from dotenv import load_dotenv
load_dotenv() 

from botocore.exceptions import ClientError
from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from jinja2 import DictLoader
from werkzeug.security import check_password_hash

from aws_services import (products_t, orders_t, upload_image, get_image,
                          send_order_message, update_order_status)
from templates_html import TEMPLATES

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "cambia-esto")
app.jinja_loader = DictLoader(TEMPLATES)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


@app.context_processor
def inject_cart_count():
    return {"cart_count": lambda: sum(session.get("cart", {}).values())}


# ---------- Autenticación admin ----------
def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pwd = request.form.get("password", "")
        if (user == ADMIN_USER and ADMIN_PASSWORD_HASH
                and check_password_hash(ADMIN_PASSWORD_HASH, pwd)):
            session["admin"] = True
            flash("Sesión iniciada")
            return redirect(url_for("admin_dashboard"))
        flash("Credenciales inválidas")
    return render_template("admin_login.html", title="Admin")


@app.get("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Sesión cerrada")
    return redirect(url_for("catalog"))


@app.get("/admin")
@admin_required
def admin_dashboard():
    products = products_t.scan().get("Items", [])
    orders = sorted(orders_t.scan().get("Items", []),
                    key=lambda o: o.get("created_at", ""), reverse=True)[:20]
    return render_template("admin_dashboard.html", products=products,
                           orders=orders, title="Admin")


@app.post("/admin/products")
@admin_required
def admin_product_create():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    try:
        price = Decimal(request.form["price"]).quantize(Decimal("0.01"))
        if price <= 0:
            raise InvalidOperation
    except (InvalidOperation, KeyError):
        flash("Precio inválido")
        return redirect(url_for("admin_dashboard"))

    pid = str(uuid.uuid4())
    image_key = ""
    f = request.files.get("image")
    if f and f.filename:
        ext = f.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXT:
            flash("Formato de imagen no permitido")
            return redirect(url_for("admin_dashboard"))
        image_key = f"products/{pid}.{ext}"
        upload_image(f.stream, image_key, f.mimetype)  # S3 local

    products_t.put_item(Item={"id": pid, "name": name, "description": description,
                              "price": price, "image_key": image_key})
    flash("Producto creado")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/products/<pid>/delete")
@admin_required
def admin_product_delete(pid):
    products_t.delete_item(Key={"id": pid})
    flash("Producto eliminado")
    return redirect(url_for("admin_dashboard"))


# ---------- Catálogo e imágenes ----------
@app.get("/")
def catalog():
    products = products_t.scan().get("Items", [])
    return render_template("catalog.html", products=products, title="Catálogo")


@app.get("/images/<path:key>")
def serve_image(key):
    try:
        obj = get_image(key)
    except ClientError:
        abort(404)
    return Response(obj["Body"].read(), mimetype=obj["ContentType"])


# ---------- Carrito (en sesión) ----------
@app.post("/cart/add/<pid>")
def cart_add(pid):
    if "Item" not in products_t.get_item(Key={"id": pid}):
        abort(404)
    cart = session.get("cart", {})
    cart[pid] = cart.get(pid, 0) + 1
    session["cart"] = cart
    flash("Producto agregado al carrito")
    return redirect(url_for("catalog"))


@app.post("/cart/remove/<pid>")
def cart_remove(pid):
    cart = session.get("cart", {})
    cart.pop(pid, None)
    session["cart"] = cart
    return redirect(url_for("cart_view"))


def _cart_items():
    items, total = [], Decimal("0")
    for pid, qty in session.get("cart", {}).items():
        p = products_t.get_item(Key={"id": pid}).get("Item")
        if not p:
            continue
        subtotal = p["price"] * qty
        total += subtotal
        items.append({"id": pid, "name": p["name"], "price": p["price"],
                      "qty": qty, "subtotal": subtotal})
    return items, total


@app.get("/cart")
def cart_view():
    items, total = _cart_items()
    return render_template("cart.html", items=items, total=total, title="Carrito")


# ---------- Compra ----------
@app.post("/checkout")
def checkout():
    items, total = _cart_items()
    if not items:
        flash("El carrito está vacío")
        return redirect(url_for("cart_view"))

    order = {
        "id": str(uuid.uuid4()),
        "email": request.form.get("email", ""),
        "items": [{"product_id": i["id"], "name": i["name"],
                   "price": i["price"], "qty": i["qty"]} for i in items],
        "total": total,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    orders_t.put_item(Item=order)                      # 1. guardar en DynamoDB
    try:
        send_order_message(order)                      # 2. encolar en SQS
        update_order_status(order["id"], "QUEUED")
    except ClientError:
        app.logger.exception("Error enviando pedido a SQS")
        flash("Pedido registrado, pero hubo un problema al encolarlo")
    session.pop("cart", None)
    return render_template("order_done.html", order_id=order["id"], title="Gracias")


if __name__ == "__main__":
    app.run(debug=True, port=8000)
