from flask import Flask
from .config import Config
from .sockets import socketio

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    socketio.init_app(app)  # Inicializa socketio con la app

    # Registrar blueprints HTTP normales
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.salas import salas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(salas_bp)

    # Importar eventos SocketIO tras inicializar para evitar importación circular
    from .routes import socketio_events

    return app
