from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, FloatField, SelectField, DateField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from app.models import User, Category, Wallet
from wtforms.validators import NumberRange, Optional
from datetime import datetime

# -------------------- Auth Forms --------------------
# Add these classes to your forms.py file

class DebtForm(FlaskForm):
    name = StringField('Debt Name', validators=[DataRequired(), Length(max=100)])
    total_amount = FloatField('Total Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    remaining_amount = FloatField('Remaining Amount', validators=[DataRequired(), NumberRange(min=0)])
    interest_rate = FloatField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    lender = StringField('Lender', validators=[Length(max=100)])
    notes = TextAreaField('Notes')

class LoanForm(FlaskForm):
    name = StringField('Loan Name', validators=[DataRequired(), Length(max=100)])
    total_amount = FloatField('Total Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    remaining_amount = FloatField('Remaining Amount', validators=[DataRequired(), NumberRange(min=0)])
    interest_rate = FloatField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    borrower = StringField('Borrower', validators=[Length(max=100)])
    notes = TextAreaField('Notes')

class RepaymentForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField('Date', format='%Y-%m-%d', default=datetime.today)
    notes = TextAreaField('Notes')
    wallet_id = SelectField('From Wallet', coerce=int, validators=[DataRequired()])
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class TwoFactorForm(FlaskForm):
    token = StringField('Authentication Code', validators=[DataRequired(), Length(min=6, max=6)])

class PasscodeForm(FlaskForm):
    passcode = PasswordField('Passcode', validators=[DataRequired(), Length(min=4, max=4)])

# -------------------- Wallet Forms --------------------
class WalletForm(FlaskForm):
    name = StringField('Wallet Name', validators=[DataRequired(), Length(max=64)])
    type = SelectField('Type', choices=[
        ('cash', 'Cash'),
        ('bank', 'Bank Account'),
        ('credit', 'Credit Card'),
        ('mobile', 'Mobile Money'),
        ('crypto', 'Cryptocurrency'),
        ('investment', 'Investment'),
        ('other', 'Other')
    ])
    balance = FloatField('Initial Balance', default=0.0)
    currency = SelectField('Currency', choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('JPY', 'JPY')], default='USD')
    icon = StringField('Icon (FontAwesome class)', default='wallet')
    color = StringField('Color (hex)', default='#007bff')
    is_hidden = BooleanField('Hide from dashboard')
    notes = TextAreaField('Notes', validators=[Length(max=500)])

class TransferForm(FlaskForm):
    from_wallet = SelectField('From Wallet', coerce=int, validators=[DataRequired()])
    to_wallet = SelectField('To Wallet', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField('Date', format='%Y-%m-%d', default=datetime.today)
    description = StringField('Description', validators=[Length(max=200)])

# -------------------- Category Forms --------------------
class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=64)])
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')])
    icon = StringField('Icon (FontAwesome class)', default='circle')
    color = StringField('Color (hex)', default='#6c757d')
    parent_id = SelectField('Parent Category', coerce=int, validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.parent_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Category.query.filter_by(type=self.type.data).all()]

