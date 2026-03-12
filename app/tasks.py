from celery import Celery
from app import create_app, db
from app.models import RecurringTransaction, Transaction, Wallet, Bill, User, Budget, FinancialInsight
from app.utils.notifications import send_budget_alert, send_bill_reminder
from app.utils.insights import calculate_financial_health_score, generate_spending_insights
from datetime import datetime, timedelta
from sqlalchemy import func

celery = Celery(__name__, broker='redis://localhost:6379/0')
app = create_app()
celery.conf.update(app.config)

class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask

@celery.task
def process_recurring_transactions():
    """Create transactions for recurring items due today."""
    today = datetime.utcnow().date()
    recurring = RecurringTransaction.query.filter(
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_date <= today
    ).all()
    for r in recurring:
        t = Transaction(
            amount=r.amount,
            type=r.type,
            description=r.description,
            notes=r.notes,
            date=datetime.combine(today, datetime.min.time()),
            wallet_id=r.wallet_id,
            category_id=r.category_id,
            user_id=r.user_id,
            is_recurring=True,
            recurring_id=r.id
        )
        db.session.add(t)
        wallet = Wallet.query.get(r.wallet_id)
        if r.type == 'income':
            wallet.balance += r.amount
        else:
            wallet.balance -= r.amount
        # Update next_date
        if r.frequency == 'daily':
            r.next_date = today + timedelta(days=r.interval)
        elif r.frequency == 'weekly':
            r.next_date = today + timedelta(weeks=r.interval)
        elif r.frequency == 'monthly':
            # Add months (simplified)
            next_month = today.replace(day=1) + timedelta(days=32*r.interval)
            r.next_date = next_month.replace(day=min(today.day, 28))
        elif r.frequency == 'yearly':
            r.next_date = today.replace(year=today.year + r.interval)
        if r.end_date and r.next_date > r.end_date:
            r.is_active = False
        db.session.commit()

@celery.task
def check_budget_alerts():
    """Send alerts for budgets exceeding threshold."""
    today = datetime.now().date()
    budgets = Budget.query.filter_by(is_active=True).all()
    for b in budgets:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == b.user_id,
            Transaction.category_id == b.category_id,
            Transaction.type == 'expense',
            Transaction.date >= b.start_date,
            Transaction.date <= (b.end_date or today)
        ).scalar() or 0.0
        if b.amount > 0 and (spent / b.amount) * 100 >= b.alert_threshold:
            # Check if alert already sent recently (e.g., last 7 days)
            user = User.query.get(b.user_id)
            if user and user.preferences and user.preferences.email_notifications:
                send_budget_alert(user, b, spent)

@celery.task
def send_bill_reminders():
    """Send reminders for bills due soon."""
    today = datetime.now().date()
    bills = Bill.query.filter_by(is_active=True).all()
    for bill in bills:
        # Calculate next due date (simplified)
        if bill.frequency == 'monthly':
            # ... (as in bills route)
            pass
        if bill.next_due and (bill.next_due - today).days <= bill.reminder_days:
            user = User.query.get(bill.user_id)
            if user and user.preferences and user.preferences.email_notifications:
                send_bill_reminder(user, bill)

@celery.task
def generate_daily_insights():
    """Generate financial insights for all active users."""
    users = User.query.filter_by(is_active=True).all()
    for user in users:
        generate_spending_insights(user.id)
        # Also update health score periodically
        score = calculate_financial_health_score(user.id)
        # Could store in User model or separate table