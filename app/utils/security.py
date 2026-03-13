import secrets
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, url_for
from flask_mail import Message
from app import mail
import pyotp
import qrcode
import io
import base64
from werkzeug.security import generate_password_hash, check_password_hash

def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-verify')

def verify_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-verify', max_age=expiration)
        return email
    except:
        return False

def generate_reset_token(user):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps({'user_id': user.id}, salt='password-reset')

def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt='password-reset', max_age=expiration)
        return data['user_id']
    except:
        return None


def send_verification_email(user):
    token = user.email_verification_token
    if not token:
        token = generate_verification_token(user.email)
        user.email_verification_token = token
    link = url_for('auth.verify_email', token=token, _external=True)
    msg = Message('Verify Your Email', recipients=[user.email])
    msg.body = f'Click the link to verify your email: {link}'
    msg.html = f'<p>Click <a href="{link}">here</a> to verify your email.</p>'
    mail.send(msg)

def send_reset_email(user):
    token = generate_reset_token(user)
    link = url_for('auth.reset_token', token=token, _external=True)
    msg = Message('Password Reset Request', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{link}

If you did not make this request, simply ignore this email.
'''
    msg.html = f'''<p>To reset your password, click the link below:</p>
<p><a href="{link}">Reset Password</a></p>
<p>If you did not make this request, ignore this email.</p>'''
    mail.send(msg)

# Two-factor authentication helpers
def generate_2fa_secret():
    return pyotp.random_base32()

def get_2fa_uri(username, secret, issuer='MoneyBox'):
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)

def generate_qr_code(uri):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return img_base64

def verify_2fa_token(secret, token):
    totp = pyotp.TOTP(secret)
    return totp.verify(token)

# Passcode hashing (optional)
def hash_passcode(passcode):
    return generate_password_hash(passcode)

def check_passcode(passcode_hash, passcode):
    return check_password_hash(passcode_hash, passcode)