"""Административные маршруты: управление событиями, отчёты, контроль входа."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime

from app import models
from app.utils import (
    export_event_sales_xlsx, export_daily_revenue_xlsx,
    export_attendance_xlsx, export_dealer_stats_xlsx
)

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Декоратор: доступ только для администраторов."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@bp.route('/')
@login_required
@admin_required
def dashboard():
    """Админ-панель: сводная статистика."""
    stats = models.admin_dashboard_stats()
    revenue = models.report_daily_revenue(days=14)
    return render_template('dashboard.html', stats=stats, revenue=revenue)


# =====================================================================
# Управление событиями
# =====================================================================

@bp.route('/events')
@login_required
@admin_required
def events_list():
    """Список всех мероприятий для админки."""
    events = models.list_all_events()
    return render_template('events_list.html', events=events)


@bp.route('/events/create', methods=['GET', 'POST'])
@login_required
@admin_required
def event_create():
    """Создание нового мероприятия."""
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'venue_id': request.form.get('venue_id') or None,
            'starts_at': request.form.get('starts_at'),
            'ends_at': request.form.get('ends_at'),
            'total_capacity': request.form.get('total_capacity', type=int),
            'base_price': request.form.get('base_price', 0, type=float),
            'status': request.form.get('status', 'draft'),
        }
        event_id = models.create_event(data, created_by=current_user.id)
        flash('Мероприятие создано', 'success')
        return redirect(url_for('admin.events_list'))

    venues = models.list_venues()
    return render_template('event_form.html', event=None, venues=venues)


@bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def event_edit(event_id):
    """Редактирование мероприятия."""
    event = models.get_event(event_id)
    if not event:
        abort(404)

    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'venue_id': request.form.get('venue_id') or None,
            'starts_at': request.form.get('starts_at'),
            'ends_at': request.form.get('ends_at'),
            'total_capacity': request.form.get('total_capacity', type=int),
            'base_price': request.form.get('base_price', 0, type=float),
            'status': request.form.get('status', 'draft'),
        }
        models.update_event(event_id, data)
        flash('Мероприятие обновлено', 'success')
        return redirect(url_for('admin.events_list'))

    venues = models.list_venues()
    return render_template('event_form.html', event=event, venues=venues)


@bp.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def event_delete(event_id):
    """Удаление мероприятия."""
    models.delete_event(event_id)
    flash('Мероприятие удалено', 'success')
    return redirect(url_for('admin.events_list'))


# =====================================================================
# Контроль входа (сканирование QR)
# =====================================================================

@bp.route('/check-in', methods=['GET'])
@login_required
@admin_required
def check_in():
    """Страница контроля входа."""
    return render_template('check_in.html', result=None, error=None)


@bp.route('/api/check-in', methods=['POST'])
@login_required
@admin_required
def api_check_in():
    """API для AJAX-отметки билета."""
    data = request.get_json()
    ticket_code = data.get('code', '').strip()

    if not ticket_code:
        return jsonify({'ok': False, 'error': 'Не указан код билета'}), 400

    try:
        result = models.check_in_ticket(ticket_code, admin_id=current_user.id)
        return jsonify({
            'ok': True,
            'event_title': result.get('event_title'),
            'holder_name': result.get('holder_name'),
            'checked_at': datetime.now().isoformat(),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# =====================================================================
# Отчёты
# =====================================================================

@bp.route('/reports')
@login_required
@admin_required
def reports():
    """Страница со всеми отчётами."""
    sales = models.report_event_sales()
    revenue = models.report_daily_revenue()
    attendance = models.report_attendance()
    dealers = models.report_dealer_stats()

    return render_template(
        'reports.html',
        sales=sales,
        revenue=revenue,
        attendance=attendance,
        dealers=dealers
    )


@bp.route('/reports/export/<kind>')
@login_required
@admin_required
def reports_export(kind):
    """Экспорт отчётов в Excel."""
    if kind == 'sales':
        rows = models.report_event_sales()
        data = export_event_sales_xlsx(rows)
        filename = f'event_sales_{datetime.now().strftime("%Y%m%d")}.xlsx'
    elif kind == 'revenue':
        rows = models.report_daily_revenue(days=90)
        data = export_daily_revenue_xlsx(rows)
        filename = f'daily_revenue_{datetime.now().strftime("%Y%m%d")}.xlsx'
    elif kind == 'attendance':
        rows = models.report_attendance()
        data = export_attendance_xlsx(rows)
        filename = f'attendance_{datetime.now().strftime("%Y%m%d")}.xlsx'
    elif kind == 'dealers':
        rows = models.report_dealer_stats()
        data = export_dealer_stats_xlsx(rows)
        filename = f'dealer_stats_{datetime.now().strftime("%Y%m%d")}.xlsx'
    else:
        abort(404)

    return send_file(
        BytesIO(data),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
