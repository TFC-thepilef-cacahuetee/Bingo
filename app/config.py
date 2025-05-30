# Esta clase carga las variables de entorno y configura la app Flask.
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    DB_USER = os.getenv('user')
    DB_PASSWORD = os.getenv('password')
    DB_HOST = os.getenv('host')
    DB_PORT = os.getenv('port')
    DB_NAME = os.getenv('dbname')
