
from flask import Flask, request, redirect, render_template_string
import sqlite3
from datetime import datetime, date

app = Flask(__name__)
DB_NAME = "shop.db"


# =============== DATABASE ===============

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                qty INTEGER NOT NULL DEFAULT 0,
                price REAL NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL DEFAULT '',
                qty INTEGER NOT NULL DEFAULT 0,
                unit_price REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL DEFAULT 0,
                sale_date TEXT NOT NULL DEFAULT ''
            )
        """)

        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(sales)").fetchall()
        }

        for column, definition in {
            "product_name": "TEXT NOT NULL DEFAULT ''",
            "qty": "INTEGER NOT NULL DEFAULT 0",
            "unit_price": "REAL NOT NULL DEFAULT 0",
            "total": "REAL NOT NULL DEFAULT 0",
            "sale_date": "TEXT NOT NULL DEFAULT ''"
        }.items():
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE sales ADD COLUMN {column} {definition}"
                )

        count = conn.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        if count == 0:
            conn.executemany(
                "INSERT INTO products (name, qty, price) VALUES (?, ?, ?)",
                [
                    ("Rice", 20, 60),
                    ("Sugar", 10, 45),
                    ("Milk", 15, 30)
                ]
            )


# =============== DASHBOARD HTML ===============

PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartStock AI</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0; font-family: Arial, sans-serif;
    background: #f3f6fb; color: #1e293b;
}
header { background: #142b4a; color: white; padding: 22px; }
header h1 { margin: 0; }
header p { color: #dbeafe; }
.container { max-width: 1200px; margin: auto; padding: 22px; }
.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 15px; margin-bottom: 20px;
}
.card, .panel {
    background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 3px 12px #0000000b; margin-bottom: 20px;
}
.card h3 { font-size: 14px; color: #64748b; }
.number { font-size: 25px; font-weight: bold; overflow-wrap: anywhere; }
.forms {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
}
input, button, .link-button {
    width: 100%; padding: 11px; border: 1px solid #cbd5e1;
    border-radius: 7px; font-size: 14px;
}
input { margin: 7px 0 12px; }
button, .link-button {
    background: #1769d2; color: white; border: none;
    cursor: pointer; text-align: center; text-decoration: none;
    display: inline-block;
}
.delete { background: #dc2626; }
.edit { background: #0f766e; margin-bottom: 6px; }
.search-row { display: flex; gap: 10px; align-items: center; }
.search-row input { flex: 1; min-width: 0; }
.search-row button { width: auto; }
.table-wrap { overflow-x: auto; }
table { width: 100%; min-width: 680px; border-collapse: collapse; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
th { background: #f8fafc; }
.low { color: #dc2626; font-weight: bold; }
.good { color: #15803d; font-weight: bold; }
.notice { background: #fff7ed; color: #9a3412; padding: 12px; border-radius: 8px; }
.muted { color: #64748b; font-size: 13px; }
.actions { min-width: 100px; }
.actions form { margin: 0; }
footer { text-align: center; padding: 20px; color: #64748b; }
@media(max-width: 500px) {
    .container { padding: 12px; }
    .card, .panel { padding: 15px; }
}
</style>
</head>
<body>
<header>
    <h1>📦 SmartStock AI</h1>
    <p>Smart inventory and sales management for small shops</p>
</header>

<div class="container">
{% if low_count > 0 %}
<div class="notice">⚠️ Alert: {{ low_count }} product(s) have low stock.</div>
{% endif %}

<div class="cards">
    <div class="card"><h3>Total Products</h3><div class="number">{{ product_count }}</div></div>
    <div class="card"><h3>Total Items in Stock</h3><div class="number">{{ total_qty }}</div></div>
    <div class="card"><h3>Low-Stock Products</h3><div class="number">{{ low_count }}</div></div>
    <div class="card"><h3>Stock Value</h3><div class="number">₹{{ "%.2f"|format(stock_value) }}</div></div>
    <div class="card"><h3>Total Sales Revenue</h3><div class="number">₹{{ "%.2f"|format(total_sales) }}</div></div>
</div>

<div class="panel">
<h2>➕ Add New Product</h2>
<form action="/add" method="POST" class="forms">
    <div><label>Product name</label><input name="name" maxlength="100" required></div>
    <div><label>Quantity</label><input type="number" name="qty" min="0" required></div>
    <div><label>Selling price (₹)</label><input type="number" name="price" min="0" step="0.01" required></div>
    <div><label>&nbsp;</label><button type="submit">Add Product</button></div>
</form>
</div>

<div class="panel">
<h2>🛒 Record a Sale</h2>
<form action="/sale" method="POST" class="forms">
    <div><label>Product name</label><input name="name" placeholder="Enter product name" required></div>
    <div><label>Quantity sold</label><input type="number" name="qty" min="1" required></div>
    <div><label>&nbsp;</label><button type="submit">Record Sale</button></div>
</form>
<p class="muted">Recording a sale reduces stock and saves the transaction.</p>
</div>

<div class="panel">
<h2>📋 Inventory</h2>
<p><a href="/prediction">🤖 View Stock Predictions</a></p>
<form method="GET" action="/" class="search-row">
    <input name="search" placeholder="Search products..." value="{{ search }}">
    <button type="submit">Search</button>
</form>
<div class="table-wrap">
<table>
<thead><tr><th>ID</th><th>Product</th><th>Quantity</th><th>Price</th><th>Status</th><th>Actions</th></tr></thead>
<tbody>
{% for p in products %}
<tr>
    <td>{{ p.id }}</td><td>{{ p.name }}</td><td>{{ p.qty }}</td>
    <td>₹{{ "%.2f"|format(p.price) }}</td>
    <td>{% if p.qty <= 5 %}<span class="low">Low Stock</span>{% else %}<span class="good">In Stock</span>{% endif %}</td>
    <td class="actions">
        <a class="link-button edit" href="/edit/{{ p.id }}">Edit</a>
        <form method="POST" action="/delete/{{ p.id }}" onsubmit="return confirm('Delete this product?')">
            <button class="delete" type="submit">Delete</button>
        </form>
    </td>
</tr>
{% else %}
<tr><td colspan="6">No products found.</td></tr>
{% endfor %}
</tbody>
</table>
</div>
</div>

<div class="panel">
<h2>📊 Today's Sales Report</h2>
<div class="cards">
    <div class="card"><h3>Revenue Today</h3><div class="number">₹{{ "%.2f"|format(today_revenue) }}</div></div>
    <div class="card"><h3>Transactions Today</h3><div class="number">{{ today_transactions }}</div></div>
    <div class="card"><h3>Items Sold Today</h3><div class="number">{{ today_items }}</div></div>
</div>
</div>

<div class="panel">
<h2>💰 Sales History</h2>
<div class="table-wrap">
<table>
<thead><tr><th>Sale ID</th><th>Product</th><th>Quantity</th><th>Unit Price</th><th>Total</th><th>Date and Time</th></tr></thead>
<tbody>
{% for s in sales %}
<tr>
    <td>{{ s.id }}</td>
    <td>{{ s.product_name or "Unknown" }}</td>
    <td>{{ s.qty if s.qty is not none else "Not recorded" }}</td>
    <td>₹{{ "%.2f"|format(s.unit_price or 0) }}</td>
    <td>₹{{ "%.2f"|format(s.total or 0) }}</td>
    <td>{{ s.sale_date or "Not recorded" }}</td>
</tr>
{% else %}
<tr><td colspan="6">No sales recorded yet.</td></tr>
{% endfor %}
</tbody>
</table>
</div>
<p class="muted">Showing the latest 50 sales.</p>
</div>

<footer>SmartStock AI | Inventory Management System</footer>
</div>
</body>
</html>
"""


