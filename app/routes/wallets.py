from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Wallet, Transaction, Category, SharedWallet, User
from app.forms import WalletForm, TransferForm
from datetime import datetime

bp = Blueprint('wallets', __name__)

@bp.route('/')
@login_required
def list_wallets():
    """Display all wallets owned by or shared with the user."""
    owned = Wallet.query.filter_by(user_id=current_user.id, is_hidden=False).all()
    # Wallets shared with me
    shared_ids = [sw.wallet_id for sw in SharedWallet.query.filter_by(shared_with_user_id=current_user.id).all()]
    shared = Wallet.query.filter(Wallet.id.in_(shared_ids), Wallet.is_hidden==False).all()
    return render_template('wallets/list.html', owned=owned, shared=shared)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_wallet():
    form = WalletForm()
    if form.validate_on_submit():
        wallet = Wallet(
            name=form.name.data,
            type=form.type.data,
            balance=form.balance.data,
            currency=form.currency.data,
            icon=form.icon.data,
            color=form.color.data,
            is_hidden=form.is_hidden.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        db.session.add(wallet)
        db.session.commit()
        flash('Wallet created successfully.', 'success')
        return redirect(url_for('wallets.list_wallets'))
    return render_template('wallets/create.html', form=form)

@bp.route('/<int:wallet_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_wallet(wallet_id):
    wallet = Wallet.query.get_or_404(wallet_id)
    # Check ownership or edit permission
    if wallet.user_id != current_user.id and not has_edit_permission(wallet, current_user):
        abort(403)
    form = WalletForm(obj=wallet)
    if form.validate_on_submit():
        wallet.name = form.name.data
        wallet.type = form.type.data
        wallet.currency = form.currency.data
        wallet.icon = form.icon.data
        wallet.color = form.color.data
        wallet.is_hidden = form.is_hidden.data
        wallet.notes = form.notes.data
        # Balance is not editable directly – only via transactions
        db.session.commit()
        flash('Wallet updated.', 'success')
        return redirect(url_for('wallets.list_wallets'))
    return render_template('wallets/edit.html', form=form, wallet=wallet)

@bp.route('/<int:wallet_id>/delete', methods=['POST'])
@login_required
def delete_wallet(wallet_id):
    wallet = Wallet.query.get_or_404(wallet_id)
    if wallet.user_id != current_user.id:
        abort(403)
    # Prevent deletion if it has transactions? (optional)
    if wallet.transactions.count() > 0:
        flash('Cannot delete wallet with existing transactions. Archive it instead.', 'danger')
        return redirect(url_for('wallets.list_wallets'))
    db.session.delete(wallet)
    db.session.commit()
    flash('Wallet deleted.', 'success')
    return redirect(url_for('wallets.list_wallets'))

@bp.route('/<int:wallet_id>/share', methods=['GET', 'POST'])
@login_required
def share_wallet(wallet_id):
    wallet = Wallet.query.get_or_404(wallet_id)
    if wallet.user_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        email = request.form.get('email')
        permission = request.form.get('permission', 'view')
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User not found.', 'danger')
        else:
            # Check if already shared
            existing = SharedWallet.query.filter_by(wallet_id=wallet.id, shared_with_user_id=user.id).first()
            if existing:
                existing.permission = permission
            else:
                share = SharedWallet(wallet_id=wallet.id, user_id=current_user.id, shared_with_user_id=user.id, permission=permission)
                db.session.add(share)
            db.session.commit()
            flash(f'Wallet shared with {email}.', 'success')
        return redirect(url_for('wallets.list_wallets'))
    return render_template('wallets/share.html', wallet=wallet)

@bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    form = TransferForm()
    # Populate wallet choices
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    form.from_wallet.choices = [(w.id, f"{w.name} (${w.balance})") for w in wallets]
    form.to_wallet.choices = [(w.id, w.name) for w in wallets]

    if form.validate_on_submit():
        from_wallet = Wallet.query.get(form.from_wallet.data)
        to_wallet = Wallet.query.get(form.to_wallet.data)
        amount = form.amount.data
        date = form.date.data
        description = form.description.data or f"Transfer from {from_wallet.name} to {to_wallet.name}"

        # Check sufficient balance
        if from_wallet.balance < amount:
            flash('Insufficient balance in source wallet.', 'danger')
            return render_template('wallets/transfer.html', form=form)

        # Create transfer category (or use a system category)
        transfer_cat = Category.query.filter_by(user_id=current_user.id, name='Transfer', is_system=True).first()
        if not transfer_cat:
            transfer_cat = Category(name='Transfer', type='expense', user_id=current_user.id, is_system=True)
            db.session.add(transfer_cat)
            db.session.commit()

        # Create expense transaction for from_wallet
        t1 = Transaction(
            amount=amount,
            type='expense',
            description=description,
            date=datetime.combine(date, datetime.min.time()),
            wallet_id=from_wallet.id,
            category_id=transfer_cat.id,
            user_id=current_user.id,
            transfer_target_wallet_id=to_wallet.id
        )
        # Create income transaction for to_wallet
        t2 = Transaction(
            amount=amount,
            type='income',
            description=description,
            date=datetime.combine(date, datetime.min.time()),
            wallet_id=to_wallet.id,
            category_id=transfer_cat.id,
            user_id=current_user.id,
            transfer_target_wallet_id=from_wallet.id
        )
        # Link them
        t1.transfer_transaction_id = t2.id
        t2.transfer_transaction_id = t1.id

        db.session.add_all([t1, t2])
        # Update balances
        from_wallet.balance -= amount
        to_wallet.balance += amount
        db.session.commit()

        flash('Transfer completed.', 'success')
        return redirect(url_for('transactions.list_transactions'))
    return render_template('wallets/transfer.html', form=form)

def has_edit_permission(wallet, user):
    """Check if user has edit permission on a shared wallet."""
    share = SharedWallet.query.filter_by(wallet_id=wallet.id, shared_with_user_id=user.id).first()
    return share and share.permission == 'edit'