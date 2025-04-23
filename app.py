# En esta parte se pone todo lo que queramos importar para luego usarlo en la aplicacion
# render_template es para renderizar el html desde la carpeta templates que la usa por defecto
# Flask es el framework que estamos usando para crear la aplicacion web
from flask import Flask, render_template, redirect, url_for

# Creamos la app Flask y le pasamos __name__ para que pueda encontrar rutas de archivos como templates y estáticos
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


def paginaNoEncontrada(error):
    return redirect(url_for('index')), 404

print(__name__)

if __name__ == '__main__':
    app.run(debug=True, port=5000)