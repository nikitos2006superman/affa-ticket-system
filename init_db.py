import os, sys, time, psycopg
from werkzeug.security import generate_password_hash

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

print(f'Подключение к {DB_HOST}:{DB_PORT}/{DB_NAME}')

# Ждём БД
for i in range(30):
    try:
        conn = psycopg.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Создаём таблицу users простую
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Добавляем админа
        pwd = generate_password_hash('password123')
        cur.execute("""
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES ('admin@affa.local', %s, 'Администратор', 'admin')
            ON CONFLICT (email) DO NOTHING
        """, (pwd,))
        
        print('✅ База данных готова!')
        print('Пароль: password123')
        sys.exit(0)
    except Exception as e:
        print(f'Попытка {i+1}: {e}')
        time.sleep(2)

print('❌ Не удалось подключиться')
sys.exit(1)
