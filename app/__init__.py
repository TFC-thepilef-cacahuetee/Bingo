# Esta fábrica crea y configura la aplicación Flask, inicializa extensiones y registra los blueprints de rutas.
from flask import Flask
from flask_socketio import SocketIO
from .config import Config

socketio = SocketIO(async_mode='eventlet')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    socketio.init_app(app)

    # Importar y registrar blueprints de rutas HTTP (no de socketio)
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.salas import salas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(salas_bp)

    # NOTA: No registrar blueprint de socketio (los eventos están en socketio_events.py y registrados en socketio directamente)

    return app
