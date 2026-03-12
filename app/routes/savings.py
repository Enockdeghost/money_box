from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import SavingsGoal, Transaction, Wallet, Category
from app.forms import SavingsGoalForm, ContributionForm
from datetime import datetime

bp = Blueprint('savings', __name__)

@bp.route('/')
@login_required
def list_goals():
    goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.deadline).all()
    return render_template('savings/list.html', goals=goals)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_goal():
    form = SavingsGoalForm()
    if form.validate_on_submit():
        goal = SavingsGoal(
            name=form.name.data,
            target_amount=form.target_amount.data,
            current_amount=form.current_amount.data,
            deadline=form.deadline.data,
            notes=form.notes.data,
            icon=form.icon.data,
            color=form.color.data,
            user_id=current_user.id
        )
        db.session.add(goal)
        db.session.commit()
        flash('Savings goal created.', 'success')
        return redirect(url_for('savings.list_goals'))
    return render_template('savings/create.html', form=form)

@bp.route('/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        abort(403)
    form = SavingsGoalForm(obj=goal)
    if form.validate_on_submit():
        goal.name = form.name.data
        goal.target_amount = form.target_amount.data
        goal.deadline = form.deadline.data
        goal.notes = form.notes.data
        goal.icon = form.icon.data
        goal.color = form.color.data
        db.session.commit()
        flash('Goal updated.', 'success')
        return redirect(url_for('savings.list_goals'))
    return render_template('savings/edit.html', form=form, goal=goal)

@bp.route('/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        abort(403)
    db.session.delete(goal)
    db.session.commit()
    flash('Goal deleted.', 'success')
    return redirect(url_for('savings.list_goals'))

@bp.route('/<int:goal_id>/contribute', methods=['GET', 'POST'])
@login_required
def contribute(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        abort(403)
    form = ContributionForm()
    form.wallet_id.choices = [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        amount = form.amount.data
        wallet = Wallet.query.get(form.wallet_id.data)
        if wallet.balance < amount:
            flash('Insufficient balance in selected wallet.', 'danger')
            return render_template('savings/contribute.html', form=form, goal=goal)
        savings_cat = Category.query.filter_by(user_id=current_user.id, name='Savings', is_system=True).first()
        if not savings_cat:
            savings_cat = Category(name='Savings', type='expense', user_id=current_user.id, is_system=True)
            db.session.add(savings_cat)
            db.session.commit()
        transaction = Transaction(
            amount=amount,
            type='expense',
            description=f'Contribution to savings goal: {goal.name}',
            date=datetime.combine(form.date.data, datetime.now().time()),
            wallet_id=wallet.id,
            category_id=savings_cat.id,
            user_id=current_user.id,
            goal_id=goal.id
        )
        wallet.balance -= amount
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
            goal.completed_date = form.date.data
        db.session.add(transaction)
        db.session.commit()
        flash('Contribution added.', 'success')
        return redirect(url_for('savings.list_goals'))
    return render_template('savings/contribute.html', form=form, goal=goal)

@bp.route('/<int:goal_id>/complete', methods=['POST'])
@login_required
def complete_goal(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        abort(403)
    goal.is_completed = True
    goal.completed_date = datetime.now().date()
    db.session.commit()
    flash('Goal marked as completed!', 'success')
    return redirect(url_for('savings.list_goals'))