import psycopg2
import os

connection = psycopg2.connect(
    user="postgres.agpcdcrmobqhnlnaocdx",
    password="t5kmJHbrldFsQHng",
    host="aws-0-eu-west-3.pooler.supabase.com",
    port=6543,
    dbname="postgres"
)

cursor = connection.cursor()
cursor.execute("SELECT NOW();")
print(cursor.fetchone())

cursor.close()
connection.close()
