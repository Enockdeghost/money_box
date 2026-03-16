import json
import csv
import io
from datetime import datetime, timedelta
from app.extensions import db
from app.models import (
    User, Wallet, Category, Transaction, Budget,
    SavingsGoal, Bill, Debt, Loan
)
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def export_user_data(user_id, data_type='all', start_date=None, end_date=None):
    """Export user data as dictionary."""
    data = {'user_id': user_id, 'export_date': datetime.utcnow().isoformat()}
    
    if data_type in ['all', 'wallets']:
        wallets = Wallet.query.filter_by(user_id=user_id).all()
        data['wallets'] = [{
            'id': w.id, 'name': w.name, 'type': w.type,
            'balance': float(w.balance), 'currency': w.currency,
            'icon': w.icon, 'color': w.color
        } for w in wallets]
    
    if data_type in ['all', 'categories']:
        categories = Category.query.filter_by(user_id=user_id).all()
        data['categories'] = [{
            'id': c.id, 'name': c.name, 'type': c.type,
            'icon': c.icon, 'color': c.color, 'parent_id': c.parent_id
        } for c in categories]
    
    if data_type in ['all', 'transactions']:
        query = Transaction.query.filter_by(user_id=user_id)
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date + timedelta(days=1))
        transactions = query.all()
        data['transactions'] = [{
            'id': t.id, 'amount': float(t.amount), 'type': t.type,
            'description': t.description, 'notes': t.notes,
            'date': t.date.isoformat(), 'merchant': t.merchant,
            'location': t.location, 'receipt_filename': t.receipt_filename,
            'wallet_id': t.wallet_id, 'category_id': t.category_id,
            'tags': t.tags
        } for t in transactions]
    
    if data_type in ['all', 'budgets']:
        budgets = Budget.query.filter_by(user_id=user_id).all()
        data['budgets'] = [{
            'id': b.id, 'name': b.name, 'amount': float(b.amount),
            'period': b.period, 'start_date': b.start_date.isoformat(),
            'end_date': b.end_date.isoformat() if b.end_date else None,
            'category_id': b.category_id, 'rollover': b.rollover,
            'alert_threshold': b.alert_threshold
        } for b in budgets]
    
    if data_type in ['all', 'savings']:
        savings = SavingsGoal.query.filter_by(user_id=user_id).all()
        data['savings'] = [{
            'id': s.id, 'name': s.name, 'target_amount': float(s.target_amount),
            'current_amount': float(s.current_amount),
            'deadline': s.deadline.isoformat() if s.deadline else None,
            'notes': s.notes, 'icon': s.icon, 'color': s.color,
            'is_completed': s.is_completed
        } for s in savings]
    
    if data_type in ['all', 'bills']:
        bills = Bill.query.filter_by(user_id=user_id).all()
        data['bills'] = [{
            'id': b.id, 'name': b.name, 'amount': float(b.amount),
            'due_day': b.due_day, 'due_month': b.due_month,
            'frequency': b.frequency, 'category_id': b.category_id,
            'wallet_id': b.wallet_id, 'reminder_days': b.reminder_days,
            'notes': b.notes,
            'start_date': b.start_date.isoformat() if b.start_date else None,
            'end_date': b.end_date.isoformat() if b.end_date else None
        } for b in bills]
    
    if data_type in ['all', 'debts']:
        debts = Debt.query.filter_by(user_id=user_id).all()
        data['debts'] = [{
            'id': d.id, 'name': d.name, 'total_amount': float(d.total_amount),
            'remaining_amount': float(d.remaining_amount),
            'interest_rate': float(d.interest_rate) if d.interest_rate else None,
            'start_date': d.start_date.isoformat(),
            'due_date': d.due_date.isoformat() if d.due_date else None,
            'lender': d.lender, 'notes': d.notes, 'is_paid': d.is_paid
        } for d in debts]
        loans = Loan.query.filter_by(user_id=user_id).all()
        data['loans'] = [{
            'id': l.id, 'name': l.name, 'total_amount': float(l.total_amount),
            'remaining_amount': float(l.remaining_amount),
            'interest_rate': float(l.interest_rate) if l.interest_rate else None,
            'start_date': l.start_date.isoformat(),
            'due_date': l.due_date.isoformat() if l.due_date else None,
            'borrower': l.borrower, 'notes': l.notes, 'is_repaid': l.is_repaid
        } for l in loans]
    
    return data


def import_from_json(data, user_id, duplicate_handling='skip'):
    """Import data from JSON dict."""
    stats = {'created': 0, 'updated': 0, 'skipped': 0}
    
    if 'wallets' in data:
        for w_data in data['wallets']:
            existing = Wallet.query.filter_by(user_id=user_id, name=w_data['name']).first()
            if existing:
                if duplicate_handling == 'skip':
                    stats['skipped'] += 1
                    continue
                elif duplicate_handling == 'overwrite':
                    for key, value in w_data.items():
                        if hasattr(existing, key) and key not in ['id', 'user_id']:
                            setattr(existing, key, value)
                    stats['updated'] += 1
            else:
                w = Wallet(user_id=user_id, **{k: v for k, v in w_data.items() if k not in ['id']})
                db.session.add(w)
                stats['created'] += 1
    
    # Similar for other entities (simplified)
    db.session.commit()
    return stats



def export_to_csv(rows):
    """Export list of dicts to CSV string."""
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return output.getvalue()


def export_to_excel(rows):
    """Export list of dicts to Excel binary."""
    wb = openpyxl.Workbook()
    ws = wb.active
    if rows:
        ws.append(list(rows[0].keys()))
        for row in rows:
            ws.append(list(row.values()))
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()


def export_to_pdf(rows, title):
    """Export list of dicts to PDF (simple table)."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, title)
    y = 700
    for row in rows:
        # Create a one-line summary from the row (customize as needed)
        text = f"{row.get('Date','')} - {row.get('Description','')} - {row.get('Amount','')}"
        c.drawString(100, y, text)
        y -= 20
        if y < 50:
            c.showPage()
            y = 750
    c.save()
    buffer.seek(0)
    return buffer.read()