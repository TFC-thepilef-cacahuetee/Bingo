# Importamos eventlet para habilitar soporte asíncrono eficiente y parches a bibliotecas estándar
import eventlet
eventlet.monkey_patch()  # Aplica monkey patching a librerías estándar para hacerlas compatibles con eventlet

# Importamos módulos necesarios de Flask y Flask-SocketIO
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room  # Para comunicación en tiempo real con WebSockets

# Librerías estándar para operaciones aleatorias y hashing
import random
import string
from hashlib import sha256  # Para encriptar datos como el DNI

# Módulos para conexión a base de datos PostgreSQL y manejo de variables de entorno
import psycopg2
from dotenv import load_dotenv
import os


## Creamos la aplicación Flask
app = Flask(__name__)

# Inicializamos SocketIO con la app de Flask utilizando eventlet como modo asíncrono
socketio = SocketIO(app, async_mode='eventlet')

# Definimos la ruta de la aplicacion, en este caso la ruta principal que es la que se carga al abrir la app
@app.route('/')
def indexRuta():
    return render_template('index.html')

# Esto es para hacer la conexion con la base de datos
numeros_usados_global = set()
numeros_marcados_por_jugador = {}

load_dotenv()  # Cargar variables desde .env

app.secret_key = os.getenv('SECRET_KEY')  # Clave para sesiones seguras en Flask

# Obtener variables de conexión a la base de datos
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Probar conexión a la base de datos PostgreSQL
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")
    
    cursor = connection.cursor()
    cursor.execute("SELECT NOW();")  # Consulta simple para probar
    result = cursor.fetchone()
    print("Current Time:", result)

    cursor.close()
    connection.close()
    print("Connection closed.")

except Exception as e:
    print(f"Failed to connect: {e}")  # Mostrar errores de conexión

@app.route('/login', methods=['GET', 'POST'])
def loginRuta():
    if request.method == 'POST':
        # Recibe datos del formulario
        username = request.form.get('username')
        dni_plano = request.form.get('dni')

        # Hashea el DNI antes de buscarlo en la base de datos
        dni_hash = sha256(dni_plano.encode()).hexdigest()

        try:
            connection = psycopg2.connect(...)  # Conectar a la DB
            cursor = connection.cursor()

            # Buscar usuario por nombre y DNI encriptado
            cursor.execute("SELECT id, username FROM usuarios WHERE username = %s AND dni = %s", (username, dni_hash))
            user = cursor.fetchone()

            if user:
                # Guardar datos en la sesión
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
            if cursor: cursor.close()
            if connection: connection.close()

    return render_template('login.html')  # Renderiza el formulario


@app.route('/registro', methods=['GET', 'POST'])
def registroRuta():
    if request.method == 'POST':
        username = request.form.get('username')
        dni_plano = request.form.get('dni')
        mayor_edad = 'mayor_edad' in request.form

        dni_hash = sha256(dni_plano.encode()).hexdigest()  # Hashear DNI

        try:
            connection = psycopg2.connect(...)
            cursor = connection.cursor()

            # Validar si el usuario o DNI ya existen
            cursor.execute("SELECT 1 FROM usuarios WHERE username = %s OR dni = %s", (username, dni_hash))
            if cursor.fetchone():
                flash("⚠️ El nombre de usuario o DNI ya están registrados.")
                return render_template('registro.html')

            # Insertar nuevo usuario
            cursor.execute("INSERT INTO usuarios (username, dni, mayor_edad) VALUES (%s, %s, %s)", (username, dni_hash, mayor_edad))
            connection.commit()
            flash("✅ Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect(url_for('loginRuta'))

        except Exception as e:
            print(f"❌ Error al registrar usuario: {e}")
            flash("Error al registrar el usuario. Intenta de nuevo.")

        finally:
            if cursor: cursor.close()
            if connection: connection.close()

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

    codigo_sala = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))  # Generar código único

    try:
        connection = psycopg2.connect(...)
        cursor = connection.cursor()

        # Insertar sala en la base de datos
        cursor.execute("INSERT INTO salas (id, creador_id, estado) VALUES (%s, %s, %s)", (codigo_sala, session['user_id'], 'esperando'))
        connection.commit()

        flash(f"✅ Sala creada: {codigo_sala}")
        return redirect(url_for('salaRuta', codigo_sala=codigo_sala))

    except Exception as e:
        print(f"❌ Error al crear sala: {e}")
        flash("⚠️ Error al crear la sala. Intenta de nuevo.")

    finally:
        if cursor: cursor.close()
        if connection: connection.close()


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
    # Agrega un jugador a una sala y emite el estado actualizado
    codigo_sala = data['codigo_sala']
    username = data['username']

    if codigo_sala not in salas:
        salas[codigo_sala] = {'jugadores': [], 'listos': {}}

    # ⚠️ Verificar que no haya más de 10 jugadores
    if len(salas[codigo_sala]['jugadores']) >= 10:
        emit('sala_llena', {'mensaje': 'La sala ya tiene 10 jugadores.'})
        return

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
def handle_jugador_listo(data):
    # Marca jugador como listo. Si todos están listos, inicia partida
    codigo_sala = data['codigo_sala']
    username = data['username']

    if codigo_sala in salas and username in salas[codigo_sala]['listos']:
        salas[codigo_sala]['listos'][username] = True

        emit_actualizacion_jugadores(codigo_sala)

        jugadores = salas[codigo_sala]['jugadores']
        listos_dict = salas[codigo_sala]['listos']

        todos_listos = all(listos_dict.get(j, False) for j in jugadores)
        if todos_listos:
            numeros_usados_sala = set()
            cartones_por_jugador = {}

            for jugador in jugadores:
                carton = generar_carton_bingo_personalizado(numeros_usados_sala)
                cartones_por_jugador[jugador] = carton

            emit('partida_iniciada', {'cartones': cartones_por_jugador}, room=codigo_sala)

            # Iniciar emisión de números en hilo separado
            thread = threading.Thread(target=emitir_numeros_periodicos, args=(codigo_sala,))
            thread.start()


