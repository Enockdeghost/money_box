import sys
import os
import re
from flask import Flask
from app.extensions import db, migrate, login_manager, mail
import logging
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_uri():
    """Return the database URI, converting to pg8000 dialect if needed."""
    raw_uri = os.environ.get('DATABASE_URL', 'sqlite:///moneybox.db')
    if raw_uri.startswith('postgres://') or raw_uri.startswith('postgresql://'):
        raw_uri = re.sub(r'^postgres(ql)?://', 'postgresql+pg8000://', raw_uri)
    return raw_uri

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key'
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Redis for Celery
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # Exchange rate API (optional)
    EXCHANGE_RATE_API_KEY = os.environ.get('EXCHANGE_RATE_API_KEY')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Debug: print the database URI (visible in Render logs)
    print("CONFIG LOADED. DATABASE URI:", app.config.get('SQLALCHEMY_DATABASE_URI'))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Logging configuration (only in non-debug mode)
    if not app.debug:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_handler = RotatingFileHandler(os.path.join(log_dir, 'moneybox.log'), maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    # Import blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.main import bp as main_bp
    from app.routes.wallets import bp as wallets_bp
    from app.routes.transactions import bp as transactions_bp
    from app.routes.categories import bp as categories_bp
    from app.routes.budgets import bp as budgets_bp
    from app.routes.savings import bp as savings_bp
    from app.routes.bills import bp as bills_bp
    from app.routes.debts import bp as debts_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.sync import bp as sync_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.subscriptions import bp as subscriptions_bp
    from app.routes.admin import bp as admin_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(wallets_bp, url_prefix='/wallets')
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(budgets_bp, url_prefix='/budgets')
    app.register_blueprint(savings_bp, url_prefix='/savings')
    app.register_blueprint(bills_bp, url_prefix='/bills')
    app.register_blueprint(debts_bp, url_prefix='/debts')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(sync_bp, url_prefix='/sync')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(subscriptions_bp, url_prefix='/subscriptions')
    app.register_blueprint(admin_bp)

    return app
