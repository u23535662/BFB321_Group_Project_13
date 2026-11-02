import os
import ssl
import pymysql
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def connect(use_db=True):
    """
    Establishes a secure connection to the Aiven MySQL server,
    bypassing self-signed certificate verification.
    """
    db_name = os.getenv("DB_NAME", "inventory_db") if use_db else None
    port = int(os.getenv("DB_PORT", 3306))

    # Create an SSL context that ignores self-signed certificate errors
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=port,
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        ssl=ssl_context
    )