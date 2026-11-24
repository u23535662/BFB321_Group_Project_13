import pymysql
from flask import current_app, g
from config import get_config

def _cfg(key: str, default=None):
    """Read a setting from Flask's current_app.config, or fall back to get_config()."""
    if current_app:
        return current_app.config.get(key, default)
    return getattr(get_config(), key, default)


def connect():
    db_name = _cfg("DB_NAME", "stock_db")
    options = dict(
        host=_cfg("DB_HOST", "127.0.0.1"),
        port=int(_cfg("DB_PORT", 3306)),
        user=_cfg("DB_USER", "root"),
        password=_cfg("DB_PASSWORD", ""),
        charset=_cfg("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=int(_cfg("DB_CONNECT_TIMEOUT", 15)),
    )

    conn= pymysql.connect(**options)
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        cursor.execute(f"USE `{db_name}`;")
    return conn

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
    try:
        with db.cursor() as cur:
            cur.execute(sql, params or ())
            new_id = cur.lastrowid
        db.commit()
        return new_id
    except Exception:
        db.rollback()
        raise