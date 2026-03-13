from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import SharedBudget, Category, User, Transaction
from app.forms import SharedBudgetForm
from datetime import datetime

bp = Blueprint('shared_budgets', __name__)

@bp.route('/')
@login_required
def list_shared_budgets():
    owned = SharedBudget.query.filter_by(owner_id=current_user.id).all()
    shared_with_me = SharedBudget.query.filter_by(shared_with_user_id=current_user.id).all()
    return render_template('shared_budgets/list.html', owned=owned, shared=shared_with_me)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_shared_budget():
    form = SharedBudgetForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    if form.validate_on_submit():
        partner = User.query.filter_by(email=form.shared_with_email.data).first()
        if not partner:
            flash('User not found with that email.', 'danger')
            return render_template('shared_budgets/create.html', form=form)
        budget = SharedBudget(
            name=form.name.data,
            amount=form.amount.data,
            period=form.period.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            category_id=form.category_id.data,
            owner_id=current_user.id,
            shared_with_user_id=partner.id
        )
        db.session.add(budget)
        db.session.commit()
        flash('Shared budget created.', 'success')
        return redirect(url_for('shared_budgets.list_shared_budgets'))
    return render_template('shared_budgets/create.html', form=form)

@bp.route('/<int:budget_id>')
@login_required
def view_budget(budget_id):
    budget = SharedBudget.query.get_or_404(budget_id)
    if budget.owner_id != current_user.id and budget.shared_with_user_id != current_user.id:
        abort(403)
    today = datetime.now().date()
    # Sum transactions for both users in this category within the period
    spent_owner = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == budget.owner_id,
        Transaction.category_id == budget.category_id,
        Transaction.type == 'expense',
        Transaction.date >= budget.start_date,
        Transaction.date <= (budget.end_date or today)
    ).scalar() or 0
    spent_partner = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.user_id == budget.shared_with_user_id,
        Transaction.category_id == budget.category_id,
        Transaction.type == 'expense',
        Transaction.date >= budget.start_date,
        Transaction.date <= (budget.end_date or today)
    ).scalar() or 0
    total_spent = spent_owner + spent_partner
    remaining = budget.amount - total_spent
    progress = (total_spent / budget.amount * 100) if budget.amount else 0
    return render_template('shared_budgets/view.html', budget=budget, total_spent=total_spent, remaining=remaining, progress=progress)

@bp.route('/<int:budget_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_budget(budget_id):
    budget = SharedBudget.query.get_or_404(budget_id)
    if budget.owner_id != current_user.id:
        abort(403)
    form = SharedBudgetForm(obj=budget)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    if form.validate_on_submit():
        partner = User.query.filter_by(email=form.shared_with_email.data).first()
        if not partner:
            flash('User not found.', 'danger')
            return render_template('shared_budgets/edit.html', form=form, budget=budget)
        budget.name = form.name.data
        budget.amount = form.amount.data
        budget.period = form.period.data
        budget.start_date = form.start_date.data
        budget.end_date = form.end_date.data
        budget.category_id = form.category_id.data
        budget.shared_with_user_id = partner.id
        db.session.commit()
        flash('Shared budget updated.', 'success')
        return redirect(url_for('shared_budgets.list_shared_budgets'))
    form.shared_with_email.data = budget.shared_with.email
    return render_template('shared_budgets/edit.html', form=form, budget=budget)

@bp.route('/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = SharedBudget.query.get_or_404(budget_id)
    if budget.owner_id != current_user.id:
        abort(403)
    db.session.delete(budget)
    db.session.commit()
    flash('Shared budget deleted.', 'success')
    return redirect(url_for('shared_budgets.list_shared_budgets'))