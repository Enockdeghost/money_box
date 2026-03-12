from flask import render_template, redirect, url_for, flash, request, abort, jsonify, Blueprint
from flask_login import login_required, current_user
from app.extensions import db  # use from app.extensions, not app
from app.models import Category, Transaction
from app.forms import CategoryForm


from flask import Blueprint
bp = Blueprint('categories', __name__)

@bp.route('/')
@login_required
def list_categories():
    """List all categories grouped by type (income/expense)."""
    income_cats = Category.query.filter_by(user_id=current_user.id, type='income').order_by(Category.name).all()
    expense_cats = Category.query.filter_by(user_id=current_user.id, type='expense').order_by(Category.name).all()
    return render_template('categories/list.html', income_cats=income_cats, expense_cats=expense_cats)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_category():
    form = CategoryForm()
    # Populate parent choices based on selected type (via JavaScript)
    if request.method == 'GET':
        form.parent_id.choices = [(0, 'None')]
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            type=form.type.data,
            icon=form.icon.data,
            color=form.color.data,
            user_id=current_user.id,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None
        )
        db.session.add(category)
        db.session.commit()
        flash('Category created.', 'success')
        return redirect(url_for('categories.list_categories'))
    return render_template('categories/create.html', form=form)

@bp.route('/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.user_id != current_user.id:
        abort(403)
    form = CategoryForm(obj=category)
    # Build parent choices excluding self and descendants to prevent cycles
    all_cats = Category.query.filter_by(user_id=current_user.id, type=category.type).all()
    form.parent_id.choices = [(0, 'None')] + [(c.id, c.name) for c in all_cats if c.id != category.id and not is_descendant(c, category)]
    if form.validate_on_submit():
        category.name = form.name.data
        category.icon = form.icon.data
        category.color = form.color.data
        category.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        db.session.commit()
        flash('Category updated.', 'success')
        return redirect(url_for('categories.list_categories'))
    return render_template('categories/edit.html', form=form, category=category)

@bp.route('/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.user_id != current_user.id or category.is_system:
        abort(403)
    # Check if category has transactions
    if category.transactions.count() > 0:
        flash('Cannot delete category with transactions. Reassign transactions first.', 'danger')
        return redirect(url_for('categories.list_categories'))
    # Delete subcategories first (optional, or reassign)
    for sub in category.subcategories:
        db.session.delete(sub)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted.', 'success')
    return redirect(url_for('categories.list_categories'))

@bp.route('/reorder', methods=['POST'])
@login_required
def reorder_categories():
    """Save custom order (if implementing sort_order field)."""
    # This would require a sort_order column in Category
    data = request.get_json()
    for item in data:
        cat = Category.query.get(item['id'])
        if cat and cat.user_id == current_user.id:
            cat.sort_order = item['order']
    db.session.commit()
    return jsonify({'status': 'ok'})

def is_descendant(cat, target):
    """Check if cat is a descendant of target (to prevent cycles)."""
    if cat.parent_id is None:
        return False
    if cat.parent_id == target.id:
        return True
    parent = Category.query.get(cat.parent_id)
    return is_descendant(parent, target) if parent else False