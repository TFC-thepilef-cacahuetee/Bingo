# Esta clase gestiona la conexión a la base de datos PostgreSQL.
import psycopg2
from flask import current_app

def get_db_connection():
    config = current_app.config
    conn = psycopg2.connect(
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        host=config['DB_HOST'],
        port=config['DB_PORT'],
        dbname=config['DB_NAME']
    )
    return conn
