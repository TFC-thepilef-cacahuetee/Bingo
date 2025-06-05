from flask_socketio import join_room, leave_room, emit
import threading
from flask import request
from db import get_db_connection, close_db
from utils.bingo import (
    numeros_emitidos_por_sala,
    generar_carton_bingo_personalizado,
    emitir_numeros_periodicos,
    validar_bingo,
    guardar_sala_y_numeros
)

# Variables globales para salas y control de hilos
salas = {}
hilos_emitir = {}  # <--- Añade este diccionario para controlar los hilos
# Variable global para controlar la emisión por sala
partida_activa_por_sala = {}
linea_cantada_por_sala = {}

def register_socket_events(socketio):
    @socketio.on('unirse_sala')
    def unirse_sala(data):
        codigo_sala = data['codigo_sala']
        username = data['username'].strip().lower()

        if codigo_sala not in salas:
            salas[codigo_sala] = {'jugadores': [], 'listos': {}}

        if len(salas[codigo_sala]['jugadores']) >= 10:
            emit('sala_llena', {'mensaje': 'La sala ya tiene 10 jugadores.'})
            return

        if username not in salas[codigo_sala]['jugadores']:
            salas[codigo_sala]['jugadores'].append(username)
            salas[codigo_sala]['listos'][username] = False

            # 🔽 NUEVO: Insertar jugador en la tabla jugadores_sala
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Obtener el ID del usuario desde su username
                cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
                resultado = cursor.fetchone()

                if resultado:
                    usuario_id = resultado[0]

                    cursor.execute("""
                        INSERT INTO jugadores_sala (sala_id, usuario_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (codigo_sala, usuario_id))

                    conn.commit()
                else:
                    print(f"⚠️ No se encontró usuario con username: {username}")

            except Exception as e:
                print(f"❌ Error al insertar en jugadores_sala: {e}")
            finally:
                close_db(cursor, conn)

        join_room(codigo_sala)
        emit_actualizacion_jugadores(codigo_sala)

    @socketio.on('jugador_listo')
    def jugador_listo(data):
        codigo_sala = data['codigo_sala']
        username = data['username'].strip().lower()

        if codigo_sala in salas:
            if username not in salas[codigo_sala]['jugadores']:
                salas[codigo_sala]['jugadores'].append(username)
            salas[codigo_sala]['listos'][username] = True

            emit_actualizacion_jugadores(codigo_sala)

            jugadores = salas[codigo_sala]['jugadores']
            listos_dict = salas[codigo_sala]['listos']

            # Verifica que todos los jugadores estén listos
            faltantes = [j for j in jugadores if not listos_dict.get(j, False)]
            print(f"Faltan por estar listos: {faltantes}")

            if len(faltantes) == 0:
                cartones_por_jugador = {}
                for jugador in jugadores:
                    carton = generar_carton_bingo_personalizado()
                    cartones_por_jugador[jugador] = carton

                emit('partida_iniciada', {'cartones': cartones_por_jugador}, room=codigo_sala)

                # --- Cambia aquí: solo lanza un hilo por sala y pasa salas como argumento ---
                if codigo_sala not in hilos_emitir or not hilos_emitir[codigo_sala].is_alive():
                    thread = threading.Thread(target=emitir_numeros_periodicos, args=(codigo_sala, socketio, salas))
                    hilos_emitir[codigo_sala] = thread
                    thread.start()

    @socketio.on('salir_sala')
    def salir_sala(data):
        codigo_sala = data['codigo_sala']
        username = data['username'].strip().lower()

        if codigo_sala in salas:
            if username in salas[codigo_sala]['jugadores']:
                salas[codigo_sala]['jugadores'].remove(username)
                salas[codigo_sala]['listos'].pop(username, None)
                leave_room(codigo_sala)
                emit_actualizacion_jugadores(codigo_sala)

    @socketio.on('iniciar_partida')
    def iniciar_partida(data):
        codigo_sala = data['codigo_sala']
        emit('partida_iniciada', room=codigo_sala)

    @socketio.on('numero_marcado')
    def numero_marcado(data):
        codigo_sala = data.get('codigo_sala')
        username = data.get('username', '').strip().lower()
        numero = data.get('numero')
        marcado = data.get('marcado')

        socketio.emit('numero_marcado', {
            'codigo_sala': codigo_sala,
            'username': username,
            'numero': numero,
            'marcado': marcado
        }, room=codigo_sala)

    # Supongamos que ya agregaste esta estructura arriba del todo:
# linea_cantada_por_sala = {}

@socketio.on('linea_cantada')
def linea_cantada(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username', '').strip().lower()
    emit('linea_cantada', {'username': username}, room=codigo_sala)


@socketio.on('bingo_cantado')
def bingo_cantado(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username', '').strip().lower()
    carton_jugador = data.get('carton')

    from utils.bingo import numeros_emitidos_por_sala, guardar_sala_y_numeros

    bingo_valido = validar_bingo(carton_jugador)

    if bingo_valido:
        emit('anunciar_ganador', {'ganador': username}, room=codigo_sala)

        if codigo_sala in salas:
            for jugador in salas[codigo_sala]['listos']:
                salas[codigo_sala]['listos'][jugador] = False
            emit_actualizacion_jugadores(codigo_sala)
    else:
        emit('bingo_invalido', {'msg': 'Bingo no válido'}, room=request.sid)


@socketio.on('bingo_completado')
def bingo_completado(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username')
    tipo = data.get('tipo')  # 'bingo' o 'linea'
    cantidad = data.get('cantidad', 1)

    # 🟡 VALIDAR si ya se cantó línea
    if tipo == 'linea':
        if linea_cantada_por_sala.get(codigo_sala, False):
            emit('intento_invalido', {
                'username': username,
                'tipo': tipo,
                'motivo': 'Ya se cantó la línea en esta sala.'
            }, to=codigo_sala)
            return
        else:
            linea_cantada_por_sala[codigo_sala] = True

    # 🔴 Si es bingo, desactivar emisión de números y guardar en BD
    if tipo == 'bingo':
        partida_activa_por_sala[codigo_sala] = False

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            user_record = cursor.fetchone()

            if not user_record:
                emit('error', {'msg': 'Usuario no encontrado en base de datos.'}, room=request.sid)
                return

            user_id = user_record[0]

            cursor.execute(
                "UPDATE salas SET ganador_id = %s WHERE id = %s",
                (user_id, codigo_sala)
            )
            conn.commit()

            print(f"Ganador guardado en sala {codigo_sala}: usuario {username} (id {user_id})")

        except Exception as e:
            print(f"Error guardando ganador en sala: {e}")
            emit('error', {'msg': 'Error al guardar ganador en la base de datos.'}, room=request.sid)

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # ✅ Notificar a todos el resultado (línea o bingo)
    emit('bingo_completado', {
        'tipo': tipo,
        'username': username,
        'cantidad': cantidad
    }, to=codigo_sala)


# Función auxiliar usada varias veces
def emit_actualizacion_jugadores(codigo_sala):
    emit('actualizar_jugadores_listos', {
        'jugadores': salas[codigo_sala]['jugadores'],
        'listos': salas[codigo_sala]['listos']
    }, room=codigo_sala)
