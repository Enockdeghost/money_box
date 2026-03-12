import json
import os
from datetime import datetime
from flask import current_app
from app import db
from app.models import Backup, Wallet, Category, Transaction, Budget, SavingsGoal, Bill, Debt, Loan

def create_backup(user_id):
    """Create a full JSON backup of user data."""
    from app.utils.export import export_user_data
    data = export_user_data(user_id, 'all')
    filename = f"backup_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, default=str, indent=2)
    backup = Backup(
        user_id=user_id,
        filename=filename,
        size=os.path.getsize(filepath),
        type='manual',
        status='success'
    )
    db.session.add(backup)
    db.session.commit()
    return filename

def restore_from_backup(backup_id):
    """Restore user data from a backup file."""
    backup = Backup.query.get(backup_id)
    if not backup:
        return False
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], backup.filename)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except:
        return False
    user_id = backup.user_id
    # Clear existing data (careful! might want to archive instead)
    # We'll delete all user's data
    Transaction.query.filter_by(user_id=user_id).delete()
    Budget.query.filter_by(user_id=user_id).delete()
    SavingsGoal.query.filter_by(user_id=user_id).delete()
    Bill.query.filter_by(user_id=user_id).delete()
    Debt.query.filter_by(user_id=user_id).delete()
    Loan.query.filter_by(user_id=user_id).delete()
    Category.query.filter_by(user_id=user_id).delete()
    Wallet.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    # Import from JSON
    from app.utils.export import import_from_json
    import_from_json(data, user_id, duplicate_handling='overwrite')
    return True