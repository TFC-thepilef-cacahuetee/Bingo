# Este módulo registra los eventos de SocketIO para la gestión de salas y juego en tiempo real.
from flask_socketio import emit, join_room, leave_room
import threading
from ..utils.bingo import generar_carton_bingo
from ..utils.threading import emitir_numeros_periodicos
from ..sockets import socketio 

# Estructura en memoria para salas y jugadores
salas = {}

def emit_actualizacion_jugadores(codigo_sala):
    emit('actualizar_jugadores_listos', {
        'jugadores': salas[codigo_sala]['jugadores'],
        'listos': salas[codigo_sala]['listos']
    }, room=codigo_sala)

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
def handle_jugador_listo(data):
    codigo_sala = data['codigo_sala']
    username = data['username'].strip().lower()
    if codigo_sala in salas:
        if username not in salas[codigo_sala]['jugadores']:
            salas[codigo_sala]['jugadores'].append(username)
        salas[codigo_sala]['listos'][username] = True
        emit_actualizacion_jugadores(codigo_sala)
        jugadores = salas[codigo_sala]['jugadores']
        listos_dict = salas[codigo_sala]['listos']
        faltantes = [j for j in jugadores if not listos_dict.get(j, False)]
        if len(faltantes) == 0:
            cartones_por_jugador = {jugador: generar_carton_bingo() for jugador in jugadores}
            emit('partida_iniciada', {'cartones': cartones_por_jugador}, room=codigo_sala)
            thread = threading.Thread(target=emitir_numeros_periodicos, args=(codigo_sala,))
            thread.start()

@socketio.on('salir_sala')
def handle_salir_sala(data):
    codigo_sala = data['codigo_sala']
    username = data['username'].strip().lower()
    if codigo_sala in salas:
        if username in salas[codigo_sala]['jugadores']:
            salas[codigo_sala]['jugadores'].remove(username)
            salas[codigo_sala]['listos'].pop(username, None)
            leave_room(codigo_sala)
            emit_actualizacion_jugadores(codigo_sala)

@socketio.on('iniciar_partida')
def handle_iniciar_partida(data):
    codigo_sala = data['codigo_sala']
    emit('partida_iniciada', room=codigo_sala)

@socketio.on('numero_marcado')
def handle_numero_marcado(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username', '').strip().lower()
    numero = data.get('numero')
    marcado = data.get('marcado')
    emit('numero_marcado', {
        'codigo_sala': codigo_sala,
        'username': username,
        'numero': numero,
        'marcado': marcado
    }, room=codigo_sala)

@socketio.on('linea_cantada')
def handle_linea_cantada(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username', '').strip().lower()
    emit('linea_cantada', {'username': username}, room=codigo_sala)