# -------------------- Transaction Forms --------------------
class TransactionForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    wallet_id = SelectField('Wallet', coerce=int, validators=[DataRequired()])
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()])
    description = StringField('Description', validators=[Length(max=200)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    merchant = StringField('Merchant', validators=[Length(max=100)])
    location = StringField('Location', validators=[Length(max=100)])
    tags = StringField('Tags (comma separated)')
    receipt = FileField('Receipt (optional)', validators=[FileAllowed(['jpg', 'png', 'pdf'], 'Images or PDF only!')])
    is_recurring = BooleanField('Make this a recurring transaction')
    # For transfers (if type='transfer', we'll handle separately)
    transfer_to = SelectField('Transfer to Wallet', coerce=int, validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super(TransactionForm, self).__init__(*args, **kwargs)
        # Populate choices based on user and type
        self.category_id.choices = []
        self.wallet_id.choices = []
        # These will be set in the route after obtaining current_user

# -------------------- Recurring Transaction / Bill Forms --------------------
class RecurringTransactionForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    wallet_id = SelectField('Wallet', coerce=int, validators=[DataRequired()])
    frequency = SelectField('Frequency', choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ])
    interval = IntegerField('Repeat every', default=1, validators=[DataRequired(), NumberRange(min=1)])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date (optional)', format='%Y-%m-%d', validators=[Optional()])
    description = StringField('Description', validators=[Length(max=200)])
    notes = TextAreaField('Notes')
    is_bill = BooleanField('This is a bill')
    reminder_days = IntegerField('Remind me days before', default=0, validators=[NumberRange(min=0, max=30)])

class BillForm(FlaskForm):
    name = StringField('Bill Name', validators=[DataRequired(), Length(max=100)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    due_day = IntegerField('Due Day of Month', validators=[DataRequired(), NumberRange(min=1, max=31)])
    due_month = IntegerField('Due Month (for yearly bills)', validators=[Optional(), NumberRange(min=1, max=12)])
    frequency = SelectField('Frequency', choices=[('monthly', 'Monthly'), ('yearly', 'Yearly'), ('quarterly', 'Quarterly')])
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    wallet_id = SelectField('Default Wallet', coerce=int, validators=[Optional()])
    reminder_days = IntegerField('Reminder Days Before', default=3, validators=[NumberRange(min=0, max=30)])
    notes = TextAreaField('Notes')
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])

# -------------------- Budget Forms --------------------
class BudgetForm(FlaskForm):
    name = StringField('Budget Name', validators=[DataRequired(), Length(max=100)])
    amount = FloatField('Budget Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    period = SelectField('Period', choices=[('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date (optional)', format='%Y-%m-%d', validators=[Optional()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    rollover = BooleanField('Allow rollover of unused amount')
    alert_threshold = IntegerField('Alert at % of budget', default=80, validators=[NumberRange(min=1, max=100)])

# -------------------- Savings Goal Forms --------------------
class SavingsGoalForm(FlaskForm):
    name = StringField('Goal Name', validators=[DataRequired(), Length(max=100)])
    target_amount = FloatField('Target Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    current_amount = FloatField('Current Amount', default=0.0)
    deadline = DateField('Deadline (optional)', format='%Y-%m-%d', validators=[Optional()])
    notes = TextAreaField('Notes')
    icon = StringField('Icon', default='bullseye')
    color = StringField('Color', default='#28a745')

class ContributionForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField('Date', format='%Y-%m-%d', default=datetime.today)
    notes = TextAreaField('Notes')
    wallet_id = SelectField('From Wallet', coerce=int, validators=[DataRequired()])

# -------------------- Debt/Loan Forms --------------------
class DebtForm(FlaskForm):
    name = StringField('Debt Name', validators=[DataRequired(), Length(max=100)])
    total_amount = FloatField('Total Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    remaining_amount = FloatField('Remaining Amount', validators=[DataRequired(), NumberRange(min=0)])
    interest_rate = FloatField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    lender = StringField('Lender', validators=[Length(max=100)])
    notes = TextAreaField('Notes')

class RepaymentForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField('Date', format='%Y-%m-%d', default=datetime.today)
    notes = TextAreaField('Notes')
    wallet_id = SelectField('From Wallet', coerce=int, validators=[DataRequired()])

# -------------------- Report Forms --------------------
class ReportForm(FlaskForm):
    report_type = SelectField('Report Type', choices=[
        ('income_vs_expense', 'Income vs Expense'),
        ('category_breakdown', 'Category Breakdown'),
        ('spending_trend', 'Spending Trend'),
        ('budget_vs_actual', 'Budget vs Actual'),
        ('net_worth', 'Net Worth')
    ])
    period = SelectField('Period', choices=[
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('this_year', 'This Year'),
        ('custom', 'Custom')
    ])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    format = SelectField('Export Format', choices=[('html', 'HTML'), ('pdf', 'PDF'), ('csv', 'CSV'), ('excel', 'Excel')])

# -------------------- Settings Forms --------------------
class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    language = SelectField('Language', choices=[('en', 'English'), ('es', 'Spanish'), ('fr', 'French')])
    theme = SelectField('Theme', choices=[('light', 'Light'), ('dark', 'Dark')])
    currency = SelectField('Currency', choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP')])
    date_format = SelectField('Date Format', choices=[('YYYY-MM-DD', 'YYYY-MM-DD'), ('DD/MM/YYYY', 'DD/MM/YYYY'), ('MM/DD/YYYY', 'MM/DD/YYYY')])

class SecurityForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('new_password')])
    two_factor = BooleanField('Enable Two-Factor Authentication')
    passcode = PasswordField('App Passcode (4 digits)', validators=[Optional(), Length(min=4, max=4)])
    biometric = BooleanField('Enable Biometric Login (if device supports)')

class NotificationForm(FlaskForm):
    email_notifications = BooleanField('Email Notifications')
    push_notifications = BooleanField('Push Notifications')
    budget_alert_threshold = IntegerField('Budget Alert Threshold (%)', default=80, validators=[NumberRange(min=1, max=100)])
    bill_reminder_days = IntegerField('Bill Reminder Days Before', default=3, validators=[NumberRange(min=0, max=30)])

# -------------------- Import/Export Forms --------------------
class ImportForm(FlaskForm):
    file = FileField('File (CSV/Excel)', validators=[DataRequired(), FileAllowed(['csv', 'xlsx'], 'CSV or Excel only!')])
    import_type = SelectField('Import Type', choices=[('transactions', 'Transactions'), ('categories', 'Categories'), ('wallets', 'Wallets')])
    duplicate_handling = SelectField('Handle Duplicates', choices=[('skip', 'Skip'), ('overwrite', 'Overwrite'), ('create_new', 'Create New')])

class ExportForm(FlaskForm):
    data_type = SelectField('Data to Export', choices=[('all', 'All Data'), ('transactions', 'Transactions'), ('budgets', 'Budgets'), ('savings', 'Savings Goals')])
    format = SelectField('Format', choices=[('csv', 'CSV'), ('excel', 'Excel'), ('pdf', 'PDF')])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])