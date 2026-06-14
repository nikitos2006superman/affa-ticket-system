"""Публичные маршруты: афиша, детали мероприятия, покупка билетов, личный кабинет."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user
from io import BytesIO

from app import models
from app.utils import make_qr_png

bp = Blueprint('public', __name__)


@bp.route('/')
def index():
    """Афиша мероприятий."""
    search = request.args.get('q', '').strip()
    events = models.list_published_events(search=search)
    return render_template('index.html', events=events, search=search)


@bp.route('/event/<int:event_id>')
def event_detail(event_id):
    """Детальная страница мероприятия."""
    event = models.get_event(event_id)
    if not event:
        abort(404)
    return render_template('event_detail.html', event=event)


@bp.route('/event/<int:event_id>/buy', methods=['POST'])
@login_required
def buy_ticket(event_id):
    """Покупка/регистрация на мероприятие."""
    if current_user.is_admin:
        flash('Администраторы не могут регистрироваться на мероприятия как участники', 'error')
        return redirect(url_for('public.event_detail', event_id=event_id))

    quantity = int(request.form.get('quantity', 1))

    try:
        transaction_id, ticket_codes = models.purchase_ticket(
            user_id=current_user.id,
            event_id=event_id,
            quantity=quantity
        )
        flash(f'Успешно зарегистрировано билетов: {len(ticket_codes)}', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('public.my_tickets'))


@bp.route('/my-tickets')
@login_required
def my_tickets():
    """Личный кабинет — список билетов пользователя."""
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    tickets = models.list_user_tickets(current_user.id)
    return render_template('my_tickets.html', tickets=tickets)


@bp.route('/my-tickets/<ticket_code>/cancel', methods=['POST'])
@login_required
def cancel_my_ticket(ticket_code):
    """Отмена регистрации пользователем."""
    if current_user.is_admin:
        flash('Действие недоступно для администратора', 'error')
        return redirect(url_for('public.my_tickets'))

    ok = models.cancel_ticket(ticket_code, current_user.id)
    if ok:
        flash('Регистрация отменена', 'success')
    else:
        flash('Не удалось отменить регистрацию', 'error')

    return redirect(url_for('public.my_tickets'))


@bp.route('/qr/<ticket_code>.png')
@login_required
def qr_image(ticket_code):
    """Генерация QR-кода для билета."""
    ticket = models.get_ticket_by_code(ticket_code)
    if not ticket:
        abort(404)

    # Проверка прав: владелец билета или админ
    if not current_user.is_admin and ticket['user_id'] != current_user.id:
        abort(403)

    qr_data = f"https://affa.events/check/{ticket_code}"
    img_bytes = make_qr_png(qr_data)
    return send_file(BytesIO(img_bytes), mimetype='image/png')
