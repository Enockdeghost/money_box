from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Bill, Category, Wallet, Transaction
from app.forms import BillForm
from datetime import datetime, timedelta
from calendar import monthrange

bp = Blueprint('bills', __name__)

@bp.route('/')
@login_required
def list_bills():
    bills = Bill.query.filter_by(user_id=current_user.id, is_active=True).all()
    today = datetime.now().date()
    for bill in bills:
        if bill.frequency == 'monthly':
            year = today.year
            month = today.month
            day = bill.due_day
            due_this_month = datetime(year, month, min(day, monthrange(year, month)[1])).date()
            if due_this_month >= today:
                bill.next_due = due_this_month
            else:
                next_month = month + 1
                next_year = year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                bill.next_due = datetime(next_year, next_month, min(day, monthrange(next_year, next_month)[1])).date()
        elif bill.frequency == 'yearly':
            # Simplified: just use next year if due date passed
            due_this_year = datetime(today.year, bill.due_month or 1, bill.due_day).date()
            if due_this_year >= today:
                bill.next_due = due_this_year
            else:
                bill.next_due = datetime(today.year + 1, bill.due_month or 1, bill.due_day).date()
    return render_template('bills/list.html', bills=bills, today=today)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_bill():
    form = BillForm()
    form.category_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    form.wallet_id.choices = [(0, 'None')] + [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        bill = Bill(
            name=form.name.data,
            amount=form.amount.data,
            due_day=form.due_day.data,
            due_month=form.due_month.data,
            frequency=form.frequency.data,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            wallet_id=form.wallet_id.data if form.wallet_id.data != 0 else None,
            reminder_days=form.reminder_days.data,
            notes=form.notes.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            user_id=current_user.id
        )
        db.session.add(bill)
        db.session.commit()
        flash('Bill created.', 'success')
        return redirect(url_for('bills.list_bills'))
    return render_template('bills/create.html', form=form)

@bp.route('/<int:bill_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.user_id != current_user.id:
        abort(403)
    form = BillForm(obj=bill)
    form.category_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id, type='expense').all()]
    form.wallet_id.choices = [(0, 'None')] + [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        bill.name = form.name.data
        bill.amount = form.amount.data
        bill.due_day = form.due_day.data
        bill.due_month = form.due_month.data
        bill.frequency = form.frequency.data
        bill.category_id = form.category_id.data if form.category_id.data != 0 else None
        bill.wallet_id = form.wallet_id.data if form.wallet_id.data != 0 else None
        bill.reminder_days = form.reminder_days.data
        bill.notes = form.notes.data
        bill.start_date = form.start_date.data
        bill.end_date = form.end_date.data
        db.session.commit()
        flash('Bill updated.', 'success')
        return redirect(url_for('bills.list_bills'))
    return render_template('bills/edit.html', form=form, bill=bill)

@bp.route('/<int:bill_id>/delete', methods=['POST'])
@login_required
def delete_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.user_id != current_user.id:
        abort(403)
    db.session.delete(bill)
    db.session.commit()
    flash('Bill deleted.', 'success')
    return redirect(url_for('bills.list_bills'))

@bp.route('/<int:bill_id>/pay', methods=['POST'])
@login_required
def pay_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.user_id != current_user.id:
        abort(403)
    if not bill.wallet_id:
        flash('No default wallet set for this bill. Please select a wallet to pay from.', 'danger')
        return redirect(url_for('bills.list_bills'))
    wallet = Wallet.query.get(bill.wallet_id)
    if wallet.balance < bill.amount:
        flash('Insufficient balance in default wallet.', 'danger')
        return redirect(url_for('bills.list_bills'))
    cat_id = bill.category_id or Category.query.filter_by(user_id=current_user.id, name='Bills', is_system=True).first().id
    transaction = Transaction(
        amount=bill.amount,
        type='expense',
        description=f'Payment for {bill.name}',
        date=datetime.now(),
        wallet_id=bill.wallet_id,
        category_id=cat_id,
        user_id=current_user.id
    )
    wallet.balance -= bill.amount
    db.session.add(transaction)
    bill.last_paid = datetime.now().date()
    db.session.commit()
    flash('Bill payment recorded.', 'success')
    return redirect(url_for('bills.list_bills'))

@bp.route('/calendar')
@login_required
def calendar():
    bills = Bill.query.filter_by(user_id=current_user.id, is_active=True).all()
    events = []
    for bill in bills:
        if bill.next_due:
            events.append({
                'title': bill.name,
                'start': bill.next_due.isoformat(),
                'url': url_for('bills.list_bills')
            })
    return render_template('bills/calendar.html', events=events)