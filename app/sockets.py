# Este archivo inicializa la instancia de SocketIO para la aplicación.
from flask_socketio import SocketIO

socketio = SocketIO(async_mode='eventlet', cors_allowed_origins="*")
