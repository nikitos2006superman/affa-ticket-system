-- ============================================================
-- Хранимые процедуры
-- ============================================================

-- Процедура покупки билета (с защитой от овербукинга)
CREATE OR REPLACE FUNCTION sp_purchase_ticket(
    p_user_id INTEGER,
    p_event_id INTEGER,
    p_quantity INTEGER DEFAULT 1
)
RETURNS TABLE(
    transaction_id INTEGER,
    ticket_codes TEXT[]
) AS $$
DECLARE
    v_event RECORD;
    v_available INTEGER;
    v_transaction_id INTEGER;
    v_ticket_codes TEXT[] := '{}';
    v_ticket_id INTEGER;
    v_ticket_code TEXT;
BEGIN
    -- Блокируем событие для предотвращения гонок
    SELECT e.total_capacity, 
           COALESCE(COUNT(t.ticket_id), 0) as sold_count,
           e.base_price,
           e.status,
           e.starts_at
    INTO v_event
    FROM events e
    LEFT JOIN tickets t ON t.event_id = e.event_id AND t.status IN ('active', 'used')
    WHERE e.event_id = p_event_id
    GROUP BY e.event_id
    FOR UPDATE;

    -- Проверки
    IF v_event.status != 'published' THEN
        RAISE EXCEPTION 'Мероприятие не доступно для регистрации';
    END IF;

    IF v_event.starts_at <= CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Регистрация на мероприятие закрыта';
    END IF;

    v_available := v_event.total_capacity - v_event.sold_count;
    IF v_available < p_quantity THEN
        RAISE EXCEPTION 'Свободных мест: %, запрошено: %', v_available, p_quantity;
    END IF;

    -- Создаём транзакцию
    INSERT INTO transactions (user_id, event_id, amount, quantity, status)
    VALUES (p_user_id, p_event_id, v_event.base_price * p_quantity, p_quantity, 'completed')
    RETURNING transaction_id INTO v_transaction_id;

    -- Создаём билеты
    FOR i IN 1..p_quantity LOOP
        INSERT INTO tickets (event_id, user_id, price_paid, status)
        VALUES (p_event_id, p_user_id, v_event.base_price, 'active')
        RETURNING ticket_id, ticket_code::TEXT INTO v_ticket_id, v_ticket_code;

        v_ticket_codes := array_append(v_ticket_codes, v_ticket_code);
    END LOOP;

    RETURN QUERY SELECT v_transaction_id, v_ticket_codes;
END;
$$ LANGUAGE plpgsql;


-- Процедура отметки входа (check-in)
CREATE OR REPLACE FUNCTION sp_check_in_ticket(
    p_ticket_code TEXT,
    p_admin_id INTEGER,
    p_note TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    event_title TEXT,
    holder_name TEXT,
    message TEXT
) AS $$
DECLARE
    v_ticket RECORD;
BEGIN
    -- Блокируем билет
    SELECT t.ticket_id, t.status, t.user_id, t.event_id,
           e.title as event_title, u.full_name as holder_name
    INTO v_ticket
    FROM tickets t
    JOIN events e ON e.event_id = t.event_id
    JOIN users u ON u.user_id = t.user_id
    WHERE t.ticket_code = p_ticket_code::UUID
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, NULL, NULL, 'Билет не найден';
        RETURN;
    END IF;

    IF v_ticket.status = 'used' THEN
        RETURN QUERY SELECT FALSE, NULL, NULL, 'Билет уже был использован';
        RETURN;
    END IF;

    IF v_ticket.status = 'cancelled' THEN
        RETURN QUERY SELECT FALSE, NULL, NULL, 'Билет отменён';
        RETURN;
    END IF;

    -- Отмечаем вход
    UPDATE tickets 
    SET status = 'used', used_at = CURRENT_TIMESTAMP
    WHERE ticket_id = v_ticket.ticket_id;

    -- Записываем отметку
    INSERT INTO check_ins (ticket_id, checked_by, notes)
    VALUES (v_ticket.ticket_id, p_admin_id, p_note);

    RETURN QUERY SELECT 
        TRUE, 
        v_ticket.event_title, 
        v_ticket.holder_name, 
        'Отметка успешно выполнена';
END;
$$ LANGUAGE plpgsql;


-- Процедура отмены билета
CREATE OR REPLACE FUNCTION sp_cancel_ticket(
    p_ticket_code TEXT,
    p_user_id INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    v_ticket RECORD;
BEGIN
    SELECT ticket_id, status, user_id, event_id
    INTO v_ticket
    FROM tickets
    WHERE ticket_code = p_ticket_code::UUID
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    -- Проверяем права (только владелец или админ)
    IF v_ticket.user_id != p_user_id THEN
        -- Проверим, может пользователь админ?
        IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = p_user_id AND role = 'admin') THEN
            RETURN FALSE;
        END IF;
    END IF;

    IF v_ticket.status != 'active' THEN
        RETURN FALSE;
    END IF;

    -- Проверяем, что мероприятие ещё не началось
    IF EXISTS (SELECT 1 FROM events WHERE event_id = v_ticket.event_id AND starts_at <= CURRENT_TIMESTAMP) THEN
        RETURN FALSE;
    END IF;

    UPDATE tickets 
    SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP
    WHERE ticket_id = v_ticket.ticket_id;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
