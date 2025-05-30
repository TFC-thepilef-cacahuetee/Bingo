# Este blueprint gestiona el dashboard y el juego individual.
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from ..utils.bingo import generar_carton_bingo

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')

@dashboard_bp.route('/juego_individual', methods=['POST'])
def juego_individual():
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('auth.login'))
    cantidad_jugadores = int(request.form.get('cantidad_jugadores', 2))
    if cantidad_jugadores < 2 or cantidad_jugadores > 5:
        flash("⚠️ El número de jugadores debe estar entre 2 y 5.")
        return redirect(url_for('dashboard.dashboard'))
    cartones = [generar_carton_bingo() for _ in range(cantidad_jugadores)]
    return render_template('juego_individual.html', cartones=cartones)

@dashboard_bp.route('/historial')
def historial():
    if 'user_id' not in session:
        flash("⚠️ Debes iniciar sesión primero.")
        return redirect(url_for('auth.login'))
    
    # Logica para el historial aqui

    return render_template('historial.html', partidas=historial_partidas)

