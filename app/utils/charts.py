from app import db
from app.models import Transaction, Category, Wallet, Budget
from sqlalchemy import func, extract, and_
from datetime import datetime, timedelta
from collections import defaultdict

def category_pie_data(user_id, start_date, end_date, transaction_type='expense'):
    """Return data for a pie chart: category breakdown."""
    categories = Category.query.filter_by(user_id=user_id, type=transaction_type).all()
    labels = []
    data = []
    colors = []
    for cat in categories:
        total = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == cat.id,
            Transaction.type == transaction_type,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar() or 0.0
        if total > 0:
            labels.append(cat.name)
            data.append(float(total))
            colors.append(cat.color)
    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': colors,
            'hoverOffset': 4
        }]
    }

def income_expense_trend(user_id, start_date, end_date, group_by='month'):
    """Return data for line/bar chart: income vs expense over time."""
    # Determine date grouping
    if group_by == 'month':
        # Group by month
        months = []
        income_data = []
        expense_data = []
        current = start_date.replace(day=1)
        while current <= end_date:
            next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'income',
                Transaction.date >= current,
                Transaction.date < next_month
            ).scalar() or 0.0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'expense',
                Transaction.date >= current,
                Transaction.date < next_month
            ).scalar() or 0.0
            months.append(current.strftime('%b %Y'))
            income_data.append(float(inc))
            expense_data.append(float(exp))
            current = next_month
        labels = months
    elif group_by == 'week':
        # Group by week (simplified: week numbers)
        weeks = []
        income_data = []
        expense_data = []
        current = start_date
        while current <= end_date:
            week_end = current + timedelta(days=6)
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'income',
                Transaction.date >= current,
                Transaction.date <= week_end
            ).scalar() or 0.0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'expense',
                Transaction.date >= current,
                Transaction.date <= week_end
            ).scalar() or 0.0
            weeks.append(f"Week {current.isocalendar()[1]}")
            income_data.append(float(inc))
            expense_data.append(float(exp))
            current = week_end + timedelta(days=1)
        labels = weeks
    else:  # day
        days = []
        income_data = []
        expense_data = []
        current = start_date
        while current <= end_date:
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'income',
                Transaction.date == current
            ).scalar() or 0.0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'expense',
                Transaction.date == current
            ).scalar() or 0.0
            days.append(current.strftime('%Y-%m-%d'))
            income_data.append(float(inc))
            expense_data.append(float(exp))
            current += timedelta(days=1)
        labels = days

    return {
        'labels': labels,
        'datasets': [
            {'label': 'Income', 'data': income_data, 'borderColor': '#28a745', 'backgroundColor': 'rgba(40,167,69,0.1)'},
            {'label': 'Expense', 'data': expense_data, 'borderColor': '#dc3545', 'backgroundColor': 'rgba(220,53,69,0.1)'}
        ]
    }

def net_worth_history(user_id, start_date, end_date):
    """Calculate net worth over time (daily)."""
    # This requires knowing wallet balances at each date.
    # Approach: start from earliest date with balance = sum of initial wallet balances,
    # then apply transactions day by day.
    wallets = Wallet.query.filter_by(user_id=user_id).all()
    if not wallets:
        return {'labels': [], 'data': []}
    
    # Get all transactions in range, ordered by date
    transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date).all()
    
    # Get initial balances as of day before start_date
    # We need to sum all transactions before start_date to compute opening balance
    pre_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date < start_date
    ).all()
    # Opening net worth: sum of all wallet initial balances plus all income/expense before start
    # But we don't store initial wallet balances separately. Instead, we can compute net worth
    # as sum of wallet current balances, then subtract transactions after each date.
    # Easier: start from current and go backwards? Let's do forward simulation.
    
    # Get current balances (as of today)
    current_balances = {w.id: w.balance for w in wallets}
    # We'll simulate backwards: start from end_date, subtract transactions to get balance at each day.
    # Build a dict date -> net worth
    net_worth_by_date = {}
    # Sort transactions descending
    transactions_desc = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date.desc()).all()
    
    # Current net worth as of end_date
    net_worth = sum(current_balances.values())
    net_worth_by_date[end_date] = net_worth
    
    # Work backwards day by day
    current_date = end_date
    t_index = 0
    while current_date >= start_date and t_index < len(transactions_desc):
        # Process all transactions on current_date
        day_net_worth = net_worth
        while t_index < len(transactions_desc) and transactions_desc[t_index].date.date() == current_date:
            t = transactions_desc[t_index]
            # Reverse the transaction effect
            if t.type == 'income':
                day_net_worth -= t.amount
            elif t.type == 'expense':
                day_net_worth += t.amount
            # For transfers, net worth unchanged, but wallet balances change.
            # However, net worth is sum of all wallets, so transfer doesn't affect net worth.
            t_index += 1
        net_worth_by_date[current_date] = day_net_worth
        net_worth = day_net_worth
        current_date -= timedelta(days=1)
    
    # Fill missing dates with previous value
    all_dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    labels = [d.strftime('%Y-%m-%d') for d in all_dates]
    data = []
    last_nw = 0
    for d in all_dates:
        if d in net_worth_by_date:
            last_nw = net_worth_by_date[d]
        data.append(float(last_nw))
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Net Worth',
            'data': data,
            'borderColor': '#007bff',
            'fill': False
        }]
    }

def budget_vs_actual(user_id, budget_id=None):
    """Compare budgeted amounts vs actual spending for all budgets or a single budget."""
    budgets = Budget.query.filter_by(user_id=user_id, is_active=True)
    if budget_id:
        budgets = budgets.filter_by(id=budget_id)
    result = []
    today = datetime.now().date()
    for b in budgets:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == b.category_id,
            Transaction.type == 'expense',
            Transaction.date >= b.start_date,
            Transaction.date <= (b.end_date or today)
        ).scalar() or 0.0
        result.append({
            'budget_name': b.name,
            'budgeted': float(b.amount),
            'actual': float(spent),
            'difference': float(b.amount - spent),
            'progress': (spent / b.amount * 100) if b.amount else 0
        })
    return result

def top_categories(user_id, start_date, end_date, limit=5, transaction_type='expense'):
    """Return top spending/income categories."""
    results = db.session.query(
        Category.name,
        Category.color,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.user_id == user_id,
        Transaction.type == transaction_type,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).group_by(Category.id).order_by(func.sum(Transaction.amount).desc()).limit(limit).all()
    return [{'name': r[0], 'color': r[1], 'amount': float(r[2])} for r in results]