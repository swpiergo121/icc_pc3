#!/usr/bin/env python3

TEMPLATES = {
    "base.html": """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title or 'Tienda' }}</title>
<style>
body{font-family:system-ui,sans-serif;max-width:980px;margin:auto;padding:1rem}
nav a{margin-right:1rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem}
.card{border:1px solid #ddd;border-radius:8px;padding:.6rem}
.card img{width:100%;height:160px;object-fit:cover;border-radius:6px}
.flash{background:#eef3ff;padding:.5rem;border-radius:6px}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:.4rem;text-align:left}
</style></head><body>
<nav>
  <a href="{{ url_for('catalog') }}">Catálogo</a>
  <a href="{{ url_for('cart_view') }}">Carrito ({{ cart_count() }})</a>
  {% if session.get('admin') %}
    <a href="{{ url_for('admin_dashboard') }}">Admin</a>
    <a href="{{ url_for('admin_logout') }}">Salir</a>
  {% else %}
    <a href="{{ url_for('admin_login') }}">Acceso admin</a>
  {% endif %}
</nav>
{% for m in get_flashed_messages() %}<p class="flash">{{ m }}</p>{% endfor %}
{% block content %}{% endblock %}
</body></html>""",

    "catalog.html": """{% extends "base.html" %}
{% block content %}
<h1>Catálogo</h1>
<div class="grid">
{% for p in products %}
  <div class="card">
    {% if p.image_key %}<img src="{{ url_for('serve_image', key=p.image_key) }}" alt="">{% endif %}
    <h3>{{ p.name }}</h3>
    <p>{{ p.description }}</p>
    <p><b>S/ {{ "%.2f"|format(p.price) }}</b></p>
    <form method="post" action="{{ url_for('cart_add', pid=p.id) }}">
      <button>Agregar al carrito</button>
    </form>
  </div>
{% else %}
  <p>No hay productos todavía.</p>
{% endfor %}
</div>
{% endblock %}""",

    "cart.html": """{% extends "base.html" %}
{% block content %}
<h1>Carrito</h1>
{% if items %}
<table>
  <tr><th>Producto</th><th>Precio</th><th>Cant.</th><th>Subtotal</th><th></th></tr>
  {% for i in items %}
  <tr>
    <td>{{ i.name }}</td>
    <td>S/ {{ "%.2f"|format(i.price) }}</td>
    <td>{{ i.qty }}</td>
    <td>S/ {{ "%.2f"|format(i.subtotal) }}</td>
    <td><form method="post" action="{{ url_for('cart_remove', pid=i.id) }}"><button>Quitar</button></form></td>
  </tr>
  {% endfor %}
</table>
<h3>Total: S/ {{ "%.2f"|format(total) }}</h3>
<form method="post" action="{{ url_for('checkout') }}">
  <input type="email" name="email" placeholder="Correo (opcional)">
  <button>Comprar</button>
</form>
{% else %}
  <p>Tu carrito está vacío.</p>
{% endif %}
{% endblock %}""",

    "order_done.html": """{% extends "base.html" %}
{% block content %}
<h1>¡Gracias por tu compra!</h1>
<p>Número de pedido: <code>{{ order_id }}</code></p>
<p>El pedido fue enviado a la cola de procesamiento.</p>
<a href="{{ url_for('catalog') }}">Volver al catálogo</a>
{% endblock %}""",

    "admin_login.html": """{% extends "base.html" %}
{% block content %}
<h1>Acceso administrador</h1>
<form method="post">
  <p><input name="username" placeholder="Usuario" required></p>
  <p><input name="password" type="password" placeholder="Contraseña" required></p>
  <button>Ingresar</button>
</form>
{% endblock %}""",

    "admin_dashboard.html": """{% extends "base.html" %}
{% block content %}
<h1>Panel administrador</h1>

<h2>Nuevo producto</h2>
<form method="post" action="{{ url_for('admin_product_create') }}" enctype="multipart/form-data">
  <p><input name="name" placeholder="Nombre" required></p>
  <p><input name="price" type="number" step="0.01" min="0.01" placeholder="Precio" required></p>
  <p><textarea name="description" placeholder="Descripción"></textarea></p>
  <p><input type="file" name="image" accept="image/*"></p>
  <button>Guardar</button>
</form>

<h2>Productos</h2>
<table>
  <tr><th>Nombre</th><th>Precio</th><th></th></tr>
  {% for p in products %}
  <tr>
    <td>{{ p.name }}</td>
    <td>S/ {{ "%.2f"|format(p.price) }}</td>
    <td><form method="post" action="{{ url_for('admin_product_delete', pid=p.id) }}"><button>Eliminar</button></form></td>
  </tr>
  {% endfor %}
</table>

<h2>Últimos pedidos</h2>
<table>
  <tr><th>ID</th><th>Total</th><th>Estado</th><th>Fecha</th></tr>
  {% for o in orders %}
  <tr><td>{{ o.id }}</td><td>S/ {{ "%.2f"|format(o.total) }}</td><td>{{ o.status }}</td><td>{{ o.created_at }}</td></tr>
  {% endfor %}
</table>
{% endblock %}""",
}
