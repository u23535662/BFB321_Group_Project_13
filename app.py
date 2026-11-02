import os
from dotenv import load_dotenv
import pymysql

load_dotenv()

# 1. Defined with lowercase 'c'
connection = pymysql.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    cursorclass=pymysql.cursors.DictCursor,
)

with connection.cursor() as cursor:
    query = "SELECT * FROM Sale"
    cursor.execute(query)
    result = cursor.fetchall()
    print(result)