# =============== HOME PAGE ===============

@app.route("/")
def home():
    search = request.args.get("search", "").strip()
    today = date.today().isoformat()

    with get_db() as conn:
        if search:
            products = conn.execute(
                "SELECT * FROM products WHERE name LIKE ? ORDER BY name",
                (f"%{search}%",)
            ).fetchall()
        else:
            products = conn.execute(
                "SELECT * FROM products ORDER BY name"
            ).fetchall()

        product_count = conn.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        total_qty = conn.execute(
            "SELECT COALESCE(SUM(qty), 0) FROM products"
        ).fetchone()[0]

        low_count = conn.execute(
            "SELECT COUNT(*) FROM products WHERE qty <= 5"
        ).fetchone()[0]

        stock_value = conn.execute(
            "SELECT COALESCE(SUM(qty * price), 0) FROM products"
        ).fetchone()[0]

        total_sales = conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM sales"
        ).fetchone()[0]

        sales = conn.execute("""
            SELECT id, product_name, qty, unit_price, total, sale_date
            FROM sales ORDER BY id DESC LIMIT 50
        """).fetchall()

        today_data = conn.execute("""
            SELECT COALESCE(SUM(total), 0) AS revenue,
                   COUNT(*) AS transactions,
                   COALESCE(SUM(qty), 0) AS items
            FROM sales
            WHERE substr(sale_date, 1, 10) = ?
        """, (today,)).fetchone()

    return render_template_string(
        PAGE, products=products, sales=sales, search=search,
        product_count=product_count, total_qty=total_qty,
        low_count=low_count, stock_value=stock_value,
        total_sales=total_sales,
        today_revenue=today_data["revenue"],
        today_transactions=today_data["transactions"],
        today_items=today_data["items"]
    )


