import random
import string
from flask import session, flash, redirect, url_for
from functools import wraps

def generar_codigo_sala():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("⚠️ Debes iniciar sesión primero.")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated