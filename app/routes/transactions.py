from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Transaction, Wallet, Category, RecurringTransaction
from app.forms import TransactionForm, RecurringTransactionForm
from app.utils.helpers import save_receipt, delete_receipt
from datetime import datetime, timedelta
from sqlalchemy import or_
from decimal import Decimal
from app.models import SavingsGoal

bp = Blueprint('transactions', __name__)

@bp.route('/')
@login_required
def list_transactions():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    query = Transaction.query.filter_by(user_id=current_user.id)

    search = request.args.get('search', '')
    if search:
        query = query.filter(or_(
            Transaction.description.ilike(f'%{search}%'),
            Transaction.notes.ilike(f'%{search}%'),
            Transaction.merchant.ilike(f'%{search}%')
        ))

    type_filter = request.args.get('type', '')
    if type_filter in ['income', 'expense']:
        query = query.filter_by(type=type_filter)

    category_id = request.args.get('category', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)

    wallet_id = request.args.get('wallet', type=int)
    if wallet_id:
        query = query.filter_by(wallet_id=wallet_id)

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

    sort = request.args.get('sort', 'date_desc')
    if sort == 'date_desc':
        query = query.order_by(Transaction.date.desc())
    elif sort == 'date_asc':
        query = query.order_by(Transaction.date.asc())
    elif sort == 'amount_desc':
        query = query.order_by(Transaction.amount.desc())
    elif sort == 'amount_asc':
        query = query.order_by(Transaction.amount.asc())

    transactions = query.paginate(page=page, per_page=per_page)
    categories = Category.query.filter_by(user_id=current_user.id).all()
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    return render_template('transactions/list.html',
                           transactions=transactions,
                           categories=categories,
                           wallets=wallets,
                           filters=request.args)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()

    # Always fetch wallets (they are used in both category and wallet dropdowns)
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    # Set wallet choices unconditionally (never None)
    form.wallet_id.choices = [(w.id, f"{w.name} (${w.balance})") for w in wallets] or []
    form.transfer_to.choices = [(0, 'None')] + [(w.id, w.name) for w in wallets] or []

    # Determine which categories to show based on form type (if available)
    if form.type.data:
        cat_type = form.type.data
    else:
        # Default to expense on GET
        cat_type = 'expense'
    categories = Category.query.filter_by(user_id=current_user.id, type=cat_type).all()
    form.category_id.choices = [(c.id, c.name) for c in categories] or []

    if form.validate_on_submit():
        # Convert amount to Decimal
        from decimal import Decimal
        amount = Decimal(str(form.amount.data))

        # Handle receipt upload
        filename = None
        if form.receipt.data:
            filename = save_receipt(form.receipt.data)

        transaction = Transaction(
            amount=amount,
            type=form.type.data,
            description=form.description.data,
            notes=form.notes.data,
            date=datetime.combine(form.date.data, datetime.now().time()),
            merchant=form.merchant.data,
            location=form.location.data,
            receipt_filename=filename,
            tags=form.tags.data,
            wallet_id=form.wallet_id.data,
            category_id=form.category_id.data,
            user_id=current_user.id
        )

        wallet = Wallet.query.get(form.wallet_id.data)
        if transaction.type == 'income':
            wallet.balance += amount
        else:
            wallet.balance -= amount

        db.session.add(transaction)

        # Handle transfer
        if form.type.data == 'expense' and form.transfer_to.data and form.transfer_to.data != 0:
            to_wallet = Wallet.query.get(form.transfer_to.data)
            t2 = Transaction(
                amount=amount,
                type='income',
                description=f"Transfer from {wallet.name}",
                date=transaction.date,
                wallet_id=to_wallet.id,
                category_id=form.category_id.data,
                user_id=current_user.id,
                transfer_target_wallet_id=wallet.id
            )
            transaction.transfer_target_wallet_id = to_wallet.id
            transaction.transfer_transaction_id = t2.id
            t2.transfer_transaction_id = transaction.id
            db.session.add(t2)
            to_wallet.balance += amount

        if form.is_recurring.data:
            flash('Transaction saved. Now set up recurring schedule.', 'info')
            db.session.commit()
            return redirect(url_for('transactions.add_recurring', transaction_id=transaction.id))

        db.session.commit()
        flash('Transaction added.', 'success')
        return redirect(url_for('transactions.list_transactions'))

    return render_template('transactions/add.html', form=form)

@bp.route('/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        abort(403)

    form = TransactionForm(obj=transaction)
    # ... populate choices ...

    if form.validate_on_submit():
        # Convert new amount to Decimal
        new_amount = Decimal(str(form.amount.data))

        # Revert old wallet balance
        old_wallet = Wallet.query.get(transaction.wallet_id)
        if transaction.type == 'income':
            old_wallet.balance -= transaction.amount  # transaction.amount is already Decimal
        else:
            old_wallet.balance += transaction.amount

        # Handle new receipt
        if form.receipt.data:
            if transaction.receipt_filename:
                delete_receipt(transaction.receipt_filename)
            transaction.receipt_filename = save_receipt(form.receipt.data)

        # Update transaction fields
        transaction.amount = new_amount
        transaction.type = form.type.data
        transaction.description = form.description.data
        transaction.notes = form.notes.data
        transaction.date = datetime.combine(form.date.data, transaction.date.time())
        transaction.merchant = form.merchant.data
        transaction.location = form.location.data
        transaction.tags = form.tags.data
        transaction.wallet_id = form.wallet_id.data
        transaction.category_id = form.category_id.data

        # Update new wallet balance
        new_wallet = Wallet.query.get(form.wallet_id.data)
        if transaction.type == 'income':
            new_wallet.balance += new_amount
        else:
            new_wallet.balance -= new_amount

        db.session.commit()
        flash('Transaction updated.', 'success')
        return redirect(url_for('transactions.list_transactions'))

    if transaction.transfer_target_wallet_id:
        form.transfer_to.data = transaction.transfer_target_wallet_id
    return render_template('transactions/edit.html', form=form, transaction=transaction)

@bp.route('/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        abort(403)

    wallet = Wallet.query.get(transaction.wallet_id)
    if transaction.type == 'income':
        wallet.balance -= transaction.amount  # Decimal
    else:
        wallet.balance += transaction.amount

    if transaction.transfer_transaction_id:
        counterpart = Transaction.query.get(transaction.transfer_transaction_id)
        if counterpart:
            c_wallet = Wallet.query.get(counterpart.wallet_id)
            if counterpart.type == 'income':
                c_wallet.balance -= counterpart.amount
            else:
                c_wallet.balance += counterpart.amount
            db.session.delete(counterpart)

    if transaction.receipt_filename:
        delete_receipt(transaction.receipt_filename)

    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted.', 'success')
    return redirect(url_for('transactions.list_transactions'))

@bp.route('/recurring')
@login_required
def list_recurring():
    recurring = RecurringTransaction.query.filter_by(user_id=current_user.id, is_active=True).all()
    return render_template('transactions/recurring_list.html', recurring=recurring)

@bp.route('/recurring/add', methods=['GET', 'POST'])
@login_required
def add_recurring():
    form = RecurringTransactionForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(user_id=current_user.id).all()]
    form.wallet_id.choices = [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]

    transaction_id = request.args.get('transaction_id', type=int)
    if transaction_id and request.method == 'GET':
        t = Transaction.query.get(transaction_id)
        if t and t.user_id == current_user.id:
            form.amount.data = t.amount
            form.type.data = t.type
            form.category_id.data = t.category_id
            form.wallet_id.data = t.wallet_id
            form.description.data = t.description
            form.notes.data = t.notes

    if form.validate_on_submit():
        next_date = form.start_date.data
        recurring = RecurringTransaction(
            amount=form.amount.data,
            type=form.type.data,
            description=form.description.data,
            notes=form.notes.data,
            frequency=form.frequency.data,
            interval=form.interval.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            wallet_id=form.wallet_id.data,
            category_id=form.category_id.data,
            user_id=current_user.id,
            is_bill=form.is_bill.data,
            bill_reminder_days=form.reminder_days.data if form.is_bill.data else 0,
            next_date=next_date
        )
        db.session.add(recurring)
        db.session.commit()
        flash('Recurring transaction created.', 'success')
        return redirect(url_for('transactions.list_recurring'))
    return render_template('transactions/add_recurring.html', form=form)

def apply_round_up(transaction):
    if transaction.type != 'expense':
        return
    # Check if this transaction belongs to a goal (via category or maybe a goal_id field)
    goal = None
    if transaction.goal_id:
        goal = SavingsGoal.query.get(transaction.goal_id)
    elif transaction.category and transaction.category.name == 'Savings':
        # Or maybe we need a more robust way: we could store goal_id in transaction
        pass
    if goal and goal.round_up_enabled and goal.round_up_wallet:
        # Calculate round-up to nearest dollar (or configurable increment)
        increment = Decimal('1.00')  # could be a field on goal later
        amount = transaction.amount
        remainder = amount % increment
        round_up = increment - remainder if remainder != 0 else 0
        if round_up > 0:
            # Create a separate transaction as transfer from the original wallet to round-up wallet
            round_up_transaction = Transaction(
                amount=round_up,
                type='expense',
                description=f'Round-up for {transaction.description or "transaction"}',
                date=transaction.date,
                wallet_id=transaction.wallet_id,
                category_id=transaction.category_id,  # or a special "Round-up" category
                user_id=transaction.user_id,
                goal_id=goal.id,
                is_recurring=False
            )
            # Also create a corresponding income in the round-up wallet
            income_transaction = Transaction(
                amount=round_up,
                type='income',
                description=f'Round-up from {transaction.description or "transaction"}',
                date=transaction.date,
                wallet_id=goal.round_up_wallet_id,
                category_id=transaction.category_id,  # or a special category
                user_id=transaction.user_id,
                goal_id=goal.id,
                is_recurring=False
            )
            db.session.add(round_up_transaction)
            db.session.add(income_transaction)
            # Update wallet balances
            from_wallet = Wallet.query.get(transaction.wallet_id)
            to_wallet = Wallet.query.get(goal.round_up_wallet_id)
            from_wallet.balance -= round_up
            to_wallet.balance += round_up
            db.session.commit()