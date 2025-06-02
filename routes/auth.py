from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from hashlib import sha256
from db import get_db_connection, close_db

auth_bp = Blueprint('auth', __name__)

# Ruta para el registro de usuarios
@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Registra un nuevo usuario en la base de datos."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        dni_plano = request.form.get('dni', '').strip()
        mayor_edad = 'mayor_edad' in request.form  # Devuelve True si está marcado

        # Hashear el DNI
        dni_hash = sha256(dni_plano.encode()).hexdigest()

        try:
            # Obtenemos una conexión a la base de datos
            connection = get_db_connection()
            cursor = connection.cursor()
            # Insertamos el nuevo usuario en la base de datos
            cursor.execute(
                "INSERT INTO usuarios (username, dni) VALUES (%s, %s)",
                (username, dni_hash)
            )
            connection.commit()
            flash("✅ Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect(url_for('login'))
        
        except Exception as e:
            print(f"❌ Error al registrar usuario: {e}")
            flash("⚠️ Error al registrar el usuario.")
        finally:
            close_db(cursor, connection)

    return render_template('registro.html')

# Ruta para el login de usuarios
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Inicia sesión si las credenciales coinciden."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        dni_plano = request.form.get('dni', '').strip()

        # Hashear el DNI ingresado
        dni_hash = sha256(dni_plano.encode()).hexdigest()

        try:
            # Obtenemos una conexión a la base de datos
            connection = get_db_connection()
            cursor = connection.cursor()

            # Validar que el nombre de usuario y DNI (hasheado) coincidan con un registro en la base de datos
            cursor.execute("SELECT id, username FROM usuarios WHERE username = %s AND dni = %s", (username, dni_hash))
            user = cursor.fetchone()

            if user:
                # Guardamos el ID del usuario en la sesión
                session['user_id'] = user[0]
                session['username'] = user[1]
                flash("✅ Sesión iniciada correctamente.")
                return redirect(url_for('dashboard'))
            else:
                flash("⚠️ Usuario o DNI incorrectos.")

        except Exception as e:
            print(f"❌ Error al iniciar sesión: {e}")
            flash("⚠️ Error al iniciar sesión.")

        finally:
            close_db(cursor, connection)

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    # Limpiar la sesión (esto elimina los datos del usuario)
    session.clear()
    flash("✅ Has cerrado sesión exitosamente.")
    return redirect(url_for('index'))  # Redirigir al usuario a la página de inicio
