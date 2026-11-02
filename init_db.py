import os
import sys
from db import BASE_DIR, connect

# Children tables before parent tables to respect foreign key constraints
TABLES_IN_DROP_ORDER = [
    "Sale", 
    "Job_Product", 
    "Inventory_Order", 
    "Product_Supplier", 
    "Job", 
    "Supplier", 
    "Product"
]

def read_statements(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]

def main(reset=False):
    conn = connect()
    try:
        with conn.cursor() as cur:
            if reset:
                print("Dropping existing tables...")
                for table in TABLES_IN_DROP_ORDER:
                    cur.execute(f"DROP TABLE IF EXISTS {table}")

            print("Creating tables from inventory_schema.sql ...")
            for stmt in read_statements("inventory_schema.sql"):
                cur.execute(stmt)

            cur.execute("SELECT COUNT(*) AS n FROM Product")
            if cur.fetchone()["n"] == 0:
                print("Loading sample data from seed.sql ...")
                for stmt in read_statements("seed.sql"):
                    cur.execute(stmt)
            else:
                print("Products already exist - sample data NOT loaded")

        # Commit transaction successfully
        conn.commit()
        print("Database initialized successfully.")
        
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main(reset="--reset" in sys.argv)