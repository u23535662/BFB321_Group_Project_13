import os
from db import connect

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "stock_db"


def read_statements(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, encoding="utf-8") as f:
        lines = [
            ln for ln in f.read().splitlines() if not ln.strip().startswith("--")
        ]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def main():
    conn = connect()
    try:
        with conn.cursor() as cur:
            print(f"Dropping database `{DB_NAME}` if it exists...")
            cur.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")

            print(f"Creating database `{DB_NAME}`...")
            cur.execute(
                f"CREATE DATABASE `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
            cur.execute(f"USE `{DB_NAME}`")

            print("Creating tables from schema.sql ...")
            for stmt in read_statements("schema.sql"):
                cur.execute(stmt)

            print("Loading sample data from seed.sql ...")
            for stmt in read_statements("seed.sql"):
                cur.execute(stmt)

        conn.commit()
        print("Database recreated and initialized successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()