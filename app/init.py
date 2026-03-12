from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Register blueprints
    from app.routes import auth, main, wallets, transactions, categories, budgets, savings, bills, debts, reports, sync, settings
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(wallets.bp, url_prefix='/wallets')
    app.register_blueprint(transactions.bp, url_prefix='/transactions')
    app.register_blueprint(categories.bp, url_prefix='/categories')
    app.register_blueprint(budgets.bp, url_prefix='/budgets')
    app.register_blueprint(savings.bp, url_prefix='/savings')
    app.register_blueprint(bills.bp, url_prefix='/bills')
    app.register_blueprint(debts.bp, url_prefix='/debts')
    app.register_blueprint(reports.bp, url_prefix='/reports')
    app.register_blueprint(sync.bp, url_prefix='/sync')
    app.register_blueprint(settings.bp, url_prefix='/settings')

    return app