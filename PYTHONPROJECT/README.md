# Product Sales

A small product and sales app with a Flask UI, JSON API, and SQLite database.
Products store prices in cents, and a sale reduces stock and records the sale in
one database transaction.

## Run locally

```powershell
cd PYTHONPROJECT
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The database is created at
`PYTHONPROJECT/instance/product_sales.sqlite3` on first run.

To use a different database file, set `DATABASE` in the environment before
starting the app.

## API

- `GET /api/products` — list products.
- `POST /api/products` — add a product using `{"name":"Notebook","price":12.50,"stock":10}`.
- `GET /api/sales` — list recorded sales.
- `POST /api/sales` — sell stock using `{"product_id":1,"quantity":2}`.

API errors return a JSON `error` message. A sale with insufficient stock returns
HTTP `409`.

## Tests

```powershell
python -m unittest discover -s tests
```
