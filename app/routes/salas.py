# Este blueprint gestiona la creación y visualización de salas.
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
import random
import string
from ..db.queries import insert_sala

salas_bp = Blueprint('salas', __name__)

@salas_bp.route('/crear_sala', methods=['POST'])
def crear_sala():
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('auth.login'))
    codigo_sala = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    insert_sala(codigo_sala, session['user_id'])
    flash(f"✅ Sala creada: {codigo_sala}")
    return redirect(url_for('salas.sala', codigo_sala=codigo_sala))

@salas_bp.route('/sala/<codigo_sala>')
def sala(codigo_sala):
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('auth.login'))
    return render_template('sala.html', codigo_sala=codigo_sala, username=session.get('username'))
