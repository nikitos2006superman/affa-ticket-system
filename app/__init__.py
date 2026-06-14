"""Фабрика Flask-приложения."""

from flask import Flask
from flask_login import LoginManager

from app.config import Config
from app import db, models


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # БД
    db.init_app(app)

    # Авторизация
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для продолжения войдите в систему'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return models.find_user_by_id(int(user_id))
        except (ValueError, TypeError):
            return None

    # Blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.public import bp as public_bp
    from app.routes.admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    # Контекст-процессоры
    from datetime import datetime

    @app.context_processor
    def inject_globals():
        return {'now': datetime.now()}

    # Шаблонные фильтры
    @app.template_filter('dt')
    def fmt_dt(value, fmt='%d.%m.%Y %H:%M'):
        if value is None:
            return ''
        return value.strftime(fmt)

    @app.template_filter('money')
    def fmt_money(value):
        if value is None:
            return ''
        try:
            return f'{float(value):,.2f} ₽'.replace(',', ' ')
        except (TypeError, ValueError):
            return str(value)

    return app
