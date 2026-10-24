import sqlite3

conn = sqlite3.connect("enterprise.db")
cursor = conn.cursor()

# Create Tables
cursor.executescript("""
    CREATE TABLE Customers (customer_id INTEGER PRIMARY KEY, name TEXT, segment TEXT, signup_date DATE);
    CREATE TABLE Products (product_id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
    CREATE TABLE Orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER, quantity INTEGER, order_date DATE,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id),
        FOREIGN KEY(product_id) REFERENCES Products(product_id));
""")

# Insert Dummy Data
cursor.executescript("""
    INSERT INTO Customers VALUES (1, 'Acme Corp', 'Enterprise', '2025-01-15');
    INSERT INTO Customers VALUES (2, 'Global Tech', 'Mid-Market', '2025-03-22');
    INSERT INTO Customers VALUES (3, 'Local Bakery', 'Small Business', '2025-06-10');
    INSERT INTO Products VALUES (101, 'SaaS License', 'Software', 1200.00);
    INSERT INTO Products VALUES (102, 'Consulting Hours', 'Services', 250.00);
    INSERT INTO Products VALUES (103, 'Server Maintenance', 'IT', 500.00);
    INSERT INTO Orders VALUES (1001, 1, 101, 5, '2026-08-01');
    INSERT INTO Orders VALUES (1002, 2, 102, 10, '2026-08-15');
    INSERT INTO Orders VALUES (1003, 1, 103, 2, '2026-08-20');
""")

conn.commit()
conn.close()
print("Database enterprise.db created successfully!")