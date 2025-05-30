# db/__init__.py
# Paquete para la gestión de la base de datos
from .connection import get_db_connection
from .queries import (
    get_user_by_username_and_dni,
    user_exists,
    insert_user,
    insert_sala,
)
