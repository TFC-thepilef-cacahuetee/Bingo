import random
import time
from datetime import datetime
from db import get_db_connection, close_db
from sockets.handlers import partida_activa_por_sala

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

def emitir_numeros_periodicos(codigo_sala, socketio, salas):
    try:
        numeros_emitidos_por_sala[codigo_sala] = []
        todos_numeros = set(range(1, 100))

        partida_activa_por_sala[codigo_sala] = True

        while codigo_sala in salas and partida_activa_por_sala.get(codigo_sala, True):
            if not salas[codigo_sala]['jugadores']:
                print(f"Parando emisión para sala {codigo_sala} (sin jugadores)")
                break

            emitidos = set(n for n, _ in numeros_emitidos_por_sala[codigo_sala])
            disponibles = list(todos_numeros - emitidos)

            if not disponibles:
                print(f"Números agotados para sala {codigo_sala}. Fin de partida.")
                socketio.emit('fin_partida', room=codigo_sala)
                break

            numero = random.choice(disponibles)
            timestamp = datetime.utcnow()
            numeros_emitidos_por_sala[codigo_sala].append((numero, timestamp))

            socketio.emit('numero_nuevo', {'numero': numero}, room=codigo_sala)
            time.sleep(3)

    except Exception as e:
        print(f"❌ Error en emisión periódica de {codigo_sala}: {e}")
    finally:
        try:
            guardar_sala_y_numeros(codigo_sala, numeros_emitidos_por_sala[codigo_sala])
        except Exception as e:
            print(f"❌ Error guardando números emitidos: {e}")
        if codigo_sala in numeros_emitidos_por_sala:
            del numeros_emitidos_por_sala[codigo_sala]

def guardar_sala_y_numeros(sala_id, lista_numeros):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for num in lista_numeros:
            cursor.execute("""
                INSERT INTO numeros_ll (sala_id, numero)
                VALUES (%s, %s)
            """, (sala_id, num))

        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error al guardar números para la sala {sala_id}: {e}")
        return False
    finally:
        close_db(cursor, conn)

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
