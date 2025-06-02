import psycopg2

connection = psycopg2.connect(
    user="postgres.agpcdcrmobqhnlnaocdx",
    password="9ZwDvYhL15S9YI6l",
    host="aws-0-eu-west-3.pooler.supabase.com",
    port=6543,
    dbname="postgres"
)

cursor = connection.cursor()

print("✅ Conexión exitosa.\n")

# Obtener la hora actual
cursor.execute("SELECT NOW();")
print("🕒 Hora del servidor:", cursor.fetchone()[0])

# Obtener la versión de PostgreSQL
cursor.execute("SELECT version();")
print("🧠 Versión de PostgreSQL:", cursor.fetchone()[0])

# Obtener el nombre de la base actual
cursor.execute("SELECT current_database();")
print("📂 Base de datos:", cursor.fetchone()[0])

# Obtener el usuario actual
cursor.execute("SELECT current_user;")
print("👤 Usuario conectado:", cursor.fetchone()[0])

cursor.close()
connection.close()
print("\n🔌 Conexión cerrada.")
