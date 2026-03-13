from celery import Celery
from app import create_app, db
from app.models import RecurringTransaction, SavingsGoal, Transaction, Wallet, Bill, User, Budget, FinancialInsight
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

@celery.task
def check_subscription_alerts():
    from app.models import Subscription, User
    from datetime import date, timedelta
    from app.utils.notifications import send_subscription_reminder

    today = date.today()
    upcoming = Subscription.query.filter(
        Subscription.active == True,
        Subscription.next_billing_date <= today + timedelta(days=Subscription.reminder_days),
        Subscription.next_billing_date >= today
    ).all()
    for sub in upcoming:
        user = User.query.get(sub.user_id)
        if user:
            send_subscription_reminder(user, sub)

@celery.task
def update_health_score(user_id):
    from app.models import User, Transaction, Budget, Debt
    from datetime import datetime, timedelta
    from decimal import Decimal

    user = User.query.get(user_id)
    if not user:
        return

    today = datetime.now().date()
    three_months_ago = today - timedelta(days=90)

    # Income and expense
    income = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= three_months_ago
    ).scalar() or 0
    expense = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= three_months_ago
    ).scalar() or 0

    # Savings rate (max 30)
    if income > 0:
        savings_rate = (income - expense) / income
    else:
        savings_rate = 0
    score = min(savings_rate * 30, 30)

    # Budget adherence (max 30)
    budgets = Budget.query.filter_by(user_id=user_id, is_active=True).all()
    if budgets:
        budget_score_sum = 0
        for b in budgets:
            spent = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == b.category_id,
                Transaction.type == 'expense',
                Transaction.date >= b.start_date,
                Transaction.date <= (b.end_date or today)
            ).scalar() or 0
            if b.amount > 0:
                ratio = spent / b.amount
                budget_score_sum += max(30 - (ratio - 1) * 30, 0) if ratio > 1 else 30
        score += budget_score_sum / len(budgets)

    # Debt-to-income (max 20)
    total_debt = db.session.query(db.func.sum(Debt.remaining_amount)).filter_by(user_id=user_id, is_paid=False).scalar() or 0
    monthly_income = income / 3  # average monthly income over 3 months
    if monthly_income > 0:
        debt_ratio = total_debt / monthly_income
        if debt_ratio < 3:
            score += 20
        elif debt_ratio < 6:
            score += 15
        else:
            score += 10
    else:
        score += 15

    # Consistency (max 20) – e.g., logged in regularly, added transactions frequently
    # Simplified: just give 10 if they've used the app for >30 days
    if user.created_at and (datetime.now() - user.created_at).days > 30:
        score += 10
    else:
        score += 5

    user.health_score = int(score)
    user.health_score_updated_at = datetime.now()
    db.session.commit()

    # Check for achievements
    check_achievements(user_id)

def check_achievements(user_id):
    from app.models import Achievement
    user = User.query.get(user_id)
    achievements = []

    # First transaction
    if Transaction.query.filter_by(user_id=user_id).count() >= 1:
        if not Achievement.query.filter_by(user_id=user_id, name='First Transaction').first():
            achievements.append(Achievement(user_id=user_id, name='First Transaction', description='You recorded your first transaction!'))

    # Budget set
    if Budget.query.filter_by(user_id=user_id).count() >= 1:
        if not Achievement.query.filter_by(user_id=user_id, name='Budget Master').first():
            achievements.append(Achievement(user_id=user_id, name='Budget Master', description='You created your first budget.'))

    # Goal achieved
    if SavingsGoal.query.filter_by(user_id=user_id, is_completed=True).count() >= 1:
        if not Achievement.query.filter_by(user_id=user_id, name='Goal Crusher').first():
            achievements.append(Achievement(user_id=user_id, name='Goal Crusher', description='You achieved a savings goal!'))

    # etc.

    if achievements:
        db.session.add_all(achievements)
        db.session.commit()