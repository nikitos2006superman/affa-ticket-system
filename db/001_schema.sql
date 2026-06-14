-- ============================================================
-- Схема базы данных билетной системы АФФА
-- ============================================================

-- Типы ENUM
CREATE TYPE user_role AS ENUM ('admin', 'user');
CREATE TYPE event_status AS ENUM ('draft', 'published', 'cancelled', 'finished');
CREATE TYPE ticket_status AS ENUM ('active', 'used', 'cancelled', 'refunded');
CREATE TYPE transaction_status AS ENUM ('pending', 'completed', 'failed', 'refunded');

-- ============================================================
-- Таблицы
-- ============================================================

-- Пользователи
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    phone           TEXT,
    organization    TEXT,
    dealer_code     TEXT,
    role            user_role DEFAULT 'user',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at   TIMESTAMP
);

-- Площадки
CREATE TABLE venues (
    venue_id    SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    address     TEXT,
    city        TEXT,
    capacity    INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Мероприятия
CREATE TABLE events (
    event_id        SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT,
    venue_id        INTEGER REFERENCES venues(venue_id) ON DELETE SET NULL,
    starts_at       TIMESTAMP NOT NULL,
    ends_at         TIMESTAMP NOT NULL,
    total_capacity  INTEGER NOT NULL CHECK (total_capacity > 0),
    base_price      DECIMAL(10,2) DEFAULT 0,
    status          event_status DEFAULT 'draft',
    created_by      INTEGER REFERENCES users(user_id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (ends_at > starts_at)
);

-- Билеты
CREATE TABLE tickets (
    ticket_id       SERIAL PRIMARY KEY,
    ticket_code     UUID UNIQUE DEFAULT gen_random_uuid(),
    event_id        INTEGER NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    price_paid      DECIMAL(10,2) NOT NULL,
    status          ticket_status DEFAULT 'active',
    issued_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at         TIMESTAMP,
    cancelled_at    TIMESTAMP
);

-- Транзакции (история покупок)
CREATE TABLE transactions (
    transaction_id  SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(user_id),
    event_id        INTEGER REFERENCES events(event_id),
    ticket_id       INTEGER REFERENCES tickets(ticket_id),
    amount          DECIMAL(10,2) NOT NULL,
    quantity        INTEGER DEFAULT 1,
    status          transaction_status DEFAULT 'pending',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Лог отметок (check-in)
CREATE TABLE check_ins (
    check_in_id     SERIAL PRIMARY KEY,
    ticket_id       INTEGER NOT NULL REFERENCES tickets(ticket_id),
    checked_by      INTEGER REFERENCES users(user_id),
    checked_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address      TEXT,
    notes           TEXT
);

-- Журнал аудита изменений
CREATE TABLE audit_log (
    audit_id        SERIAL PRIMARY KEY,
    table_name      TEXT NOT NULL,
    record_id       INTEGER NOT NULL,
    operation       TEXT NOT NULL,
    old_data        JSONB,
    new_data        JSONB,
    changed_by      INTEGER REFERENCES users(user_id),
    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_events_starts_at ON events(starts_at);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_tickets_code ON tickets(ticket_code);
CREATE INDEX idx_tickets_user ON tickets(user_id);
CREATE INDEX idx_tickets_event ON tickets(event_id);
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_check_ins_ticket ON check_ins(ticket_id);
