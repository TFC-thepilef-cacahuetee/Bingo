import os
from dotenv import load_dotenv

# Cargamos las variables de entorno desde un archivo .env
load_dotenv()
#Variables de entorno
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
SECRET_KEY = os.getenv("SECRET_KEY")