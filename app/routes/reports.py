from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from datetime import datetime
import json
from datetime import timedelta
# Try to import chart utilities – if missing, provide fallbacks
try:
    from app.utils.charts import category_pie_data, income_expense_trend, net_worth_history
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    print("Warning: app.utils.charts not found – reports will be limited.")

try:
    from app.utils.export import export_to_csv, export_to_excel, export_to_pdf
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT_AVAILABLE = False
    print("Warning: app.utils.export not found – export disabled.")

bp = Blueprint('reports', __name__)

@bp.route('/')
@login_required
def reports():
    """Render the reports page."""
    return render_template('reports/index.html')

@bp.route('/data')
@login_required
def report_data():
    """AJAX endpoint for chart data."""
    if not CHARTS_AVAILABLE:
        return jsonify({'error': 'Chart utilities not installed'}), 500

    # Get filter parameters from request
    report_type = request.args.get('type', 'income_vs_expense')
    period = request.args.get('period', 'this_month')
    start = request.args.get('start_date')
    end = request.args.get('end_date')

    # Parse dates
    today = datetime.now().date()
    if period == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'last_month':
        first = today.replace(day=1) - timedelta(days=1)
        start_date = first.replace(day=1)
        end_date = first
    elif period == 'this_year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period == 'custom' and start and end:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
    else:
        start_date = today.replace(day=1)
        end_date = today

    # Generate appropriate chart data
    try:
        if report_type == 'income_vs_expense':
            data = income_expense_trend(current_user.id, start_date, end_date)
        elif report_type == 'category_breakdown':
            data = category_pie_data(current_user.id, start_date, end_date, 'expense')
        elif report_type == 'net_worth':
            data = net_worth_history(current_user.id, start_date, end_date)
        else:
            data = {'error': 'Invalid report type'}
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/export')
@login_required
def export():
    """Export data endpoint."""
    if not EXPORT_AVAILABLE:
        flash('Export functionality not available.', 'danger')
        return redirect(url_for('reports.reports'))

    fmt = request.args.get('format', 'csv')
    report_type = request.args.get('type', 'transactions')
    start = request.args.get('start_date')
    end = request.args.get('end_date')

    # This is a placeholder – actual export logic would go here
    flash(f'Exporting as {fmt} is not yet implemented.', 'info')
    return redirect(url_for('reports.reports'))

@bp.route('/financial-health')
@login_required
def financial_health():
    """Display financial health score and achievements."""
    from app.models import Achievement
    health_score = current_user.health_score if current_user.health_score is not None else 0
    achievements = Achievement.query.filter_by(user_id=current_user.id).order_by(Achievement.earned_date.desc()).all()
    return render_template('reports/financial_health.html', health_score=health_score, achievements=achievements)