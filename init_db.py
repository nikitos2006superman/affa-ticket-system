import os
import sys
from pathlib import Path
import psycopg
from werkzeug.security import generate_password_hash

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'ticket_db')
DB_USER = os.getenv('DB_USER', 'ticket_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'ticket_pass')

DB_DIR = Path(__file__).parent / 'db'

def run_sql(cur, path):
    print(f'  → {path.name}')
    cur.execute(path.read_text())

def main():
    print(f'Подключение к {DB_HOST}:{DB_PORT}/{DB_NAME}')
    try:
        conn = psycopg.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
        cur = conn.cursor()
        
        for f in sorted(DB_DIR.glob('*.sql')):
            if f.name != '005_seed.sql':
                run_sql(cur, f)
        
        pwd = generate_password_hash('password123')
        users = [
            ('admin@affa.local', 'Администратор АФФА', 'admin'),
            ('petrov@dealer1.ru', 'Иван Петров', 'user'),
            ('sidorova@dealer2.ru', 'Мария Сидорова', 'user'),
            ('kozlov@dealer3.ru', 'Алексей Козлов', 'user')
        ]
        for email, name, role in users:
            cur.execute("INSERT INTO users (email, password_hash, full_name, role) VALUES (%s, %s, %s, %s) ON CONFLICT (email) DO NOTHING", (email, pwd, name, role))
        
        cur.execute("SELECT user_id FROM users WHERE email='admin@affa.local'")
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE events SET created_by=%s WHERE created_by IS NULL", (row[0],))
        
        seed = DB_DIR / '005_seed.sql'
        if seed.exists():
            run_sql(cur, seed)
        
        conn.commit()
        print('✅ База данных готова!')
        print('Пароль для всех: password123')
    except Exception as e:
        print(f'Ошибка: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
