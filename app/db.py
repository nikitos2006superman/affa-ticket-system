"""Модуль работы с PostgreSQL через psycopg (версия 3)."""

from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from flask import current_app, g


def get_db_connection():
    """Возвращает соединение, привязанное к текущему запросу Flask."""
    if 'db_conn' not in g:
        g.db_conn = psycopg.connect(
            host=current_app.config['DB_HOST'],
            port=current_app.config['DB_PORT'],
            dbname=current_app.config['DB_NAME'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD'],
            autocommit=False,
        )
    return g.db_conn


def close_db_connection(exc=None):
    """Закрытие соединения по завершении запроса."""
    conn = g.pop('db_conn', None)
    if conn is not None:
        if exc is not None:
            conn.rollback()
        conn.close()


@contextmanager
def get_cursor(commit=False, dict_rows=True):
    """Контекстный менеджер для курсора.

    :param commit:    делать ли COMMIT в конце блока
    :param dict_rows: возвращать ли строки как dict-подобные объекты
    """
    conn = get_db_connection()
    factory = dict_row if dict_rows else None
    cur = conn.cursor(row_factory=factory) if factory else conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def init_app(app):
    """Регистрация хука на завершение запроса."""
    app.teardown_appcontext(close_db_connection)
