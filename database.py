import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

# Get DB credentials from environment variables
hostname = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
database = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
pwd = os.getenv("DB_PASSWORD")
conn = None
try:
  with psycopg2.connect(
                  host = hostname,
                  dbname = database,
                  user = user,
                  password = pwd,
                  port = port) as conn:
  
   with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

    #example of inserting 
    insert_script = '''INSERT INTO USERS (name, email, password, role) VALUES (%s,%s,%s,%s)'''
    insert_value = ('Jeeni','abc4@gmail.com','abc@123','buyer')
    #cur.execute(insert_script,insert_value)

    #Fetch and print users
    cur.execute('SELECT * FROM users;')
    for record in cur.fetchall():
      print(record['name'],record['role'])
    
except Exception as error:
  print(error)
finally:
  if conn is not None:
    conn.close()