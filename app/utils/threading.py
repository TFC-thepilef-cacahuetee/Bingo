# Esta clase implementa la lógica para emitir números de bingo periódicamente a través de SocketIO.
import random
import time
from ..sockets import socketio

numeros_emitidos_por_sala = {}

def emitir_numeros_periodicos(codigo_sala):
    numeros_emitidos_por_sala[codigo_sala] = set()
    todos_numeros = set(range(1, 100))
    while True:
        disponibles = list(todos_numeros - numeros_emitidos_por_sala[codigo_sala])
        if not disponibles:
            socketio.emit('fin_partida', room=codigo_sala)
            break
        numero = random.choice(disponibles)
        numeros_emitidos_por_sala[codigo_sala].add(numero)
        socketio.emit('numero_nuevo', {'numero': numero}, room=codigo_sala)
        time.sleep(3)
