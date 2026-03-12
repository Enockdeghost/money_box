from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Wallet, Transaction, Budget, SavingsGoal, Bill
from datetime import datetime, timedelta
from sqlalchemy import func

bp = Blueprint('main', __name__)

@bp.route('/')
def landing():
    """Public landing page."""
    return render_template('landing.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Protected dashboard for logged-in users."""
    # Net worth
    wallets = Wallet.query.filter_by(user_id=current_user.id, is_hidden=False).all()
    net_worth = sum(w.balance for w in wallets)

    # This month's income/expense
    today = datetime.now().date()
    month_start = today.replace(day=1)
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= month_start
    ).all()
    total_income = sum(t.amount for t in transactions if t.type == 'income')
    total_expense = sum(t.amount for t in transactions if t.type == 'expense')

    # Recent transactions
    recent = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(10).all()

    # Budget progress
    budgets = Budget.query.filter_by(user_id=current_user.id, is_active=True).all()
    budget_data = []
    for b in budgets:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == b.category_id,
            Transaction.type == 'expense',
            Transaction.date >= b.start_date,
            Transaction.date <= (b.end_date or today)
        ).scalar() or 0.0
        budget_data.append({
            'budget': b,
            'spent': spent,
            'remaining': b.amount - spent,
            'progress': (spent / b.amount * 100) if b.amount else 0
        })

    # Upcoming bills (next 7 days)
    bills = Bill.query.filter_by(user_id=current_user.id, is_active=True).all()
    upcoming_bills = []
    for bill in bills:
        if bill.next_due and bill.next_due >= today and bill.next_due <= today + timedelta(days=7):
            upcoming_bills.append(bill)

    # Chart data (simplified – you may want to compute real trends)
    months = []
    income_trend = []
    expense_trend = []
    for i in range(5, -1, -1):
        month = today.replace(day=1) - timedelta(days=i*30)
        months.append(month.strftime('%b %Y'))
        income_trend.append(0)
        expense_trend.append(0)

    cat_labels = []
    cat_data = []
    cat_colors = []

    return render_template('dashboard.html',
                           net_worth=net_worth,
                           total_income=total_income,
                           total_expense=total_expense,
                           recent_transactions=recent,
                           budget_data=budget_data,
                           upcoming_bills=upcoming_bills,
                           months=months,
                           income_trend=income_trend,
                           expense_trend=expense_trend,
                           cat_labels=cat_labels,
                           cat_data=cat_data,
                           cat_colors=cat_colors)