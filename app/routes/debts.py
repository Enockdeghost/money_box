from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Debt, Loan, Repayment, Transaction, Wallet, Category
from app.forms import DebtForm, LoanForm, RepaymentForm
from datetime import datetime

bp = Blueprint('debts', __name__)

@bp.route('/')
@login_required
def list_debts():
    debts = Debt.query.filter_by(user_id=current_user.id, is_paid=False).all()
    loans = Loan.query.filter_by(user_id=current_user.id, is_repaid=False).all()
    return render_template('debts/list.html', debts=debts, loans=loans)

@bp.route('/create-debt', methods=['GET', 'POST'])
@login_required
def create_debt():
    form = DebtForm()
    if form.validate_on_submit():
        debt = Debt(
            name=form.name.data,
            total_amount=form.total_amount.data,
            remaining_amount=form.remaining_amount.data,
            interest_rate=form.interest_rate.data,
            start_date=form.start_date.data,
            due_date=form.due_date.data,
            lender=form.lender.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        db.session.add(debt)
        db.session.commit()
        flash('Debt record created.', 'success')
        return redirect(url_for('debts.list_debts'))
    return render_template('debts/create_debt.html', form=form)

@bp.route('/create-loan', methods=['GET', 'POST'])
@login_required
def create_loan():
    form = LoanForm()
    if form.validate_on_submit():
        loan = Loan(
            name=form.name.data,
            total_amount=form.total_amount.data,
            remaining_amount=form.remaining_amount.data,
            interest_rate=form.interest_rate.data,
            start_date=form.start_date.data,
            due_date=form.due_date.data,
            borrower=form.borrower.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        db.session.add(loan)
        db.session.commit()
        flash('Loan record created.', 'success')
        return redirect(url_for('debts.list_debts'))
    return render_template('debts/create_loan.html', form=form)

@bp.route('/debt/<int:debt_id>/repay', methods=['GET', 'POST'])
@login_required
def repay_debt(debt_id):
    debt = Debt.query.get_or_404(debt_id)
    if debt.user_id != current_user.id:
        abort(403)
    form = RepaymentForm()
    form.wallet_id.choices = [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        amount = form.amount.data
        if amount > debt.remaining_amount:
            flash('Amount exceeds remaining debt.', 'danger')
            return render_template('debts/repay.html', form=form, debt=debt)
        wallet = Wallet.query.get(form.wallet_id.data)
        if wallet.balance < amount:
            flash('Insufficient balance.', 'danger')
            return render_template('debts/repay.html', form=form, debt=debt)
        # Create expense transaction
        debt_cat = Category.query.filter_by(user_id=current_user.id, name='Debt Payment', is_system=True).first()
        if not debt_cat:
            debt_cat = Category(name='Debt Payment', type='expense', user_id=current_user.id, is_system=True)
            db.session.add(debt_cat)
            db.session.commit()
        transaction = Transaction(
            amount=amount,
            type='expense',
            description=f'Repayment for {debt.name}',
            date=datetime.combine(form.date.data, datetime.now().time()),
            wallet_id=wallet.id,
            category_id=debt_cat.id,
            user_id=current_user.id
        )
        wallet.balance -= amount
        debt.remaining_amount -= amount
        repayment = Repayment(
            amount=amount,
            date=form.date.data,
            notes=form.notes.data,
            debt_id=debt.id,
            transaction_id=transaction.id
        )
        db.session.add_all([transaction, repayment])
        if debt.remaining_amount <= 0:
            debt.is_paid = True
        db.session.commit()
        flash('Repayment recorded.', 'success')
        return redirect(url_for('debts.list_debts'))
    return render_template('debts/repay.html', form=form, debt=debt)

@bp.route('/loan/<int:loan_id>/receive', methods=['GET', 'POST'])
@login_required
def receive_repayment(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user.id:
        abort(403)
    form = RepaymentForm()
    form.wallet_id.choices = [(w.id, w.name) for w in Wallet.query.filter_by(user_id=current_user.id).all()]
    if form.validate_on_submit():
        amount = form.amount.data
        if amount > loan.remaining_amount:
            flash('Amount exceeds remaining loan.', 'danger')
            return render_template('debts/receive.html', form=form, loan=loan)
        wallet = Wallet.query.get(form.wallet_id.data)
        # Create income transaction
        loan_cat = Category.query.filter_by(user_id=current_user.id, name='Loan Repayment', is_system=True).first()
        if not loan_cat:
            loan_cat = Category(name='Loan Repayment', type='income', user_id=current_user.id, is_system=True)
            db.session.add(loan_cat)
            db.session.commit()
        transaction = Transaction(
            amount=amount,
            type='income',
            description=f'Repayment received for {loan.name}',
            date=datetime.combine(form.date.data, datetime.now().time()),
            wallet_id=wallet.id,
            category_id=loan_cat.id,
            user_id=current_user.id
        )
        wallet.balance += amount
        loan.remaining_amount -= amount
        repayment = Repayment(
            amount=amount,
            date=form.date.data,
            notes=form.notes.data,
            loan_id=loan.id,
            transaction_id=transaction.id
        )
        db.session.add_all([transaction, repayment])
        if loan.remaining_amount <= 0:
            loan.is_repaid = True
        db.session.commit()
        flash('Repayment received.', 'success')
        return redirect(url_for('debts.list_debts'))
    return render_template('debts/receive.html', form=form, loan=loan)