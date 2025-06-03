from flask_socketio import join_room, leave_room, emit
import threading
from flask import request
from datetime import datetime
from data.numeros_salas import numeros_emitidos_por_sala
from utils.bingo import (
    generar_carton_bingo_personalizado, emitir_numeros_periodicos,
    validar_bingo, guardar_sala_y_numeros
)

# Variables globales para salas y control de hilos
salas = {}
hilos_emitir = {}  # <--- Añade este diccionario para controlar los hilos

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
            # 💾 Guardar los números emitidos en la BD
            if codigo_sala in numeros_emitidos_por_sala:
                guardar_sala_y_numeros(codigo_sala, numeros_emitidos_por_sala[codigo_sala])

            # 📣 Anunciar ganador
            emit('anunciar_ganador', {'ganador': username}, room=codigo_sala)

            # 🔁 Resetear estados de jugadores
            if codigo_sala in salas:
                for jugador in salas[codigo_sala]['listos']:
                    salas[codigo_sala]['listos'][jugador] = False
                emit_actualizacion_jugadores(codigo_sala)
        else:
            emit('bingo_invalido', {'msg': 'Bingo no válido'}, room=request.sid)

    @socketio.on('bingo_completado')
    def bingo_completado(data):
        codigo_sala = data['codigo_sala']
        username = data['username']
        valido = data.get('valido', False)

        if valido:
            emit('ganador_bingo', {'username': username}, to=codigo_sala)

# Función auxiliar usada varias veces
def emit_actualizacion_jugadores(codigo_sala):
    emit('actualizar_jugadores_listos', {
        'jugadores': salas[codigo_sala]['jugadores'],
        'listos': salas[codigo_sala]['listos']
    }, room=codigo_sala)
