# Esta clase contiene funciones para ejecutar consultas SQL específicas.
from .connection import get_db_connection

def get_user_by_username_and_dni(username, dni_hash):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM usuarios WHERE username = %s AND dni = %s", (username, dni_hash))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def user_exists(username, dni_hash):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM usuarios WHERE username = %s OR dni = %s", (username, dni_hash))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists

def insert_user(username, dni_hash, mayor_edad):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO usuarios (username, dni, mayor_edad) VALUES (%s, %s, %s)",
        (username, dni_hash, mayor_edad)
    )
    conn.commit()
    cur.close()
    conn.close()

def insert_sala(codigo_sala, creador_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO salas (id, creador_id, estado) VALUES (%s, %s, %s)",
        (codigo_sala, creador_id, 'esperando')
    )
    conn.commit()
    cur.close()
    conn.close()