# =============== ADD PRODUCT ===============

@app.route("/add", methods=["POST"])
def add_product():
    name = request.form.get("name", "").strip()

    try:
        qty = int(request.form.get("qty", ""))
        price = round(float(request.form.get("price", "")), 2)
        if not name or len(name) > 100 or qty < 0 or price < 0:
            raise ValueError
    except ValueError:
        return "Enter a valid name, quantity, and price.", 400

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO products (name, qty, price) VALUES (?, ?, ?)",
                (name, qty, price)
            )
    except sqlite3.IntegrityError:
        return "That product name already exists.", 400

    return redirect("/")


# =============== EDIT PRODUCT ===============

@app.route("/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()

    if product is None:
        return "Product not found.", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        try:
            qty = int(request.form.get("qty", ""))
            price = round(float(request.form.get("price", "")), 2)
            if not name or len(name) > 100 or qty < 0 or price < 0:
                raise ValueError
        except ValueError:
            return "Enter valid product details.", 400

        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE products SET name=?, qty=?, price=? WHERE id=?",
                    (name, qty, price, product_id)
                )
        except sqlite3.IntegrityError:
            return "Another product already uses that name.", 400

        return redirect("/")

    return render_template_string("""
    <!DOCTYPE html><html><head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Edit Product</title>
    <style>
    body{font-family:Arial;background:#f3f6fb;padding:25px}
    .box{max-width:450px;margin:30px auto;background:white;padding:25px;border-radius:12px}
    input,button{box-sizing:border-box;width:100%;padding:12px;margin:10px 0;border:1px solid #ccc;border-radius:7px}
    button{background:#1769d2;color:white;border:0}
    </style></head><body><div class="box">
    <h2>✏️ Edit Product</h2>
    <form method="POST">
    <label>Product name</label><input name="name" value="{{ product.name }}" maxlength="100" required>
    <label>Quantity</label><input type="number" name="qty" min="0" value="{{ product.qty }}" required>
    <label>Selling price (₹)</label><input type="number" name="price" min="0" step="0.01" value="{{ product.price }}" required>
    <button type="submit">Save Changes</button>
    </form><a href="/">Back to Dashboard</a>
    </div></body></html>
    """, product=product)


# =============== RECORD SALE ===============

@app.route("/sale", methods=["POST"])
def record_sale():
    name = request.form.get("name", "").strip()

    try:
        qty_sold = int(request.form.get("qty", ""))
        if not name or qty_sold <= 0:
            raise ValueError
    except ValueError:
        return "Enter a valid product name and quantity.", 400

    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE name = ? COLLATE NOCASE",
            (name,)
        ).fetchone()

        if product is None:
            return "Product not found. Check the name.", 404

        if qty_sold > product["qty"]:
            return f"Not enough stock. Available quantity: {product['qty']}.", 400

        total = round(qty_sold * product["price"], 2)
        sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            "UPDATE products SET qty = qty - ? WHERE id = ?",
            (qty_sold, product["id"])
        )

        conn.execute("""
            INSERT INTO sales (product_name, qty, unit_price, total, sale_date)
            VALUES (?, ?, ?, ?, ?)
        """, (product["name"], qty_sold, product["price"], total, sale_date))

    return redirect("/")


