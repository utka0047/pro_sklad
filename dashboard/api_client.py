import os
import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT = 10.0


def _get(path: str, params: dict = None):
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        r = client.get(path, params=params)
        r.raise_for_status()
        return r.json()


def _post(path: str, data: dict):
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        r = client.post(path, json=data)
        r.raise_for_status()
        return r.json()


def _put(path: str, data: dict):
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        r = client.put(path, json=data)
        r.raise_for_status()
        return r.json()


def _delete(path: str):
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT) as client:
        r = client.delete(path)
        r.raise_for_status()


# ── Products ──────────────────────────────────────────────────────────────────

def get_products(category=None, low_stock_only=False):
    params = {"limit": 1000}
    if category:
        params["category"] = category
    if low_stock_only:
        params["low_stock_only"] = "true"
    return _get("/products/", params)


def get_categories():
    return _get("/products/categories")


def create_product(data: dict):
    return _post("/products/", data)


def update_product(product_id: int, data: dict):
    return _put(f"/products/{product_id}", data)


def delete_product(product_id: int):
    _delete(f"/products/{product_id}")


# ── Movements ────────────────────────────────────────────────────────────────

def get_movements(product_id=None, movement_type=None, date_from=None, date_to=None):
    params = {"limit": 500}
    if product_id:
        params["product_id"] = product_id
    if movement_type:
        params["movement_type"] = movement_type
    if date_from:
        params["date_from"] = str(date_from)
    if date_to:
        params["date_to"] = str(date_to)
    return _get("/movements/", params)


def create_movement(data: dict):
    return _post("/movements/", data)


# ── Analytics ────────────────────────────────────────────────────────────────

def get_summary():
    return _get("/analytics/summary")


def get_low_stock():
    return _get("/analytics/low-stock")


def get_movements_chart(days: int = 30):
    return _get("/analytics/movements-chart", {"days": days})


def get_top_products(limit: int = 10):
    return _get("/analytics/top-products", {"limit": limit})
