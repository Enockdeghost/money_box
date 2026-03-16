import os
import re
from dotenv import load_dotenv

load_dotenv()

def get_database_uri():
    """Return the database URI, converting postgres:// or postgresql:// to postgresql+pg8000://."""
    raw_uri = os.environ.get('DATABASE_URL', 'sqlite:///moneybox.db')
    if raw_uri.startswith('postgres://') or raw_uri.startswith('postgresql://'):
        # Use regex to replace the scheme
        raw_uri = re.sub(r'^postgres(ql)?://', 'postgresql+pg8000://', raw_uri)
    return raw_uri

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key'
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app/static/uploads')
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
