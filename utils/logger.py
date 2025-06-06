from db import get_db_connection, close_db

def log_event(nivel, mensaje):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO logs (nivel, mensaje) VALUES (%s, %s)",
            (nivel, mensaje)
        )
        conn.commit()
    except Exception as e:
        # Si el logging falla, no hacemos nada para evitar loops
        pass
    finally:
        try:
            close_db(cursor, conn)
        except:
            pass
