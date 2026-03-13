from flask import render_template, current_app, url_for
from flask_mail import Message
from app import mail

def send_email(recipient, subject, template, **kwargs):
    """Send an email using a template."""
    msg = Message(subject, recipients=[recipient])
    msg.body = render_template(f'emails/{template}.txt', **kwargs)
    msg.html = render_template(f'emails/{template}.html', **kwargs)
    mail.send(msg)

def send_verification_email(user):
    """Send email verification link."""
    token = user.email_verification_token
    link = url_for('auth.verify_email', token=token, _external=True)
    send_email(user.email, 'Verify Your Email', 'verify_email', user=user, link=link)

def send_password_reset_email(user, token):
    """Send password reset link."""
    link = url_for('auth.reset_password', token=token, _external=True)
    send_email(user.email, 'Password Reset Request', 'reset_password', user=user, link=link)

def send_budget_alert(user, budget, spent):
    """Send budget alert email."""
    send_email(user.email, f'Budget Alert: {budget.name}', 'budget_alert',
               user=user, budget=budget, spent=spent)

def send_bill_reminder(user, bill):
    """Send bill reminder email."""
    send_email(user.email, f'Reminder: {bill.name} is due soon', 'bill_reminder',
               user=user, bill=bill)

def send_subscription_reminder(user, subscription):
    msg = Message(
        f'Upcoming Subscription: {subscription.name}',
        recipients=[user.email]
    )
    msg.body = f'''Your subscription {subscription.name} of ${subscription.amount} is due on {subscription.next_billing_date}.

You can manage your subscriptions here: {url_for('subscriptions.list_subscriptions', _external=True)}
'''
    mail.send(msg)