# =============== DELETE PRODUCT ===============

@app.route("/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    with get_db() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    return redirect("/")


# =============== STOCK PREDICTION ===============

@app.route("/prediction")
def stock_prediction():
    with get_db() as conn:
        products = conn.execute("""
            SELECT p.id, p.name, p.qty, p.price,
                   COALESCE(SUM(
                       CASE
                           WHEN s.sale_date >= datetime('now', '-7 days')
                           THEN s.qty ELSE 0
                       END
                   ), 0) AS sold_last_7_days
            FROM products p
            LEFT JOIN sales s
                ON LOWER(p.name) = LOWER(s.product_name)
            GROUP BY p.id, p.name, p.qty, p.price
            ORDER BY p.name
        """).fetchall()

    results = []

    for p in products:
        sold = max(0, p["sold_last_7_days"] or 0)
        daily_rate = sold / 7
        days_left = p["qty"] / daily_rate if daily_rate > 0 else None
        target_stock = round(daily_rate * 14)
        restock_qty = max(0, target_stock - p["qty"])

        if p["qty"] <= 5:
            status = "Restock urgently"
        elif days_left is not None and days_left <= 7:
            status = "Restock soon"
        elif sold == 0:
            status = "Not enough recent sales data"
        else:
            status = "Stock looks sufficient"

        results.append({
            "name": p["name"],
            "qty": p["qty"],
            "sold": sold,
            "daily_rate": round(daily_rate, 2),
            "days_left": round(days_left, 1) if days_left is not None else None,
            "restock_qty": restock_qty,
            "status": status
        })

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Stock Predictions - SmartStock AI</title>
    <style>
    body{font-family:Arial;background:#f3f6fb;color:#1e293b;padding:20px}
    .container{max-width:1000px;margin:auto}
    .panel{background:white;padding:20px;border-radius:12px;margin-bottom:20px}
    .table-wrap{overflow-x:auto}
    table{width:100%;min-width:700px;border-collapse:collapse}
    th,td{padding:12px;text-align:left;border-bottom:1px solid #e2e8f0}
    th{background:#f8fafc}
    .alert{color:#dc2626;font-weight:bold}
    .good{color:#15803d;font-weight:bold}
    .note{color:#64748b;font-size:14px}
    </style>
    </head>
    <body><div class="container">
    <div class="panel">
        <h1>🤖 SmartStock AI Predictions</h1>
        <p>Recommendations based on sales recorded during the last 7 days.</p>
        <p class="note">These are estimates, not guaranteed predictions. Products without recent sales history need more data.</p>
        <a href="/">← Back to Dashboard</a>
    </div>
    <div class="panel">
    <h2>📦 Restock Recommendations</h2>
    <div class="table-wrap"><table>
    <thead><tr>
        <th>Product</th><th>Current Stock</th><th>Sold in 7 Days</th>
        <th>Estimated Days Left</th><th>Suggested Restock</th><th>Status</th>
    </tr></thead>
    <tbody>
    {% for p in results %}
    <tr>
        <td>{{ p.name }}</td><td>{{ p.qty }}</td><td>{{ p.sold }}</td>
        <td>{% if p.days_left is not none %}{{ p.days_left }} days{% else %}Unknown{% endif %}</td>
        <td>{{ p.restock_qty }} units</td>
        <td class="{% if p.status in ['Restock urgently', 'Restock soon'] %}alert{% else %}good{% endif %}">{{ p.status }}</td>
    </tr>
    {% else %}
    <tr><td colspan="6">No products found.</td></tr>
    {% endfor %}
    </tbody></table></div>
    </div></div></body></html>
    """, results=results)


# =============== START APPLICATION ===============

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
