-- ============================================================
-- Представления для отчётов
-- ============================================================

-- Продажи по событиям
CREATE OR REPLACE VIEW v_event_sales AS
SELECT 
    e.event_id,
    e.title,
    e.starts_at,
    e.status,
    e.total_capacity,
    COUNT(t.ticket_id) FILTER (WHERE t.status IN ('active', 'used')) AS sold_count,
    e.total_capacity - COUNT(t.ticket_id) FILTER (WHERE t.status IN ('active', 'used')) AS available,
    ROUND(100.0 * COUNT(t.ticket_id) FILTER (WHERE t.status IN ('active', 'used')) / e.total_capacity, 1) AS fill_rate_pct,
    COUNT(t.ticket_id) FILTER (WHERE t.status = 'active') AS tickets_active,
    COUNT(t.ticket_id) FILTER (WHERE t.status = 'used') AS tickets_used,
    COUNT(t.ticket_id) FILTER (WHERE t.status = 'cancelled') AS tickets_cancelled,
    COALESCE(SUM(t.price_paid) FILTER (WHERE t.status IN ('active', 'used')), 0) AS revenue
FROM events e
LEFT JOIN tickets t ON t.event_id = e.event_id
GROUP BY e.event_id, e.title, e.starts_at, e.status, e.total_capacity
ORDER BY e.starts_at DESC;


-- Ежедневная выручка
CREATE OR REPLACE VIEW v_daily_revenue AS
SELECT 
    DATE(t.created_at) AS sale_date,
    COUNT(t.ticket_id) AS tickets_sold,
    COUNT(DISTINCT t.user_id) AS unique_buyers,
    COUNT(DISTINCT t.event_id) AS events_with_sales,
    COALESCE(SUM(t.price_paid), 0) AS gross_revenue,
    COALESCE(SUM(CASE WHEN t.status = 'cancelled' THEN t.price_paid ELSE 0 END), 0) AS refunded_amount,
    COALESCE(SUM(CASE WHEN t.status IN ('active', 'used') THEN t.price_paid ELSE 0 END), 0) AS net_revenue
FROM tickets t
WHERE t.status != 'refunded'
GROUP BY DATE(t.created_at)
ORDER BY sale_date DESC;


-- Посещаемость мероприятий
CREATE OR REPLACE VIEW v_event_attendance AS
SELECT 
    e.event_id,
    e.title,
    e.starts_at,
    COUNT(t.ticket_id) AS tickets_issued,
    COUNT(t.ticket_id) FILTER (WHERE t.status = 'used') AS attended,
    COUNT(t.ticket_id) FILTER (WHERE t.status = 'active') AS no_shows,
    ROUND(100.0 * COUNT(t.ticket_id) FILTER (WHERE t.status = 'used') / NULLIF(COUNT(t.ticket_id), 0), 1) AS attendance_rate_pct
FROM events e
LEFT JOIN tickets t ON t.event_id = e.event_id
WHERE e.status = 'finished' OR e.ends_at < CURRENT_TIMESTAMP
GROUP BY e.event_id, e.title, e.starts_at
ORDER BY e.starts_at DESC;


-- Статистика по дилерам
CREATE OR REPLACE VIEW v_dealer_stats AS
SELECT 
    u.dealer_code,
    u.organization,
    COUNT(DISTINCT u.user_id) AS users_count,
    COUNT(t.ticket_id) AS tickets_total,
    COUNT(t.ticket_id) FILTER (WHERE t.status = 'used') AS tickets_attended,
    COUNT(t.ticket_id) FILTER (WHERE t.status = 'cancelled') AS tickets_cancelled,
    COUNT(DISTINCT CASE WHEN t.status = 'used' THEN t.event_id END) AS events_visited,
    ROUND(100.0 * COUNT(t.ticket_id) FILTER (WHERE t.status = 'used') / NULLIF(COUNT(t.ticket_id), 0), 1) AS attendance_rate_pct
FROM users u
LEFT JOIN tickets t ON t.user_id = u.user_id
WHERE u.dealer_code IS NOT NULL AND u.role = 'user'
GROUP BY u.user_id, u.dealer_code, u.organization
HAVING COUNT(t.ticket_id) > 0
ORDER BY attendance_rate_pct DESC;
