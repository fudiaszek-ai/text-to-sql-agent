import sqlite3
import os

DB_NAME = "company.db"

def build_database():
    # Usuwamy starą bazę, jeśli istnieje, aby zawsze startować z czystym stanem
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Usunięto istniejącą bazę: {DB_NAME}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Włączamy obsługę kluczy obcych w SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabela Klienci
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        segment TEXT NOT NULL,
        created_at DATE NOT NULL
    );
    """)

    # 2. Tabela Produkty
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    );
    """)

    # 3. Tabela Zamówienia
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        order_date DATE NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (product_id) REFERENCES products (product_id)
    );
    """)

    # --- Wstawianie danych testowych ---

    customers_data = [
        ("Jan Kowalski", "Warszawa", "B2C", "2024-01-15"),
        ("Anna Nowak", "Kraków", "B2C", "2024-02-10"),
        ("TechCorp Sp. z o.o.", "Warszawa", "B2B", "2023-11-01"),
        ("Piotr Wiśniewski", "Wrocław", "B2C", "2024-03-05"),
        ("DataSoft Corp", "Poznań", "B2B", "2023-08-20")
    ]
    cursor.executemany(
        "INSERT INTO customers (name, city, segment, created_at) VALUES (?, ?, ?, ?);",
        customers_data
    )

    products_data = [
        ("Laptop Pro 15", "Elektronika", 4500.00, 25),
        ("Mysz Bezprzewodowa", "Akcesoria", 120.00, 150),
        ("Klawiatura Mechaniczna", "Akcesoria", 350.00, 80),
        ("Monitor 4K 27", "Elektronika", 1800.00, 15),
        ("Fotel Biurowy Ergonomiczny", "Meble", 950.00, 10)
    ]
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock_quantity) VALUES (?, ?, ?, ?);",
        products_data
    )

    orders_data = [
        (1, 1, 1, "2024-04-01", "COMPLETED"),
        (1, 2, 2, "2024-04-01", "COMPLETED"),
        (2, 4, 1, "2024-04-02", "COMPLETED"),
        (3, 1, 5, "2024-04-03", "COMPLETED"),
        (3, 3, 5, "2024-04-03", "COMPLETED"),
        (4, 5, 1, "2024-04-05", "CANCELLED"),
        (5, 2, 10, "2024-04-06", "COMPLETED"),
        (2, 3, 1, "2024-04-07", "PENDING")
    ]
    cursor.executemany(
        "INSERT INTO orders (customer_id, product_id, quantity, order_date, status) VALUES (?, ?, ?, ?, ?);",
        orders_data
    )

    conn.commit()
    conn.close()
    print("✓ Baza danych company.db została pomyślnie utworzona i zasilona danymi!")

if __name__ == "__main__":
    build_database()