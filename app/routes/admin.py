from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, Wallet, Transaction, Category, Budget, SavingsGoal, Bill, Debt, Loan
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system stats."""
    total_users = User.query.count()
    total_wallets = Wallet.query.count()
    total_transactions = Transaction.query.count()
    total_categories = Category.query.count()
    total_budgets = Budget.query.count()
    total_savings = SavingsGoal.query.count()
    total_bills = Bill.query.count()
    total_debts = Debt.query.count()
    total_loans = Loan.query.count()

    # Users registered in the last 7 days
    week_ago = datetime.now() - timedelta(days=7)
    new_users = User.query.filter(User.created_at >= week_ago).count()

    # Recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_wallets=total_wallets,
                           total_transactions=total_transactions,
                           total_categories=total_categories,
                           total_budgets=total_budgets,
                           total_savings=total_savings,
                           total_bills=total_bills,
                           total_debts=total_debts,
                           total_loans=total_loans,
                           new_users=new_users,
                           recent_transactions=recent_transactions)

@bp.route('/users')
@login_required
@admin_required
def users_list():
    """List all users with search and pagination."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = User.query
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%') | User.email.ilike(f'%{search}%')
        )
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users, search=search)

@bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """Activate or deactivate a user."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.users_list'))
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'User {user.username} {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin.users_list'))

@bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_user_admin(user_id):
    """Grant or revoke admin privileges."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'danger')
        return redirect(url_for('admin.users_list'))
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'Admin privileges {"granted to" if user.is_admin else "revoked from"} {user.username}.', 'success')
    return redirect(url_for('admin.users_list'))

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Permanently delete a user and all their data."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users_list'))
    # All related data will be cascaded (if cascade is set in models)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} and all associated data deleted.', 'success')
    return redirect(url_for('admin.users_list'))

@bp.route('/stats')
@login_required
@admin_required
def stats():
    """Detailed statistics page."""
    # Total amounts
    total_wallet_balance = db.session.query(func.sum(Wallet.balance)).scalar() or 0
    total_transaction_amount = db.session.query(func.sum(Transaction.amount)).scalar() or 0
    total_budget_amount = db.session.query(func.sum(Budget.amount)).scalar() or 0
    total_savings_target = db.session.query(func.sum(SavingsGoal.target_amount)).scalar() or 0
    total_savings_current = db.session.query(func.sum(SavingsGoal.current_amount)).scalar() or 0

    # Counts by type (example: transactions by type)
    income_count = Transaction.query.filter_by(type='income').count()
    expense_count = Transaction.query.filter_by(type='expense').count()

    return render_template('admin/stats.html',
                           total_wallet_balance=total_wallet_balance,
                           total_transaction_amount=total_transaction_amount,
                           total_budget_amount=total_budget_amount,
                           total_savings_target=total_savings_target,
                           total_savings_current=total_savings_current,
                           income_count=income_count,
                           expense_count=expense_count)