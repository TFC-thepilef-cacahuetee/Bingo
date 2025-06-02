import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room

import random
import string
from hashlib import sha256

import psycopg2
from dotenv import load_dotenv
import os

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

@app.route('/')
def indexRuta():
    return render_template('index.html')

numeros_usados_global = set()
numeros_marcados_por_jugador = {}

load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

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
    
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("Current Time:", result)

    cursor.close()
    connection.close()
    print("Connection closed.")

except Exception as e:
    print(f"Failed to connect: {e}")

@app.route('/login', methods=['GET', 'POST'])
def loginRuta():
    if request.method == 'POST':
        username = request.form.get('username')
        dni_plano = request.form.get('dni')
        dni_hash = sha256(dni_plano.encode()).hexdigest()
        try:
            connection = psycopg2.connect(
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME
            )
            cursor = connection.cursor()

            # Validar que el nombre de usuario y DNI (hasheado) coincidan con un registro en la base de datos
            cursor.execute("SELECT id, username FROM usuarios WHERE username = %s AND dni = %s", (username, dni_hash))
            user = cursor.fetchone()

            if user:
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
        dni_plano = request.form.get('dni')
        mayor_edad = 'mayor_edad' in request.form  # Devuelve True si está marcado

        # Hashear el DNI
        dni_hash = sha256(dni_plano.encode()).hexdigest()

        try:
            connection = psycopg2.connect(
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME
            )
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM usuarios WHERE username = %s OR dni = %s", (username, dni_hash))
            if cursor.fetchone():
                flash("⚠️ El nombre de usuario o DNI ya están registrados.")
                return render_template('registro.html')

            cursor.execute(
                "INSERT INTO usuarios (username, dni, mayor_edad) VALUES (%s, %s, %s)",
                (username, dni_hash, mayor_edad)
            )
            connection.commit()
            flash("✅ Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect(url_for('loginRuta'))

        except Exception as e:
            print(f"❌ Error al registrar usuario: {e}")
            
            flash("Error al registrar el usuario. Intenta de nuevo.")
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
    username = data['username'].strip().lower()


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
    codigo_sala = data['codigo_sala']
    username = data['username'].strip().lower()

    if codigo_sala in salas:
        if username not in salas[codigo_sala]['jugadores']:
            # No debería pasar, pero lo añadimos por seguridad
            salas[codigo_sala]['jugadores'].append(username)
        salas[codigo_sala]['listos'][username] = True

        emit_actualizacion_jugadores(codigo_sala)

        jugadores = salas[codigo_sala]['jugadores']
        listos_dict = salas[codigo_sala]['listos']

        # Verifica que todos los jugadores estén listos
        faltantes = [j for j in jugadores if not listos_dict.get(j, False)]
        print(f"Faltan por estar listos: {faltantes}")

        if len(faltantes) == 0:
            numeros_usados_sala = set()
            cartones_por_jugador = {}

            for jugador in jugadores:
                carton = generar_carton_bingo_personalizado()
                cartones_por_jugador[jugador] = carton

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

def generar_carton_bingo_personalizado():
    rangos = {
        'B': range(1, 20),
        'I': range(20, 40),
        'N': range(40, 60),
        'G': range(60, 80),
        'O': range(80, 100)
    }

    columnas = {}

    for letra, rango in rangos.items():
        seleccionados = random.sample(rango, 5)
        columnas[letra] = seleccionados

    carton = []
    for i in range(5):
        fila = [columnas['B'][i], columnas['I'][i], columnas['N'][i], columnas['G'][i], columnas['O'][i]]
        carton.append(fila)

    posiciones = [(i, j) for i in range(5) for j in range(5)]
    blancos = random.sample(posiciones, 8)  # Aquí cambiamos de 10 a 8 espacios en blanco
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

    cartones = [generar_carton_bingo_personalizado() for _ in range(cantidad_jugadores)]

    return render_template('juego_individual.html', cartones=cartones)

import threading
import time

# Diccionario para guardar estado de números ya emitidos por sala
numeros_emitidos_por_sala = {}

def emitir_numeros_periodicos(codigo_sala):
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

        time.sleep(0.5)  # Espera 3 segundos antes del siguiente número

@socketio.on('numero_marcado')
def handle_numero_marcado(data):
    
    codigo_sala = data.get('codigo_sala')
    username = data.get('username', '').strip().lower()
    numero = data.get('numero')
    marcado = data.get('marcado')

    # Reenviar a todos en la sala, incluyendo al que lo marcó
    socketio.emit('numero_marcado', {
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

@socketio.on('bingo_cantado')
def handle_bingo_cantado(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username', '').strip().lower()
    carton_jugador = data.get('carton')  # asumo que el jugador manda su cartón para validar

    # Aquí pones tu lógica para validar el bingo del jugador
    bingo_valido = validar_bingo(carton_jugador)  # define esta función con tu lógica

    if bingo_valido:
        # Anunciar ganador a todos
        emit('anunciar_ganador', {'ganador': username}, room=codigo_sala)

        # Resetear estado 'listo' para todos los jugadores de la sala
        if codigo_sala in salas:
            for jugador in salas[codigo_sala]['listos']:
                salas[codigo_sala]['listos'][jugador] = False
            emit_actualizacion_jugadores(codigo_sala)

    else:
        # Si no es válido, puede emitir un mensaje o nada
        emit('bingo_invalido', {'msg': 'Bingo no válido'}, room=request.sid)


def validar_bingo(carton):
    # carton es lista 5x5, cada posición tiene número o "" para blanco
    # Aquí debes verificar que el jugador marcó una línea completa.
    # Para simplicidad, asumamos que el jugador envía el cartón con "" donde no está marcado, y "X" donde marcó.

    # Ejemplo simple: Validar si alguna fila está toda marcada (con "X")
    for fila in carton:
        if all(casilla == "X" for casilla in fila):
            return True

    # Validar columnas
    for col in range(5):
        if all(fila[col] == "X" for fila in carton):
            return True

    # Validar diagonales
    if all(carton[i][i] == "X" for i in range(5)):
        return True
    if all(carton[i][4 - i] == "X" for i in range(5)):
        return True

    return False

@socketio.on('bingo_completado')
def handle_bingo_completado(data):
    codigo_sala = data.get('codigo_sala')
    username = data.get('username')

    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        cursor = connection.cursor()

        # Obtener user_id del username
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        user_record = cursor.fetchone()

        if not user_record:
            emit('error', {'msg': 'Usuario no encontrado en base de datos.'}, room=request.sid)
            return

        user_id = user_record[0]

        # Actualizar el ganador de la sala
        cursor.execute(
            "UPDATE salas SET ganador_id = %s WHERE id = %s",
            (user_id, codigo_sala)
        )
        connection.commit()

        print(f"Ganador guardado en sala {codigo_sala}: usuario {username} (id {user_id})")

    except Exception as e:
        print(f"Error guardando ganador en sala: {e}")
        emit('error', {'msg': 'Error al guardar ganador en la base de datos.'}, room=request.sid)

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    # Notificar a todos en la sala el ganador
    emit('anunciar_ganador', {'ganador': username}, room=codigo_sala)


if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)