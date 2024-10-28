import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='recruitment_db'
    )
    if conn.is_connected():
        print('Connected to MySQL database')
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db = cursor.fetchone()
        print(f'Connected to database: {db}')
except Exception as e:
    print(f'Error: {str(e)}')
finally:
    if conn:
        conn.close()
