from flask import Flask
from config import Config
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ... (extensions init) ...

    # Import blueprints individually
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

    return app