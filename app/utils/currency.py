import requests
from datetime import datetime
from app.models import ExchangeRate
from app import db
from flask import current_app

def update_exchange_rates(base='USD'):
    """Fetch latest rates from API and store in database."""
    api_key = current_app.config.get('EXCHANGE_RATE_API_KEY')
    if not api_key:
        return
    url = f"https://api.exchangerate-api.com/v4/latest/{base}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        for currency, rate in data['rates'].items():
            # Store or update
            exch = ExchangeRate.query.filter_by(base_currency=base, target_currency=currency).first()
            if exch:
                exch.rate = rate
                exch.date = datetime.utcnow().date()
            else:
                exch = ExchangeRate(base_currency=base, target_currency=currency, rate=rate)
                db.session.add(exch)
        db.session.commit()