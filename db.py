import psycopg2
from config import USER, PASSWORD, HOST, PORT, DBNAME

def get_db_connection():
    return psycopg2.connect(
        user=USER, 
        password=PASSWORD, 
        host=HOST, 
        port=PORT, 
        dbname=DBNAME
    )

def close_db(cursor, connection):
    if cursor:
        cursor.close()
    if connection:
        connection.close()