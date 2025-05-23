# En esta parte se pone todo lo que queramos importar para luego usarlo en la aplicacion
# render_template es para renderizar el html desde la carpeta templates que la usa por defecto
# Flask es el framework que estamos usando para crear la aplicacion web
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string
import random


# Creamos la app Flask y le pasamos __name__ para que pueda encontrar rutas de archivos como templates y estáticos
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')


# Definimos la ruta de la aplicacion, en este caso la ruta principal que es la que se carga al abrir la app
@app.route('/')
def indexRuta():
    return render_template('index.html')

# Esto es para hacer la conexion con la base de datos
import psycopg2
from dotenv import load_dotenv
import os
numeros_usados_global = set()

# Load environment variables from .env
load_dotenv()

# Esto es para que funcione el flash y es lo que hace que se guarde en la cookie la session
app.secret_key = os.getenv('SECRET_KEY')


# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Connect to the database
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")
    
    # Create a cursor to execute SQL queries
    cursor = connection.cursor()
    
    # Example query
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("Current Time:", result)

    # Close the cursor and connection
    cursor.close()
    connection.close()
    print("Connection closed.")

except Exception as e:
    print(f"Failed to connect: {e}")

# Definimos todas las rutas que queremos usar en la aplicacion, en este caso son las rutas de los diferentes html que tenemos en la carpeta templates
@app.route('/login', methods=['GET', 'POST'])
def loginRuta():
    if request.method == 'POST':
        username = request.form.get('username')
        dni = request.form.get('dni')

        try:
            connection = psycopg2.connect(
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME
            )
            cursor = connection.cursor()

            # Validar que el nombre de usuario y DNI coincidan con un registro en la base de datos
            cursor.execute("SELECT id, username FROM usuarios WHERE username = %s AND dni = %s", (username, dni))
            user = cursor.fetchone()

            if user:
                # Guardar el usuario en la sesión
                session['user_id'] = user[0]
                session['username'] = user[1]
                flash("✅ ¡Bienvenido de nuevo!")
                return redirect(url_for('dashboardRuta'))
            else:
                flash("⚠️ Usuario o DNI incorrectos. Intenta nuevamente.")

        except Exception as e:
            print(f"❌ Error al conectar a la base de datos: {e}")
            flash("⚠️ Error al autenticar. Intenta de nuevo.")

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registroRuta():
    if request.method == 'POST':
        username = request.form.get('username')
        dni = request.form.get('dni')
        mayor_edad = 'mayor_edad' in request.form  # Devuelve True si está marcado

        try:
            connection = psycopg2.connect(
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME
            )
            cursor = connection.cursor()

            # Validar si el usuario o el dni ya existen
            cursor.execute("SELECT 1 FROM usuarios WHERE username = %s OR dni = %s", (username, dni))
            if cursor.fetchone():
                flash("⚠️ El nombre de usuario o DNI ya están registrados.")
                return render_template('registro.html')

            # Insertar usuario nuevo
            cursor.execute(
                "INSERT INTO usuarios (username, dni, mayor_edad) VALUES (%s, %s, %s)",
                (username, dni, mayor_edad)
            )
            connection.commit()
            flash("✅ Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect(url_for('loginRuta'))

        except Exception as e:
            print(f"❌ Error al registrar usuario: {e}")
            flash("Error al registrar el usuario. Intenta de nuevo.")
            print('HJ')
            return render_template('registro.html')

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    return render_template('registro.html')

@app.route('/dashboard')
def dashboardRuta():
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('loginRuta'))
    return render_template('dashboard.html')



@app.route('/crear_sala', methods=['POST'])
def crear_sala():
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('loginRuta'))

    # Generar un ID de sala único
    codigo_sala = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        cursor = connection.cursor()

        # Insertar la nueva sala
        cursor.execute(
            "INSERT INTO salas (id, creador_id, estado) VALUES (%s, %s, %s)",
            (codigo_sala, session['user_id'], 'esperando')
        )
        connection.commit()

        flash(f"✅ Sala creada: {codigo_sala}")
        return redirect(url_for('salaRuta', codigo_sala=codigo_sala))

    except Exception as e:
        print(f"❌ Error al crear sala: {e}")
        flash("⚠️ Error al crear la sala. Intenta de nuevo.")
        return redirect(url_for('dashboardRuta'))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# Para guardar quienes están en qué sala
# Lista de salas (esto es solo un ejemplo, puede estar en una base de datos)
salas = {
    'codigo_sala': {
        'jugadores': ['user1', 'user2'],
        'listos': {
            'user1': False,
            'user2': False,
        }
    }
}


