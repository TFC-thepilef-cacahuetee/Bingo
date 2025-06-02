import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
from config import SECRET_KEY
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from sockets.handlers import register_socket_events
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY
socketio = SocketIO(app, async_mode='eventlet')

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)

# Registrar eventos de Socket.IO
register_socket_events(socketio)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
