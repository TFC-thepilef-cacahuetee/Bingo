# Esta clase contiene la lógica para generar cartones de bingo personalizados.
import random

def generar_carton_bingo():
    rangos = {
        'B': range(1, 20),
        'I': range(20, 40),
        'N': range(40, 60),
        'G': range(60, 80),
        'O': range(80, 100)
    }
    columnas = {}
    for letra, rango in rangos.items():
        columnas[letra] = random.sample(rango, 5)
    carton = []
    for i in range(5):
        fila = [columnas['B'][i], columnas['I'][i], columnas['N'][i], columnas['G'][i], columnas['O'][i]]
        carton.append(fila)
    posiciones = [(i, j) for i in range(5) for j in range(5)]
    blancos = random.sample(posiciones, 8)
    for i, j in blancos:
        carton[i][j] = ""
    return carton
