const productForm = document.querySelector("#product-form");
const productsBody = document.querySelector("#products-body");
const salesBody = document.querySelector("#sales-body");
const productCount = document.querySelector("#product-count");
const notice = document.querySelector("#notice");

const money = new Intl.NumberFormat(undefined, {
  style: "currency",
  currency: "USD",
});

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "The request could not be completed.");
  }
  return result;
}

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.toggle("notice-error", isError);
  notice.hidden = false;
}

function cell(value, className) {
  const element = document.createElement("td");
  if (className) element.className = className;
  element.textContent = value;
  return element;
}

function renderProducts(products) {
  productCount.textContent = `${products.length} ${products.length === 1 ? "product" : "products"}`;
  productsBody.replaceChildren();
  if (products.length === 0) {
    const row = document.createElement("tr");
    const empty = cell("No products yet. Add one above to get started.", "empty-state");
    empty.colSpan = 4;
    row.append(empty);
    productsBody.append(row);
    return;
  }

  for (const product of products) {
    const row = document.createElement("tr");
    row.append(
      cell(product.name, "product-name"),
      cell(money.format(product.price)),
      cell(product.stock, product.stock === 0 ? "stock-empty" : ""),
    );

    const action = document.createElement("td");
    const form = document.createElement("form");
    form.className = "sell-form";
    const quantity = document.createElement("input");
    quantity.type = "number";
    quantity.name = "quantity";
    quantity.min = "1";
    quantity.step = "1";
    quantity.value = "1";
    quantity.max = String(Math.max(product.stock, 1));
    quantity.setAttribute("aria-label", `Quantity of ${product.name} to sell`);
    quantity.required = true;
    const button = document.createElement("button");
    button.className = "button button-small";
    button.type = "submit";
    button.textContent = "Sell";
    button.disabled = product.stock === 0;
    form.append(quantity, button);
    form.addEventListener("submit", (event) => sellProduct(event, product.id, form));
    action.append(form);
    row.append(action);
    productsBody.append(row);
  }
}

function renderSales(sales) {
  salesBody.replaceChildren();
  if (sales.length === 0) {
    const row = document.createElement("tr");
    const empty = cell("No sales have been recorded yet.", "empty-state");
    empty.colSpan = 4;
    row.append(empty);
    salesBody.append(row);
    return;
  }

  for (const sale of sales) {
    const row = document.createElement("tr");
    const date = new Date(`${sale.sold_at.replace(" ", "T")}Z`);
    row.append(
      cell(sale.product_name, "product-name"),
      cell(sale.quantity),
      cell(money.format(sale.total), "sale-total"),
      cell(date.toLocaleString()),
    );
    salesBody.append(row);
  }
}

async function refresh() {
  const [products, sales] = await Promise.all([
    api("/api/products"),
    api("/api/sales"),
  ]);
  renderProducts(products);
  renderSales(sales);
}

productForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(productForm);
  const payload = {
    name: formData.get("name"),
    price: formData.get("price"),
    stock: Number(formData.get("stock")),
  };
  try {
    const product = await api("/api/products", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    productForm.reset();
    productForm.elements.stock.value = "0";
    showNotice(`${product.name} added to your catalog.`);
    await refresh();
  } catch (error) {
    showNotice(error.message, true);
  }
});

async function sellProduct(event, productId, form) {
  event.preventDefault();
  const quantity = Number(new FormData(form).get("quantity"));
  try {
    const sale = await api("/api/sales", {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    });
    showNotice(`Sold ${sale.quantity} × ${sale.product_name} for ${money.format(sale.total)}.`);
    await refresh();
  } catch (error) {
    showNotice(error.message, true);
  }
}

refresh().catch((error) => {
  showNotice(error.message, true);
  productsBody.replaceChildren();
  salesBody.replaceChildren();
});
