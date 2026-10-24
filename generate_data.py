import sqlite3
import random
from datetime import datetime, timedelta

def generate_enterprise_data():
    conn = sqlite3.connect("enterprise.db")
    cursor = conn.cursor()

    # Recreate tables to ensure clean slate
    cursor.executescript("""
        DROP TABLE IF EXISTS Orders;
        DROP TABLE IF EXISTS Products;
        DROP TABLE IF EXISTS Customers;

        CREATE TABLE Customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            segment TEXT NOT NULL,
            signup_date DATE NOT NULL
        );

        CREATE TABLE Products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE Orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            order_date DATE NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES Customers(customer_id),
            FOREIGN KEY(product_id) REFERENCES Products(product_id)
        );
    """)

    random.seed(42)

    # 1. Seed Diverse Customers
    company_prefixes = [
        "Acme", "Global", "Apex", "Nexus", "Vertex", "Quantum", "CloudScale", "Omega",
        "Vanguard", "Horizon", "Pinnacle", "Synergy", "Beacon", "Starlight", "Crestview",
        "Frontier", "Insight", "Dynamic", "Velocity", "Summit", "Sterling", "Paramount"
    ]
    company_suffixes = [
        "Corp", "Technologies", "Logistics", "Enterprises", "Industries", "Solutions",
        "Networks", "Labs", "Systems", "Consulting", "Partners", "Holdings", "Group"
    ]
    segments = ["Enterprise", "Mid-Market", "Small Business"]
    segment_weights = [0.25, 0.45, 0.30]

    customers = []
    # Include original baseline companies
    customers.append((1, "Acme Corp", "Enterprise", "2025-01-15"))
    customers.append((2, "Global Tech", "Mid-Market", "2025-03-22"))
    customers.append((3, "Local Bakery", "Small Business", "2025-06-10"))

    used_names = {"Acme Corp", "Global Tech", "Local Bakery"}
    cust_id = 4
    start_date = datetime(2024, 1, 1)

    while len(customers) < 250:
        name = f"{random.choice(company_prefixes)} {random.choice(company_suffixes)}"
        if name in used_names:
            name = f"{name} {random.randint(10, 99)}"
        used_names.add(name)
        segment = random.choices(segments, weights=segment_weights)[0]
        days_offset = random.randint(0, 500)
        signup = (start_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")
        customers.append((cust_id, name, segment, signup))
        cust_id += 1

    cursor.executemany("INSERT INTO Customers VALUES (?, ?, ?, ?)", customers)

    # 2. Seed Products across categories
    products = [
        (101, "SaaS Enterprise Suite", "Software", 2400.00),
        (102, "Cloud Analytics License", "Software", 1200.00),
        (103, "ERP Core Platform", "Software", 4500.00),
        (104, "CRM Pro Subscription", "Software", 850.00),
        (105, "Security Compliance Suite", "Software", 1600.00),
        (106, "Executive Consulting", "Services", 350.00),
        (107, "Architecture Review", "Services", 275.00),
        (108, "Data Migration Consulting", "Services", 220.00),
        (109, "Technical Training Workshop", "Services", 500.00),
        (110, "Managed IT Operations", "IT Infrastructure", 1500.00),
        (111, "Cloud Server Maintenance", "IT Infrastructure", 750.00),
        (112, "Disaster Recovery Node", "IT Infrastructure", 1100.00),
        (113, "Network Firewall Appliance", "Cybersecurity", 3200.00),
        (114, "Endpoint Protection License", "Cybersecurity", 45.00),
        (115, "Threat Intelligence Feed", "Cybersecurity", 800.00),
        (116, "High-Performance Compute Node", "Cloud Computing", 1850.00),
        (117, "Object Storage Capacity (TB)", "Cloud Computing", 120.00),
        (118, "API Gateway Instance", "Cloud Computing", 650.00),
    ]
    cursor.executemany("INSERT INTO Products VALUES (?, ?, ?, ?)", products)

    # 3. Seed 10,000 Synthetic Orders
    orders = []
    order_start = datetime(2025, 1, 1)
    product_ids = [p[0] for p in products]
    customer_ids = [c[0] for c in customers]

    for order_id in range(1001, 11001):
        c_id = random.choice(customer_ids)
        p_id = random.choice(product_ids)
        qty = random.randint(1, 15)
        # Give Enterprise customers higher volume
        if c_id <= 3:
            qty = random.randint(2, 25)
        days = random.randint(0, 600)
        order_date = (order_start + timedelta(days=days)).strftime("%Y-%m-%d")
        orders.append((order_id, c_id, p_id, qty, order_date))

    cursor.executemany("INSERT INTO Orders VALUES (?, ?, ?, ?, ?)", orders)

    conn.commit()
    
    # Validation counts
    num_cust = cursor.execute("SELECT COUNT(*) FROM Customers").fetchone()[0]
    num_prod = cursor.execute("SELECT COUNT(*) FROM Products").fetchone()[0]
    num_ord = cursor.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
    
    conn.close()
    print(f"Successfully scaled enterprise.db:")
    print(f" - Customers: {num_cust}")
    print(f" - Products:  {num_prod}")
    print(f" - Orders:    {num_ord} (10,000 synthetic transactional records)")

if __name__ == "__main__":
    generate_enterprise_data()