@socketio.on('unirse_sala')
def unirse_sala(data):
    codigo_sala = data['codigo_sala']
    username = data['username']

    if codigo_sala not in salas:
        salas[codigo_sala] = {'jugadores': [], 'listos': {}}

    if username not in salas[codigo_sala]['jugadores']:
        salas[codigo_sala]['jugadores'].append(username)
        salas[codigo_sala]['listos'][username] = False

    join_room(codigo_sala)

    emit_actualizacion_jugadores(codigo_sala)

def emit_actualizacion_jugadores(codigo_sala):
    emit('actualizar_jugadores_listos', {
        'jugadores': salas[codigo_sala]['jugadores'],
        'listos': salas[codigo_sala]['listos']
    }, room=codigo_sala)

@socketio.on('jugador_listo')
def jugador_listo(data):
    codigo_sala = data['codigo_sala']
    username = data['username']

    if codigo_sala in salas and username in salas[codigo_sala]['listos']:
        salas[codigo_sala]['listos'][username] = True

        emit_actualizacion_jugadores(codigo_sala)

        # Verificar si todos están listos para habilitar el botón o iniciar partida
        if all(salas[codigo_sala]['listos'].values()):
            emit('todos_listos', room=codigo_sala)


@socketio.on('salir_sala')
def handle_salir_sala(data):
    codigo_sala = data['codigo_sala']
    username = data['username']
    
    # Verificar si la sala y el jugador existen en la lista
    if codigo_sala in salas and username in salas[codigo_sala]['jugadores']:
        salas[codigo_sala]['jugadores'].remove(username)
    
    # Emitir a todos los clientes conectados a esta sala la lista de jugadores
    emit('actualizar_jugadores', {'jugadores': salas[codigo_sala]['jugadores']}, room=codigo_sala)

    # Dejar el socket de la sala
    leave_room(codigo_sala)



@socketio.on('iniciar_partida')
def handle_iniciar_partida(data):
    codigo_sala = data['codigo_sala']
    emit('partida_iniciada', room=codigo_sala)


@app.route('/sala/<codigo_sala>')
def salaRuta(codigo_sala):
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('loginRuta'))

    # Emitir la lista de jugadores al cargar la sala
    if codigo_sala in salas:
        socketio.emit('actualizar_jugadores', {'jugadores': salas[codigo_sala]['jugadores']}, room=codigo_sala)

    return render_template('sala.html', codigo_sala=codigo_sala)


@app.route('/logout')
def logoutRuta():
    # Limpiar la sesión (esto elimina los datos del usuario)
    session.clear()
    flash("✅ Has cerrado sesión exitosamente.")
    return redirect(url_for('indexRuta'))  # Redirigir al usuario a la página de inicio


def generar_carton_bingo():
    global numeros_usados_global

    rangos = {
        'B': range(1, 20),
        'I': range(20, 40),
        'N': range(40, 60),
        'G': range(60, 80),
        'O': range(89, 100)
    }

    columnas = {}
    
    for letra, rango in rangos.items():
        posibles = list(set(rango) - numeros_usados_global)
        if len(posibles) < 5:
            raise ValueError(f"No hay suficientes números disponibles para la columna {letra}")
        seleccionados = random.sample(posibles, 5)
        columnas[letra] = seleccionados
        numeros_usados_global.update(seleccionados)

    # Construir la matriz del cartón (lista de filas)
    carton = []
    for i in range(5):
        fila = [columnas['B'][i], columnas['I'][i], columnas['N'][i], columnas['G'][i], columnas['O'][i]]
        carton.append(fila)

    # Agregar 10 espacios en blanco aleatorios
    posiciones = [(i, j) for i in range(5) for j in range(5)]
    blancos = random.sample(posiciones, 10)
    for i, j in blancos:
        carton[i][j] = ""

    return carton

@app.route('/juego_individual', methods=['POST'])
def juego_individual():
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('loginRuta'))

    cantidad_jugadores = int(request.form.get('cantidad_jugadores', 2))

    if cantidad_jugadores < 2 or cantidad_jugadores > 5:
        flash("⚠️ El número de jugadores debe estar entre 2 y 5.")
        return redirect(url_for('dashboardRuta'))

    numeros_usados_global.clear()  # Limpiar números usados al comenzar una nueva partida
    cartones = [generar_carton_bingo() for _ in range(cantidad_jugadores)]
    
    return render_template('juego_individual.html', cartones=cartones)



#si dejo el 404 el redirecionamiento no es automatico si lo quito es automatico
#def paginaNoEncontrada(error):
#   return redirect(url_for('indexRuta')), 404

# Definimos la ruta de error 404, que es la que se carga cuando no se encuentra la pagina que se busca
#app.register_error_handler(404, paginaNoEncontrada)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)

