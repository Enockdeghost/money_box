from flask import Flask
from config import Config
from app.extensions import db, migrate, login_manager, mail
import logging
import os
from logging.handlers import RotatingFileHandler

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Debug: print the database URI
    print("CONFIG LOADED. DATABASE URI:", app.config.get('SQLALCHEMY_DATABASE_URI'))

    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        print("WARNING: SQLALCHEMY_DATABASE_URI not set, using fallback sqlite:///moneybox.db")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moneybox.db'

    if not app.config.get('SECRET_KEY'):
        print("WARNING: SECRET_KEY not set, using fallback dev-secret-key")
        app.config['SECRET_KEY'] = 'dev-secret-key'

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Logging configuration (only in non-debug mode)
    if not app.debug:
       

        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(os.path.join(log_dir, 'moneybox.log'), maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    # Import blueprints inside the factory to avoid circular imports
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