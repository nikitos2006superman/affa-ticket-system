"""Маршруты авторизации: вход, регистрация, выход."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import models

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Заполните все поля', 'error')
            return render_template('login.html')

        user = models.verify_password(email, password)
        if user:
            login_user(user)
            flash(f'Добро пожаловать, {user.full_name}!', 'success')
            return redirect(url_for('public.index'))
        else:
            flash('Неверный email или пароль', 'error')

    return render_template('login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip() or None
        organization = request.form.get('organization', '').strip() or None
        dealer_code = request.form.get('dealer_code', '').strip() or None

        errors = []
        if not email:
            errors.append('Email обязателен')
        if not password:
            errors.append('Пароль обязателен')
        if password != password_confirm:
            errors.append('Пароли не совпадают')
        if not full_name:
            errors.append('Укажите имя и фамилию')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html')

        existing = models.find_user_by_email(email)
        if existing:
            flash('Пользователь с таким email уже зарегистрирован', 'error')
            return render_template('register.html')

        try:
            models.create_user(
                email=email,
                password=password,
                full_name=full_name,
                phone=phone,
                organization=organization,
                dealer_code=dealer_code,
                role='user'
            )
            flash('Регистрация успешна! Теперь войдите в систему.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Ошибка при регистрации: {e}', 'error')

    return render_template('register.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('public.index'))
