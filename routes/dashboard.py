from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.helpers import login_requerido, generar_codigo_sala
from db import get_db_connection, close_db

dashboard_bp = Blueprint('dashboard', __name__)

#Ruta principal de la aplicación
@dashboard_bp.route('/')
def index():
    return render_template('index.html')

#Ruta principal del usuario autenticado
@dashboard_bp.route('/dashboard')
@login_requerido
def dashboard():
    """Panel principal del usuario autenticado."""
    return render_template('dashboard.html')

# Ruta para crear una nueva sala de bingo
@dashboard_bp.route('/crear_sala', methods=['POST'])
@login_requerido
def crear_sala():
    """ Permite al usuario crear una nueva sala de bingo.
    Se genera un código único para la sala y se guarda en la base de datos."""
    # Genera un código único para la nueva sala usando la función auxiliar
    codigo_sala = generar_codigo_sala()

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Insertamos la nueva sala en la base de datos
        cursor.execute(
            "INSERT INTO salas (id, creador_id, estado) VALUES (%s, %s, %s)",
            (codigo_sala, session['user_id'], 'esperando')
        )
        connection.commit()
        flash(f"✅ Sala creada: {codigo_sala}")

        # Redirigimos al usuario a la sala recién creada
        return redirect(url_for('dashboard.sala', codigo_sala=codigo_sala))

    except Exception as e:
        print(f"❌ Error al crear sala: {e}")
        flash("⚠️ Error al crear la sala. Intenta de nuevo.")
        return redirect(url_for('auth.dashboard'))

    finally:
        close_db(cursor, connection)
    
# Ruta para mostrar una sala específica
@dashboard_bp.route('/sala/<codigo_sala>')
@login_requerido
def sala(codigo_sala):
    return render_template('sala.html', codigo_sala=codigo_sala, username=session.get('username'))