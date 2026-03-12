from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Backup
from app.forms import ImportForm, ExportForm

bp = Blueprint('sync', __name__)

@bp.route('/')
@login_required
def sync_dashboard():
    backups = Backup.query.filter_by(user_id=current_user.id).order_by(Backup.created_at.desc()).limit(10).all()
    return render_template('sync/index.html', backups=backups)

@bp.route('/backup/create', methods=['POST'])
@login_required
def create_backup_route():
    try:
        from app.utils.sync import create_backup
        filename = create_backup(current_user.id)
        flash(f'Backup created: {filename}', 'success')
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'danger')
    return redirect(url_for('sync.sync_dashboard'))

@bp.route('/backup/restore/<int:backup_id>', methods=['POST'])
@login_required
def restore_backup(backup_id):
    backup = Backup.query.get_or_404(backup_id)
    if backup.user_id != current_user.id:
        abort(403)
    try:
        from app.utils.sync import restore_from_backup
        success = restore_from_backup(backup.id)
        if success:
            flash('Backup restored successfully.', 'success')
        else:
            flash('Restore failed.', 'danger')
    except Exception as e:
        flash(f'Restore error: {str(e)}', 'danger')
    return redirect(url_for('sync.sync_dashboard'))

@bp.route('/export', methods=['GET', 'POST'])
@login_required
def export_data():
    form = ExportForm()
    if form.validate_on_submit():
        flash('Export feature coming soon.', 'info')
        return redirect(url_for('sync.sync_dashboard'))
    return render_template('sync/export.html', form=form)

@bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_data():
    form = ImportForm()
    if form.validate_on_submit():
        try:
            from app.utils.sync import import_csv
            file = form.file.data
            import_type = form.import_type.data
            duplicate = form.duplicate_handling.data
            result = import_csv(file, current_user.id, import_type, duplicate)
            flash(f'Import completed: {result.get("created",0)} created, {result.get("updated",0)} updated, {result.get("skipped",0)} skipped.', 'success')
        except Exception as e:
            flash(f'Import error: {str(e)}', 'danger')
        return redirect(url_for('sync.sync_dashboard'))
    return render_template('sync/import.html', form=form)