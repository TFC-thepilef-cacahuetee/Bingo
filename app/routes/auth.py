# Este blueprint gestiona las rutas de autenticación: login, registro y logout.
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from hashlib import sha256
from ..db.queries import get_user_by_username_and_dni, user_exists, insert_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        dni_plano = request.form.get('dni')
        dni_hash = sha256(dni_plano.encode()).hexdigest()
        user = get_user_by_username_and_dni(username, dni_hash)
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash("✅ ¡Bienvenido de nuevo!")
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash("⚠️ Usuario o DNI incorrectos. Intenta nuevamente.")
    return render_template('login.html')

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        dni_plano = request.form.get('dni')
        mayor_edad = 'mayor_edad' in request.form
        dni_hash = sha256(dni_plano.encode()).hexdigest()
        if user_exists(username, dni_hash):
            flash("⚠️ El nombre de usuario o DNI ya están registrados.")
            return render_template('registro.html')
        insert_user(username, dni_hash, mayor_edad)
        flash("✅ Registro exitoso. Ahora puedes iniciar sesión.")
        return redirect(url_for('auth.login'))
    return render_template('registro.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("✅ Has cerrado sesión exitosamente.")
    return redirect(url_for('auth.index'))

@auth_bp.route('/')
def index():
    return render_template('index.html')
