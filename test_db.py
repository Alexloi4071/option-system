import psycopg2
import os

try:
    connection = psycopg2.connect(
        user="postgres.nlwielyxzsarmcjfrazm",
        password="Bb5@45@34071",
        host="aws-1-ap-southeast-2.pooler.supabase.com",
        port=5432,
        dbname="postgres",
        connect_timeout=10,
        sslmode="require"
    )
    print("Connection successful!")
    
    cursor = connection.cursor()
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("Current Time:", result)

    cursor.close()
    connection.close()
except Exception as e:
    print(f"Failed to connect: {e}")
