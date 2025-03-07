import psycopg2
import psycopg2.extras  # Import extras
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Connect to the database
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")

    # Create a cursor with DictCursor
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Fetch and print users
    cursor.execute('SELECT * FROM users;')
    for record in cursor.fetchall():
        print(record['name'], record['role'])  # Now this will work!

except Exception as e:
    print(f"Failed to connect: {e}")

finally:
    if connection:
        cursor.close()
        connection.close()
