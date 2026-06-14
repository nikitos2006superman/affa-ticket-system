"""Скрипт инициализации базы данных."""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DB_PARAMS = dict(
    host=os.getenv('DB_HOST', 'localhost'),
    port=int(os.getenv('DB_PORT', 5432)),
    dbname=os.getenv('DB_NAME', 'ticket_db'),
    user=os.getenv('DB_USER', 'ticket_user'),
    password=os.getenv('DB_PASSWORD', 'ticket_pass'),
)

DB_DIR = Path(__file__).parent / 'db'


def run_sql_file(cur, path: Path):
    print(f'  → применяю {path.name}')
    cur.execute(path.read_text(encoding='utf-8'))


def create_test_users(cur):
    """Создаёт админа и трёх обычных пользователей. Пароль: password123"""
    print('  → создаю тестовых пользователей')

    pwd_hash = generate_password_hash('password123')
    test_users = [
        ('admin@affa.local',  'Администратор АФФА',  '+74012001122', 'ООО Группа АФФА', None,    'admin'),
        ('petrov@dealer1.ru', 'Иван Петров',         '+79009998877', 'ООО ШинТрейд',    'D-1001', 'user'),
        ('sidorova@dealer2.ru','Мария Сидорова',     '+79008887766', 'ООО АвтоПарк',    'D-1002', 'user'),
        ('kozlov@dealer3.ru', 'Алексей Козлов',      '+79007776655', 'ИП Козлов А.С.',  'D-1003', 'user'),
    ]

    for email, name, phone, org, dealer_code, role in test_users:
        cur.execute("""
            INSERT INTO users (email, password_hash, full_name, phone,
                               organization, dealer_code, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (email, pwd_hash, name, phone, org, dealer_code, role))


def update_event_creators(cur):
    """Назначаем админа создателем мероприятий."""
    print('  → назначаю создателя мероприятий')
    # Находим ID админа
    cur.execute("SELECT user_id FROM users WHERE email = 'admin@affa.local'")
    row = cur.fetchone()
    if row:
        admin_id = row[0] if isinstance(row, tuple) else row['user_id']
        cur.execute("UPDATE events SET created_by = %s WHERE created_by IS NULL", (admin_id,))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true',
                        help='Сначала удалить все таблицы')
    args = parser.parse_args()

    print(f'Подключение к БД {DB_PARAMS["dbname"]} на {DB_PARAMS["host"]}:{DB_PARAMS["port"]}')
    
    try:
        conn = psycopg.connect(**DB_PARAMS, autocommit=False)
    except psycopg.OperationalError as e:
        print(f'Ошибка подключения: {e}', file=sys.stderr)
        sys.exit(1)

    try:
        with conn.cursor() as cur:
            # Применяем SQL файлы по порядку
            sql_files = sorted(DB_DIR.glob('*.sql'))
            if not sql_files:
                print('Ошибка: не найдены SQL файлы в папке db/', file=sys.stderr)
                sys.exit(1)
            
            for sql_file in sql_files:
                if sql_file.name == '005_seed.sql':
                    continue  # seed выполним после создания пользователей
                run_sql_file(cur, sql_file)

            # Создаём тестовых пользователей
            create_test_users(cur)

            # Обновляем created_by в мероприятиях
            update_event_creators(cur)

            # Применяем seed (мероприятия)
            seed_file = DB_DIR / '005_seed.sql'
            if seed_file.exists():
                run_sql_file(cur, seed_file)

        conn.commit()
        print('\n✅ Инициализация БД завершена успешно!')
        print('\n📋 Тестовые учётные записи (пароль: password123):')
        print('  admin@affa.local      — администратор')
        print('  petrov@dealer1.ru     — дилер ООО ШинТрейд')
        print('  sidorova@dealer2.ru   — дилер ООО АвтоПарк')
        print('  kozlov@dealer3.ru     — дилер ИП Козлов А.С.')
    except Exception as e:
        conn.rollback()
        print(f'\n❌ Ошибка: {e}', file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
