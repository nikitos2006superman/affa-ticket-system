-- ============================================================
-- Триггеры для аудита и проверок
-- ============================================================

-- Функция для аудита изменений
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, operation, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.ticket_id, 'INSERT', to_jsonb(NEW), NULL);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, operation, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.ticket_id, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW), NULL);
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, operation, old_data, changed_by)
        VALUES (TG_TABLE_NAME, OLD.ticket_id, 'DELETE', to_jsonb(OLD), NULL);
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Триггер аудита для билетов
DROP TRIGGER IF EXISTS audit_tickets_trigger ON tickets;
CREATE TRIGGER audit_tickets_trigger
    AFTER INSERT OR UPDATE OR DELETE ON tickets
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Триггер проверки вместимости (дублирующий защиту)
CREATE OR REPLACE FUNCTION check_capacity_trigger()
RETURNS TRIGGER AS $$
DECLARE
    v_sold INTEGER;
    v_capacity INTEGER;
BEGIN
    -- Для INSERT и UPDATE статуса на active
    IF NEW.status = 'active' THEN
        SELECT e.total_capacity, COUNT(t.ticket_id)
        INTO v_capacity, v_sold
        FROM events e
        LEFT JOIN tickets t ON t.event_id = e.event_id AND t.status IN ('active', 'used')
        WHERE e.event_id = NEW.event_id
        GROUP BY e.event_id;
        
        IF v_sold > v_capacity THEN
            RAISE EXCEPTION 'Превышена вместимость мероприятия (максимум %)', v_capacity;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS check_capacity_trigger ON tickets;
CREATE TRIGGER check_capacity_trigger
    BEFORE INSERT OR UPDATE OF status ON tickets
    FOR EACH ROW
    WHEN (NEW.status = 'active')
    EXECUTE FUNCTION check_capacity_trigger();

-- Авто-обновление updated_at в events
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_events_updated_at ON events;
CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
