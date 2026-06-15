import os
import sys
import time
from pathlib import Path
import psycopg
from werkzeug.security import generate_password_hash

# Получаем переменные окружения Render
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

print(f'DB_HOST: {DB_HOST}')
print(f'DB_PORT: {DB_PORT}')
print(f'DB_NAME: {DB_NAME}')
print(f'DB_USER: {DB_USER}')

# Ждём, пока БД запустится
def wait_for_db():
    print('Ожидание подключения к PostgreSQL...')
    for i in range(30):
        try:
            conn = psycopg.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            conn.close()
            print('✅ Подключение успешно!')
            return True
        except Exception as e:
            print(f'Попытка {i+1}/30: {e}')
            time.sleep(2)
    return False

DB_DIR = Path(__file__).parent / 'db'

def run_sql(cur, path):
    print(f'  → {path.name}')
    cur.execute(path.read_text())

def main():
    if not DB_HOST:
        print('Ошибка: DB_HOST не задан!')
        sys.exit(1)
    
    if not wait_for_db():
        print('❌ Не удалось подключиться к БД')
        sys.exit(1)

    try:
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = False
        cur = conn.cursor()
        
        # Применяем SQL файлы
        sql_files = sorted(DB_DIR.glob('*.sql'))
        for f in sql_files:
            if f.name != '005_seed.sql':
                print(f'Выполняю {f.name}')
                run_sql(cur, f)
        
        # Создаём пользователей
        pwd = generate_password_hash('password123')
        users = [
            ('admin@affa.local', 'Администратор АФФА', 'admin'),
            ('petrov@dealer1.ru', 'Иван Петров', 'user'),
            ('sidorova@dealer2.ru', 'Мария Сидорова', 'user'),
            ('kozlov@dealer3.ru', 'Алексей Козлов', 'user')
        ]
        for email, name, role in users:
            cur.execute("""
                INSERT INTO users (email, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (email, pwd, name, role))
        
        # Назначаем создателя мероприятий
        cur.execute("SELECT user_id FROM users WHERE email='admin@affa.local'")
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE events SET created_by=%s WHERE created_by IS NULL", (row[0],))
        
        # Применяем seed
        seed = DB_DIR / '005_seed.sql'
        if seed.exists():
            run_sql(cur, seed)
        
        conn.commit()
        print('✅ База данных успешно инициализирована!')
        print('Пароль для всех пользователей: password123')
        
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