@socketio.on('salir_sala')
def handle_salir_sala(data):
    # Quita al jugador de la sala
    codigo_sala = data['codigo_sala']
    username = data['username']

    if codigo_sala in salas:
        if username in salas[codigo_sala]['jugadores']:
            salas[codigo_sala]['jugadores'].remove(username)
            salas[codigo_sala]['listos'].pop(username, None)
            leave_room(codigo_sala)
            emit_actualizacion_jugadores(codigo_sala)



@socketio.on('iniciar_partida')
def handle_iniciar_partida(data):
     # Forzar inicio de partida (manual)
    codigo_sala = data['codigo_sala']
    emit('partida_iniciada', room=codigo_sala)


@app.route('/sala/<codigo_sala>')
def salaRuta(codigo_sala):
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('loginRuta'))

    return render_template('sala.html', codigo_sala=codigo_sala, username=session.get('username'))



@app.route('/logout')
def logoutRuta():
    # Limpiar la sesión (esto elimina los datos del usuario)
    session.clear()
    flash("✅ Has cerrado sesión exitosamente.")
    return redirect(url_for('indexRuta'))  # Redirigir al usuario a la página de inicio



def generar_carton_bingo_personalizado(numeros_usados):
    # Genera un cartón de 5x5 con números únicos por columna según rangos de bingo
    rangos = {
        'B': range(1, 20),
        'I': range(20, 40),
        'N': range(40, 60),
        'G': range(60, 80),
        'O': range(89, 100)
    }

    columnas = {}
    
    for letra, rango in rangos.items():
        posibles = list(set(rango) - numeros_usados)
        if len(posibles) < 5:
            raise ValueError(f"No hay suficientes números disponibles para la columna {letra}")
        seleccionados = random.sample(posibles, 5)
        columnas[letra] = seleccionados
        numeros_usados.update(seleccionados)

    carton = []
    for i in range(5):
        fila = [columnas['B'][i], columnas['I'][i], columnas['N'][i], columnas['G'][i], columnas['O'][i]]
        carton.append(fila)

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

    numeros_usados = set()  # conjunto local para números usados en esta partida individual

    cartones = [generar_carton_bingo_personalizado(numeros_usados) for _ in range(cantidad_jugadores)]

    return render_template('juego_individual.html', cartones=cartones)




import threading
import time

# Diccionario para guardar estado de números ya emitidos por sala
numeros_emitidos_por_sala = {}

def emitir_numeros_periodicos(codigo_sala):
    # Emite un número nuevo cada 3 segundos a todos los jugadores de la sala
    numeros_emitidos_por_sala[codigo_sala] = set()
    todos_numeros = set(range(1, 100))  # Números del 1 al 99

    while True:
        disponibles = list(todos_numeros - numeros_emitidos_por_sala[codigo_sala])
        if not disponibles:
            # Ya se emitieron todos los números, se puede terminar el ciclo
            socketio.emit('fin_partida', room=codigo_sala)
            break
        
        numero = random.choice(disponibles)
        numeros_emitidos_por_sala[codigo_sala].add(numero)

        socketio.emit('numero_nuevo', {'numero': numero}, room=codigo_sala)

        time.sleep(3)  

@socketio.on('numero_marcado')
def handle_numero_marcado(data):
    # Reenvía a todos en la sala el número que un jugador marcó en su cartón
    codigo_sala = data.get('codigo_sala')
    username = data.get('username')
    numero = data.get('numero')
    marcado = data.get('marcado')

    socketio.emit('numero_marcado', {
        'codigo_sala': codigo_sala,
        'username': username,
        'numero': numero,
        'marcado': marcado
    }, room=codigo_sala)

@socketio.on('linea_cantada')
def handle_linea_cantada(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username')
    
    # Emitir a todos los jugadores en la sala que cambien el botón a "Bingo"
    emit('cambiar_a_bingo', {'username': username}, room=codigo_sala)


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
