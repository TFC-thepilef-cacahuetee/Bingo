import random
import threading
import time
from datetime import datetime
from flask import session, redirect, url_for, flash
from db import get_db_connection, close_db

# 🔁 Variable global para almacenar los números emitidos por sala
numeros_emitidos_por_sala = {}

def generar_carton_bingo_personalizado():
    rangos = {
        'B': range(1, 20),
        'I': range(20, 40),
        'N': range(40, 60),
        'G': range(60, 80),
        'O': range(80, 100)
    }

    columnas = {}
    for letra, rango in rangos.items():
        columnas[letra] = random.sample(rango, 5)

    carton = []
    for i in range(5):
        fila = [columnas['B'][i], columnas['I'][i], columnas['N'][i], columnas['G'][i], columnas['O'][i]]
        carton.append(fila)

    posiciones = [(i, j) for i in range(5) for j in range(5)]
    blancos = random.sample(posiciones, 8)  # 8 espacios en blanco
    for i, j in blancos:
        carton[i][j] = ""

    return carton

def emitir_numeros_periodicos(codigo_sala, socketio):
    numeros_emitidos_por_sala[codigo_sala] = []
    todos_numeros = set(range(1, 100))

    while True:
        emitidos = set(n for n, _ in numeros_emitidos_por_sala[codigo_sala])
        disponibles = list(todos_numeros - emitidos)

        if not disponibles:
            guardar_sala_y_numeros(codigo_sala, numeros_emitidos_por_sala[codigo_sala])
            socketio.emit('fin_partida', room=codigo_sala)
            break

        numero = random.choice(disponibles)
        timestamp = datetime.utcnow()
        numeros_emitidos_por_sala[codigo_sala].append((numero, timestamp))

        socketio.emit('numero_nuevo', {'numero': numero}, room=codigo_sala)

        time.sleep(3)

def guardar_sala_y_numeros(codigo_sala, numeros_con_tiempo):
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO salas (id, creador_id, estado, fecha_creacion, ganador_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (codigo_sala, None, 'finalizada', datetime.utcnow(), None)
        )

        datos = [
            (codigo_sala, codigo_sala, numero, llamado_en)
            for numero, llamado_en in numeros_con_tiempo
        ]
        insert_query = """
            INSERT INTO numeros_llamados (partida_id, sala_id, numero, llamado_en)
            VALUES (%s, %s, %s, %s)
        """
        cursor.executemany(insert_query, datos)

        connection.commit()
        return True

    except Exception as e:
        print(f"❌ Error al guardar en la BD: {e}")
        flash("⚠️ Error al guardar la sala o los números.")
        return False

    finally:
        close_db(cursor, connection)

def validar_bingo(carton):
    # Validación horizontal
    for fila in carton:
        if all(casilla == "X" for casilla in fila):
            return True

    # Validación vertical
    for col in range(5):
        if all(fila[col] == "X" for fila in carton):
            return True

    # Diagonales
    if all(carton[i][i] == "X" for i in range(5)):
        return True
    if all(carton[i][4 - i] == "X" for i in range(5)):
        return True

    return False
