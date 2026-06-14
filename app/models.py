"""Слой доступа к данным.

Все запросы и вызовы хранимых процедур собраны здесь, чтобы маршруты
оставались тонкими.
"""

from werkzeug.security import generate_password_hash, check_password_hash

from app.db import get_cursor


# =====================================================================
# Пользователи
# =====================================================================

class User:
    """Простая обёртка для совместимости с Flask-Login."""

    def __init__(self, row):
        self.id = row['user_id']
        self.email = row['email']
        self.full_name = row['full_name']
        self.role = row['role']
        self.is_active_flag = row['is_active']
        self.phone = row.get('phone')
        self.organization = row.get('organization')
        self.dealer_code = row.get('dealer_code')

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.is_active_flag

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == 'admin'


def find_user_by_id(user_id):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return User(row) if row else None


def find_user_by_email(email):
    with get_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
        return cur.fetchone()


def create_user(email, password, full_name, phone=None,
                organization=None, dealer_code=None, role='user'):
    pwd_hash = generate_password_hash(password)
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name, phone,
                               organization, dealer_code, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING user_id
            """,
            (email.lower().strip(), pwd_hash, full_name, phone,
             organization, dealer_code, role),
        )
        return cur.fetchone()['user_id']


def verify_password(email, password):
    row = find_user_by_email(email)
    if not row or not row['is_active']:
        return None
    if not check_password_hash(row['password_hash'], password):
        return None
    return User(row)


# =====================================================================
# Площадки
# =====================================================================

def list_venues():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM venues ORDER BY name")
        return cur.fetchall()


# =====================================================================
# Мероприятия
# =====================================================================

def list_published_events(search=None, upcoming_only=True):
    """Афиша для публичной части."""
    sql = """
        SELECT e.*, v.name AS venue_name, v.address AS venue_address, v.city AS venue_city
          FROM events e
     LEFT JOIN venues v ON v.venue_id = e.venue_id
         WHERE e.status = 'published'
    """
    params = []
    if upcoming_only:
        sql += " AND e.starts_at > CURRENT_TIMESTAMP"
    if search:
        sql += " AND (e.title ILIKE %s OR e.description ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    sql += " ORDER BY e.starts_at"

    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def list_all_events():
    """Все мероприятия — для админки."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT e.*, v.name AS venue_name
              FROM events e
         LEFT JOIN venues v ON v.venue_id = e.venue_id
          ORDER BY e.starts_at DESC
        """)
        return cur.fetchall()


def get_event(event_id):
    with get_cursor() as cur:
        cur.execute("""
            SELECT e.*, v.name AS venue_name, v.address AS venue_address, v.city AS venue_city
              FROM events e
         LEFT JOIN venues v ON v.venue_id = e.venue_id
             WHERE e.event_id = %s
        """, (event_id,))
        return cur.fetchone()


def create_event(data, created_by):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO events (title, description, venue_id, starts_at, ends_at,
                                total_capacity, base_price, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING event_id
        """, (
            data['title'], data.get('description'), data.get('venue_id'),
            data['starts_at'], data['ends_at'],
            data['total_capacity'], data.get('base_price', 0),
            data.get('status', 'draft'), created_by,
        ))
        return cur.fetchone()['event_id']


def update_event(event_id, data):
    with get_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE events SET
                title = %s, description = %s, venue_id = %s,
                starts_at = %s, ends_at = %s,
                total_capacity = %s, base_price = %s, status = %s
              WHERE event_id = %s
        """, (
            data['title'], data.get('description'), data.get('venue_id'),
            data['starts_at'], data['ends_at'],
            data['total_capacity'], data.get('base_price', 0),
            data.get('status', 'draft'), event_id,
        ))


def delete_event(event_id):
    with get_cursor(commit=True) as cur:
        cur.execute("DELETE FROM events WHERE event_id = %s", (event_id,))


# =====================================================================
# Билеты — через хранимые процедуры
# =====================================================================

def purchase_ticket(user_id, event_id, quantity=1):
    """Вызов sp_purchase_ticket. Возвращает (transaction_id, [ticket_codes])."""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT * FROM sp_purchase_ticket(%s, %s, %s)",
            (user_id, event_id, quantity),
        )
        row = cur.fetchone()
        return row['transaction_id'], row['ticket_codes']


def check_in_ticket(ticket_code, admin_id, note=None):
    """Вызов sp_check_in_ticket."""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT * FROM sp_check_in_ticket(%s, %s, %s)",
            (ticket_code, admin_id, note),
        )
        return cur.fetchone()


def cancel_ticket(ticket_code, user_id):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT sp_cancel_ticket(%s, %s) AS ok",
            (ticket_code, user_id),
        )
        return cur.fetchone()['ok']


def list_user_tickets(user_id):
    with get_cursor() as cur:
        cur.execute("""
            SELECT t.ticket_id, t.ticket_code, t.status, t.price_paid,
                   t.issued_at, t.used_at,
                   e.title AS event_title, e.starts_at, e.ends_at,
                   v.name  AS venue_name, v.address AS venue_address
              FROM tickets t
              JOIN events  e ON e.event_id = t.event_id
         LEFT JOIN venues v ON v.venue_id = e.venue_id
             WHERE t.user_id = %s
          ORDER BY e.starts_at DESC
        """, (user_id,))
        return cur.fetchall()


def get_ticket_by_code(ticket_code):
    with get_cursor() as cur:
        cur.execute("""
            SELECT t.*, e.title AS event_title, e.starts_at,
                   u.full_name AS holder_name, u.email AS holder_email
              FROM tickets t
              JOIN events  e ON e.event_id = t.event_id
              JOIN users   u ON u.user_id  = t.user_id
             WHERE t.ticket_code = %s
        """, (ticket_code,))
        return cur.fetchone()


# =====================================================================
# Отчёты (через VIEW)
# =====================================================================

def report_event_sales():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM v_event_sales ORDER BY starts_at DESC")
        return cur.fetchall()


def report_daily_revenue(days=30):
    with get_cursor() as cur:
        cur.execute("""
            SELECT * FROM v_daily_revenue
             WHERE sale_date >= CURRENT_DATE - %s::INTEGER
          ORDER BY sale_date DESC
        """, (days,))
        return cur.fetchall()


def report_attendance():
    with get_cursor() as cur:
        cur.execute("SELECT * FROM v_event_attendance ORDER BY starts_at DESC")
        return cur.fetchall()


def report_dealer_stats():
    """Отчёт по активности дилеров — характерный для корпоративной системы АФФА."""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM v_dealer_stats")
        return cur.fetchall()


def admin_dashboard_stats():
    """Сводные показатели для дашборда."""
    with get_cursor() as cur:
        cur.execute("""
            SELECT
              (SELECT COUNT(*) FROM events WHERE status = 'published'
                 AND starts_at > CURRENT_TIMESTAMP)              AS upcoming_events,
              (SELECT COUNT(*) FROM tickets WHERE status IN ('active','used')) AS total_tickets,
              (SELECT COUNT(*) FROM users  WHERE role = 'user')  AS total_users,
              (SELECT COALESCE(SUM(price_paid), 0) FROM tickets
                 WHERE status IN ('active','used'))              AS total_revenue
        """)
        return cur.fetchone()
