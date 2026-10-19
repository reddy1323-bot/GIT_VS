from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import sqlite3

from flask import Flask, g, jsonify, render_template, request


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents > 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    total_cents INTEGER NOT NULL CHECK (total_cents > 0),
    sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "product_sales.sqlite3")
        )
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    with sqlite3.connect(app.config["DATABASE"]) as database:
        database.executescript(SCHEMA)

    def get_db():
        if "database" not in g:
            g.database = sqlite3.connect(app.config["DATABASE"])
            g.database.row_factory = sqlite3.Row
            g.database.execute("PRAGMA foreign_keys = ON")
        return g.database

    @app.teardown_appcontext
    def close_db(_error=None):
        database = g.pop("database", None)
        if database is not None:
            database.close()

    def error(message, status):
        return jsonify({"error": message}), status

    def json_object():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None
        return data

    def price_to_cents(value):
        if isinstance(value, bool) or value is None:
            return None
        try:
            price = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        if not price.is_finite() or price <= 0:
            return None
        cents = price * 100
        if cents != cents.to_integral_value():
            return None
        return int(cents)

    def product_json(product):
        return {
            "id": product["id"],
            "name": product["name"],
            "price": product["price_cents"] / 100,
            "stock": product["stock"],
        }

    def sale_json(sale):
        return {
            "id": sale["id"],
            "product_id": sale["product_id"],
            "product_name": sale["product_name"],
            "quantity": sale["quantity"],
            "unit_price": sale["unit_price_cents"] / 100,
            "total": sale["total_cents"] / 100,
            "sold_at": sale["sold_at"],
        }

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/products")
    def list_products():
        products = get_db().execute(
            "SELECT id, name, price_cents, stock FROM products ORDER BY name, id"
        ).fetchall()
        return jsonify([product_json(product) for product in products])

    @app.post("/api/products")
    def create_product():
        data = json_object()
        if data is None:
            return error("Request body must be a JSON object.", 400)

        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            return error("Product name is required.", 400)
        name = name.strip()
        if len(name) > 120:
            return error("Product name must be 120 characters or fewer.", 400)

        price_cents = price_to_cents(data.get("price"))
        if price_cents is None:
            return error("Price must be a positive amount with at most 2 decimal places.", 400)

        stock = data.get("stock", 0)
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            return error("Stock must be a non-negative whole number.", 400)

        database = get_db()
        cursor = database.execute(
            "INSERT INTO products (name, price_cents, stock) VALUES (?, ?, ?)",
            (name, price_cents, stock),
        )
        database.commit()
        product = database.execute(
            "SELECT id, name, price_cents, stock FROM products WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return jsonify(product_json(product)), 201

    @app.get("/api/sales")
    def list_sales():
        sales = get_db().execute(
            """SELECT id, product_id, product_name, quantity, unit_price_cents,
                      total_cents, sold_at
               FROM sales ORDER BY id DESC"""
        ).fetchall()
        return jsonify([sale_json(sale) for sale in sales])

    @app.post("/api/sales")
    def create_sale():
        data = json_object()
        if data is None:
            return error("Request body must be a JSON object.", 400)

        product_id = data.get("product_id")
        quantity = data.get("quantity")
        if isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0:
            return error("Product ID must be a positive whole number.", 400)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            return error("Quantity must be a positive whole number.", 400)

        database = get_db()
        product = database.execute(
            "SELECT id, name, price_cents, stock FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if product is None:
            return error("Product not found.", 404)
        if product["stock"] < quantity:
            return error("Not enough stock to complete this sale.", 409)

        updated = database.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (quantity, product_id, quantity),
        )
        if updated.rowcount != 1:
            database.rollback()
            return error("Not enough stock to complete this sale.", 409)

        unit_price_cents = product["price_cents"]
        cursor = database.execute(
            """INSERT INTO sales
               (product_id, product_name, quantity, unit_price_cents, total_cents)
               VALUES (?, ?, ?, ?, ?)""",
            (
                product_id,
                product["name"],
                quantity,
                unit_price_cents,
                unit_price_cents * quantity,
            ),
        )
        database.commit()
        sale = database.execute(
            """SELECT id, product_id, product_name, quantity, unit_price_cents,
                      total_cents, sold_at
               FROM sales WHERE id = ?""",
            (cursor.lastrowid,),
        ).fetchone()
        return jsonify(sale_json(sale)), 201

    return app


app = create_app()


if __name__ == "__main__":
    app.run()
