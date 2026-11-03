import os
import pymysql
from dotenv import load_dotenv
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def connect():
    options = dict(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3307")),
        user=os.getenv("DB_USER", "avnadmin"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "inventory"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=15,
    )
    return pymysql.connect(**options)

def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db

def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)

def query_all(sql, params=None):
    with get_db().cursor() as cur:
        cur.execute(sql, params or ())
    return cur.fetchall()

def query_one(sql, params=None):
    with get_db().cursor() as cur:
        cur.execute(sql, params or ())
    return cur.fetchone()

def execute(sql, params=None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        new_id = cur.lastrowid
    db.commit()
    return new_id
