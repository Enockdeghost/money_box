from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Budget, Category, Transaction
from app.forms import BudgetForm
from datetime import datetime
from sqlalchemy import func
from decimal import Decimal

bp = Blueprint('budgets', __name__)

@bp.route('/')
@login_required
def list_budgets():
    budgets = Budget.query.filter_by(user_id=current_user.id, is_active=True).all()
    today = datetime.now().date()
    budget_data = []
    for b in budgets:
        spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == b.category_id,
            Transaction.type == 'expense',
            Transaction.date >= b.start_date,
            Transaction.date <= (b.end_date or today)
        ).scalar()
        if spent is None:
            spent = Decimal('0.00')
        # spent is now a Decimal
        budget_data.append({
            'budget': b,
            'spent': spent,
            'remaining': b.amount - spent,
            'progress': (spent / b.amount * 100) if b.amount != 0 else 0,
            'days_left': (b.end_date - today).days if b.end_date else None
        })
    return render_template('budgets/list.html', budget_data=budget_data)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_budget():
    form = BudgetForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    if form.validate_on_submit():
        budget = Budget(
            name=form.name.data,
            amount=form.amount.data,
            period=form.period.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            category_id=form.category_id.data,
            user_id=current_user.id,
            rollover=form.rollover.data,
            alert_threshold=form.alert_threshold.data
        )
        db.session.add(budget)
        db.session.commit()
        flash('Budget created.', 'success')
        return redirect(url_for('budgets.list_budgets'))
    return render_template('budgets/create.html', form=form)

@bp.route('/<int:budget_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != current_user.id:
        abort(403)
    form = BudgetForm(obj=budget)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    if form.validate_on_submit():
        budget.name = form.name.data
        budget.amount = form.amount.data
        budget.period = form.period.data
        budget.start_date = form.start_date.data
        budget.end_date = form.end_date.data
        budget.category_id = form.category_id.data
        budget.rollover = form.rollover.data
        budget.alert_threshold = form.alert_threshold.data
        db.session.commit()
        flash('Budget updated.', 'success')
        return redirect(url_for('budgets.list_budgets'))
    return render_template('budgets/edit.html', form=form, budget=budget)

@bp.route('/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != current_user.id:
        abort(403)
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted.', 'success')
    return redirect(url_for('budgets.list_budgets'))

@bp.route('/<int:budget_id>/details')
@login_required
def budget_details(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != current_user.id:
        abort(403)
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.category_id == budget.category_id,
        Transaction.type == 'expense',
        Transaction.date >= budget.start_date,
        Transaction.date <= (budget.end_date or datetime.now().date())
    ).order_by(Transaction.date.desc()).all()
    # sum of Decimal amounts (all are Decimal)
    spent = sum((t.amount for t in transactions), Decimal('0.00'))
    remaining = budget.amount - spent
    progress = (spent / budget.amount * 100) if budget.amount != 0 else 0
    return render_template('budgets/details.html', budget=budget, transactions=transactions, spent=spent, remaining=remaining, progress=progress)