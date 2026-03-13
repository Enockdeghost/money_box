from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Subscription, Category, Wallet, Transaction
from app.forms import SubscriptionForm
from datetime import date, datetime, timedelta
from collections import defaultdict

bp = Blueprint('subscriptions', __name__)

@bp.route('/')
@login_required
def list_subscriptions():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.next_billing_date).all()
    return render_template('subscriptions/list.html', subscriptions=subscriptions, today=date.today())

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_subscription():
    form = SubscriptionForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    form.wallet_id.choices = [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        sub = Subscription(
            name=form.name.data,
            amount=form.amount.data,
            billing_cycle=form.billing_cycle.data,
            next_billing_date=form.next_billing_date.data,
            category_id=form.category_id.data,
            wallet_id=form.wallet_id.data,
            reminder_days=form.reminder_days.data,
            active=form.active.data,
            user_id=current_user.id
        )
        db.session.add(sub)
        db.session.commit()
        flash('Subscription added.', 'success')
        return redirect(url_for('subscriptions.list_subscriptions'))
    return render_template('subscriptions/create.html', form=form)

@bp.route('/<int:sub_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    if sub.user_id != current_user.id:
        abort(403)
    form = SubscriptionForm(obj=sub)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    form.wallet_id.choices = [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        sub.name = form.name.data
        sub.amount = form.amount.data
        sub.billing_cycle = form.billing_cycle.data
        sub.next_billing_date = form.next_billing_date.data
        sub.category_id = form.category_id.data
        sub.wallet_id = form.wallet_id.data
        sub.reminder_days = form.reminder_days.data
        sub.active = form.active.data
        db.session.commit()
        flash('Subscription updated.', 'success')
        return redirect(url_for('subscriptions.list_subscriptions'))
    return render_template('subscriptions/edit.html', form=form, sub=sub)

@bp.route('/<int:sub_id>/delete', methods=['POST'])
@login_required
def delete_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    if sub.user_id != current_user.id:
        abort(403)
    db.session.delete(sub)
    db.session.commit()
    flash('Subscription deleted.', 'success')
    return redirect(url_for('subscriptions.list_subscriptions'))

@bp.route('/detect', methods=['GET', 'POST'])
@login_required
def detect_subscriptions():
    if request.method == 'POST':
        selected = request.form.getlist('selected')
        # For simplicity, we'll just flash a message
        flash(f'Selected {len(selected)} subscriptions to add (feature coming soon).', 'info')
        return redirect(url_for('subscriptions.list_subscriptions'))
    # Analyze last 6 months of transactions to find recurring patterns
    six_months_ago = date.today() - timedelta(days=180)
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.date >= six_months_ago
    ).all()
    # Group by (description, amount) and count occurrences
    candidates = defaultdict(list)
    for t in transactions:
        key = (t.description, float(t.amount))
        candidates[key].append(t.date)
    suggested = []
    for (desc, amount), dates in candidates.items():
        if len(dates) >= 3:
            dates.sort()
            intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            if intervals and (max(intervals) - min(intervals)) <= 5:
                suggested.append({
                    'name': desc or 'Unknown',
                    'amount': amount,
                    'dates': dates
                })
    return render_template('subscriptions/detect.html', suggested=suggested)