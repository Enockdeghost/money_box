from app import db
from app.models import Transaction, Category, Budget, FinancialInsight, User
from datetime import datetime, timedelta
from sqlalchemy import func

def calculate_financial_health_score(user_id):
    """Return a score from 0-100 based on multiple factors."""
    user = User.query.get(user_id)
    if not user:
        return 0
    today = datetime.now().date()
    # Factor 1: Savings rate (income - expense) / income for last 3 months
    three_months_ago = today - timedelta(days=90)
    income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= three_months_ago
    ).scalar() or 0
    expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= three_months_ago
    ).scalar() or 0
    if income > 0:
        savings_rate = (income - expense) / income
    else:
        savings_rate = 0
    score = min(savings_rate * 50, 50)  # up to 50 points

    # Factor 2: Budget adherence (average % of budgets not exceeded)
    budgets = Budget.query.filter_by(user_id=user_id, is_active=True).all()
    if budgets:
        total_budget_score = 0
        for b in budgets:
            spent = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == b.category_id,
                Transaction.type == 'expense',
                Transaction.date >= b.start_date,
                Transaction.date <= (b.end_date or today)
            ).scalar() or 0
            if b.amount > 0:
                ratio = spent / b.amount
                if ratio <= 1:
                    budget_score = (1 - ratio) * 20  # 0-20
                else:
                    budget_score = max(0, 20 - (ratio - 1) * 10)
                total_budget_score += budget_score
        avg_budget_score = total_budget_score / len(budgets)
        score += avg_budget_score

    # Factor 3: Debt-to-income ratio (lower is better)
    from app.models import Debt
    total_debt = db.session.query(func.sum(Debt.remaining_amount)).filter_by(user_id=user_id, is_paid=False).scalar() or 0
    monthly_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= today.replace(day=1)
    ).scalar() or 1  # avoid division by zero
    if monthly_income > 0:
        debt_ratio = total_debt / monthly_income
        if debt_ratio < 3:
            score += 30
        elif debt_ratio < 6:
            score += 20
        else:
            score += 10
    else:
        score += 15

    return min(int(score), 100)

def generate_spending_insights(user_id):
    """Create FinancialInsight records for the user."""
    today = datetime.now().date()
    insights = []
    # Compare current month spending to previous month
    current_start = today.replace(day=1)
    prev_start = (current_start - timedelta(days=1)).replace(day=1)
    prev_end = current_start - timedelta(days=1)
    current_spent = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= current_start
    ).scalar() or 0
    prev_spent = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= prev_start,
        Transaction.date <= prev_end
    ).scalar() or 0
    if prev_spent > 0:
        change = (current_spent - prev_spent) / prev_spent
        if change > 0.2:
            insights.append(FinancialInsight(
                user_id=user_id,
                insight_type='spending_increase',
                title='Spending increased',
                description=f'Your spending this month is {change*100:.0f}% higher than last month.',
                data={'change': change}
            ))
        elif change < -0.2:
            insights.append(FinancialInsight(
                user_id=user_id,
                insight_type='spending_decrease',
                title='Great job!',
                description=f'Your spending this month is {abs(change)*100:.0f}% lower than last month.',
                data={'change': change}
            ))
    # Top category suggestion
    top_cat = db.session.query(
        Category.name, func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= current_start
    ).group_by(Category.id).order_by(func.sum(Transaction.amount).desc()).first()
    if top_cat and top_cat[1] > current_spent * 0.3:
        insights.append(FinancialInsight(
            user_id=user_id,
            insight_type='top_category',
            title=f'High spending on {top_cat[0]}',
            description=f'You spent {top_cat[1]/current_spent*100:.0f}% of your budget on {top_cat[0]}.',
            data={'category': top_cat[0], 'percentage': top_cat[1]/current_spent}
        ))
    # Save insights
    for ins in insights:
        db.session.add(ins)
    db.session.commit()
    return insights

def detect_fraud_alerts(user_id):
    """Detect unusual transactions (e.g., large amount, foreign currency, etc.)."""
    alerts = []
    # Large transaction: > 3x average transaction amount
    avg_amount = db.session.query(func.avg(Transaction.amount)).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense'
    ).scalar() or 0
    large_tx = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.amount > 3 * avg_amount,
        Transaction.date >= datetime.now().date() - timedelta(days=2)
    ).first()
    if large_tx:
        alerts.append({
            'type': 'large_transaction',
            'transaction_id': large_tx.id,
            'message': f'Unusually large transaction: ${large_tx.amount}'
        })
    # Foreign transactions (if location not in user's country) – requires user profile country
    return alerts