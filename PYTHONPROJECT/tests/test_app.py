import json
import os
import tempfile
import unittest

from app import create_app


class ProductSalesApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = os.path.join(self.temp_dir.name, "test.sqlite3")
        self.app = create_app({"TESTING": True, "DATABASE": database})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_product(self, name="Notebook", price=12.5, stock=5):
        return self.client.post(
            "/api/products",
            data=json.dumps({"name": name, "price": price, "stock": stock}),
            content_type="application/json",
        )

    def test_add_product_and_sell_updates_stock_and_sales(self):
        created = self.create_product()
        self.assertEqual(created.status_code, 201)
        product = created.get_json()
        self.assertEqual(product["price"], 12.5)
        self.assertEqual(product["stock"], 5)

        response = self.client.post(
            "/api/sales",
            json={"product_id": product["id"], "quantity": 2},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["total"], 25.0)

        products = self.client.get("/api/products").get_json()
        sales = self.client.get("/api/sales").get_json()
        self.assertEqual(products[0]["stock"], 3)
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0]["product_name"], "Notebook")

    def test_sale_cannot_exceed_stock_or_create_a_sale(self):
        product = self.create_product(stock=1).get_json()
        response = self.client.post(
            "/api/sales",
            json={"product_id": product["id"], "quantity": 2},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get("/api/sales").get_json(), [])
        self.assertEqual(self.client.get("/api/products").get_json()[0]["stock"], 1)

    def test_invalid_product_data_is_rejected(self):
        response = self.client.post(
            "/api/products",
            json={"name": "Invalid price", "price": 1.001, "stock": 1},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())

        response = self.client.post(
            "/api/products",
            json={"name": "Invalid stock", "price": 1, "stock": -1},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/products").get_json(), [])

    def test_sale_requires_positive_whole_quantity(self):
        product = self.create_product().get_json()
        response = self.client.post(
            "/api/sales",
            json={"product_id": product["id"], "quantity": 0},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/sales").get_json(), [])

    def test_home_page_serves_the_ui(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Product sales", response.data)


if __name__ == "__main__":
    unittest.main()
