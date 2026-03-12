from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user, logout_user
from app.extensions import db
from app.models import UserPreference, UserDevice
from app.forms import ProfileForm, SecurityForm, NotificationForm
import pyotp

bp = Blueprint('settings', __name__)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if current_user.preferences:
        form.language.data = current_user.preferences.language
        form.theme.data = current_user.preferences.theme
        form.currency.data = current_user.preferences.currency
        form.date_format.data = current_user.preferences.date_format
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        if not current_user.preferences:
            current_user.preferences = UserPreference(user_id=current_user.id)
        current_user.preferences.language = form.language.data
        current_user.preferences.theme = form.theme.data
        current_user.preferences.currency = form.currency.data
        current_user.preferences.date_format = form.date_format.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('settings.profile'))
    return render_template('settings/profile.html', form=form)

@bp.route('/security', methods=['GET', 'POST'])
@login_required
def security():
    form = SecurityForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('settings/security.html', form=form)
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
        if form.two_factor.data and not current_user.two_factor_enabled:
            current_user.two_factor_secret = pyotp.random_base32()
            current_user.two_factor_enabled = True
        elif not form.two_factor.data and current_user.two_factor_enabled:
            current_user.two_factor_enabled = False
            current_user.two_factor_secret = None
        if form.passcode.data:
            current_user.set_passcode(form.passcode.data)
        current_user.biometric_enabled = form.biometric.data
        db.session.commit()
        flash('Security settings updated.', 'success')
        return redirect(url_for('settings.security'))
    return render_template('settings/security.html', form=form)

@bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    form = NotificationForm()
    if current_user.preferences:
        form.email_notifications.data = current_user.preferences.email_notifications
        form.push_notifications.data = current_user.preferences.push_notifications
        form.budget_alert_threshold.data = current_user.preferences.budget_alert_threshold
    if form.validate_on_submit():
        if not current_user.preferences:
            current_user.preferences = UserPreference(user_id=current_user.id)
        current_user.preferences.email_notifications = form.email_notifications.data
        current_user.preferences.push_notifications = form.push_notifications.data
        current_user.preferences.budget_alert_threshold = form.budget_alert_threshold.data
        db.session.commit()
        flash('Notification preferences updated.', 'success')
        return redirect(url_for('settings.notifications'))
    return render_template('settings/notifications.html', form=form)

@bp.route('/devices')
@login_required
def devices():
    devices = UserDevice.query.filter_by(user_id=current_user.id).order_by(UserDevice.last_login.desc()).all()
    return render_template('settings/devices.html', devices=devices)

@bp.route('/devices/revoke/<int:device_id>', methods=['POST'])
@login_required
def revoke_device(device_id):
    device = UserDevice.query.get_or_404(device_id)
    if device.user_id != current_user.id:
        abort(403)
    if device.is_current:
        flash('Cannot revoke current device.', 'danger')
    else:
        db.session.delete(device)
        db.session.commit()
        flash('Device revoked.', 'success')
    return redirect(url_for('settings.devices'))

@bp.route('/logout-all', methods=['POST'])
@login_required
def logout_all():
    UserDevice.query.filter_by(user_id=current_user.id, is_current=False).delete()
    db.session.commit()
    logout_user()
    flash('Logged out from all devices.', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    user = current_user
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Account deleted. Sorry to see you go.', 'info')
    return redirect(url_for('main.index'))