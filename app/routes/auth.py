from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, mail
from app.models import User, UserDevice, LoginHistory, Category, Wallet
from app.forms import LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm, TwoFactorForm, PasscodeForm
from app.utils.security import generate_verification_token, verify_verification_token, send_verification_email, send_reset_email, generate_reset_token
from datetime import datetime
import pyotp

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if user.two_factor_enabled:
                session['user_id'] = user.id
                return redirect(url_for('auth.two_factor'))
            login_user(user, remember=form.remember.data)
            # Record login device
            device = UserDevice(
                user_id=user.id,
                device_name=request.user_agent.string[:100],
                device_type='web',
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                is_current=True
            )
            db.session.add(device)
            db.session.add(LoginHistory(user_id=user.id, ip_address=request.remote_addr, user_agent=request.user_agent.string))
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)

@bp.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    form = TwoFactorForm()
    if form.validate_on_submit():
        totp = pyotp.TOTP(user.two_factor_secret)
        if totp.verify(form.token.data):
            login_user(user)
            session.pop('user_id', None)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid code.', 'danger')
    return render_template('auth/two_factor.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)

        # Create default categories
        default_categories = [
            Category(name='Salary', type='income', icon='money-bill', color='#28a745', user=user, is_system=True),
            Category(name='Food', type='expense', icon='utensils', color='#dc3545', user=user, is_system=True),
            Category(name='Transport', type='expense', icon='bus', color='#ffc107', user=user, is_system=True),
            Category(name='Entertainment', type='expense', icon='film', color='#17a2b8', user=user, is_system=True),
            Category(name='Shopping', type='expense', icon='shopping-cart', color='#6f42c1', user=user, is_system=True),
            Category(name='Bills', type='expense', icon='file-invoice', color='#fd7e14', user=user, is_system=True),
            Category(name='Health', type='expense', icon='heartbeat', color='#e83e8c', user=user, is_system=True),
            Category(name='Education', type='expense', icon='book', color='#20c997', user=user, is_system=True),
        ]
        db.session.add_all(default_categories)

        # Create default wallet
        default_wallet = Wallet(
            name='Cash',
            type='cash',
            balance=0,
            currency='USD',
            user=user
        )
        db.session.add(default_wallet)

        # Handle email verification based on config
        if current_app.config.get('MAIL_USERNAME'):
            user.email_verification_token = generate_verification_token(user.email)
            send_verification_email(user)
            flash('Your account has been created! Please check your email to verify your account.', 'success')
        else:
            # Development mode: auto-verify
            user.email_verified = True
            flash('Your account has been created! (Email verification disabled in development)', 'success')

        db.session.commit()
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@bp.route('/verify-email/<token>')
def verify_email(token):
    email = verify_verification_token(token)
    if email:
        user = User.query.filter_by(email=email).first()
        if user:
            user.email_verified = True
            user.email_verification_token = None
            db.session.commit()
            flash('Your email has been verified. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
    flash('The verification link is invalid or has expired.', 'danger')
    return redirect(url_for('main.landing'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.landing'))

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if current_app.config.get('MAIL_USERNAME'):
                send_reset_email(user)
                flash('A password reset link has been sent to your email.', 'info')
            else:
                # Development mode: show link directly
                token = generate_reset_token(user)
                reset_link = url_for('auth.reset_token', token=token, _external=True)
                flash(f'Password reset link (development mode): {reset_link}', 'info')
        else:
            # Always show same message for security
            flash('If an account exists with that email, a reset link will be sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_request.html', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    from app.utils.security import verify_reset_token
    user_id = verify_reset_token(token)
    if not user_id:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('auth.reset_request'))
    user = User.query.get(user_id)
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
