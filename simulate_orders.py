#!/usr/bin/env python3
"""Simula clientes reales: navega el catálogo, agrega al carrito y compra
mediante las rutas HTTP de la aplicación Flask.

Uso:
    python scripts/simulate_orders.py                       # 100 pedidos
    python scripts/simulate_orders.py --count 20 --base-url http://localhost:8000
"""
import argparse
import random
import re
import sys
import time

import requests

PRODUCT_RE = re.compile(r'/cart/add/([0-9a-fA-F-]{36})')
NAME_RE = re.compile(r'<h3>(.*?)</h3>', re.S)


def get_products(base_url):
    """Lee el catálogo HTML y extrae los IDs de producto de los formularios."""
    html = requests.get(f"{base_url}/", timeout=10).text
    ids = list(dict.fromkeys(PRODUCT_RE.findall(html)))  # sin duplicados
    if not ids:
        sys.exit("No hay productos en el catálogo. Crea al menos uno desde /admin.")
    return ids


def place_order(base_url, product_ids, n):
    """Simula un cliente: nueva sesión, varios productos, luego checkout."""
    s = requests.Session()  # cookie propia = carrito propio
    chosen = random.sample(product_ids, k=random.randint(1, min(3, len(product_ids))))

    for pid in chosen:
        for _ in range(random.randint(1, 4)):  # cada llamada suma 1 unidad
            s.post(f"{base_url}/cart/add/{pid}", timeout=10)

    resp = s.post(f"{base_url}/checkout",
                  data={"email": f"cliente{n:03d}@example.com"}, timeout=20)
    ok = resp.status_code == 200 and "Gracias por tu compra" in resp.text
    order_id = None
    m = re.search(r"Número de pedido: <code>([^<]+)</code>", resp.text)
    if m:
        order_id = m.group(1)
    return ok, order_id


def main():
    parser = argparse.ArgumentParser(description="Simula pedidos por HTTP")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--delay", type=float, default=0.0,
                        help="segundos de pausa entre pedidos")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    product_ids = get_products(base_url)
    print(f"Productos en catálogo: {len(product_ids)}")

    ok_count, failed = 0, 0
    for n in range(1, args.count + 1):
        try:
            ok, order_id = place_order(base_url, product_ids, n)
        except requests.RequestException as e:
            ok, order_id = False, None
            print(f"[{n:03d}] error de conexión: {e}")
        if ok:
            ok_count += 1
            print(f"[{n:03d}] OK  pedido {order_id}")
        else:
            failed += 1
            print(f"[{n:03d}] FALLO")
        if args.delay:
            time.sleep(args.delay)

    print(f"\nResumen: {ok_count} OK, {failed} fallidos, de {args.count} intentos")


if __name__ == "__main__":
    main()
