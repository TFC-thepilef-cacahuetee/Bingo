# Este es el punto de entrada de la aplicación. Crea la app y la corre con SocketIO.
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
